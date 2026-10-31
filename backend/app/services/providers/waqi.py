"""WAQI / AQICN adapter.

Derived from the original ``src/data_collection/fetch_aqi.py`` in this repo and
extended in two important ways:

1. WAQI's ``iaqi`` block holds **AQI sub-indices**, not concentrations. The
   original code stored them as if they were ug/m3, which understates PM2.5 in
   the healthy range and overstates it in the unhealthy range. We now invert the
   EPA piecewise function to recover true concentrations.
2. Failures are typed (:class:`ProviderUnavailable`) rather than raised as bare
   ``ValueError``/``HTTPError``, so a single dead upstream can never take the
   API down.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.core import http
from app.core.cache import cache
from app.core.config import settings
from app.core.errors import ProviderNotConfigured, ProviderUnavailable
from app.core.logging_config import get_logger, log_event
from app.domain.aqi import index_to_concentration
from app.services.providers.base import AirQualityObservation

import logging

logger = get_logger("airs.provider.waqi")

BASE_URL = "https://api.waqi.info"
_POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")


@dataclass
class WaqiStation:
    uid: int
    name: str
    lat: float
    lon: float
    aqi: float | None
    observed_at: datetime | None
    source: str = "WAQI"
    pm25: float | None = None
    pm10: float | None = None

    def age_hours(self) -> float | None:
        if self.observed_at is None:
            return None
        return (datetime.now(timezone.utc) - self.observed_at).total_seconds() / 3600


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# India split into tiles so no single bounds query is huge.
_INDIA_TILES = [(la, lo, min(la + 8, 37.5), min(lo + 10, 97.5))
                for la in (6.0, 14.0, 22.0, 30.0) for lo in (68.0, 78.0, 88.0)]
INDEX_TTL = 600          # stations publish hourly; 10 minutes is fresh enough
FEED_TTL = 600
MAX_STATION_AGE_H = 3.0  # older than this is not "now"


class WaqiProvider:
    name = "WAQI / AQICN"

    def available(self) -> bool:
        return bool(settings.waqi_token)

    # -- raw calls ------------------------------------------------------
    def _call(self, path: str, params: dict | None = None) -> dict:
        if not self.available():
            raise ProviderNotConfigured("Air quality provider is not configured.")
        try:
            resp = http.get(f"{BASE_URL}{path}",
                            params={**(params or {}), "token": settings.waqi_token},
                            timeout=15.0)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            log_event(logger, logging.WARNING, "waqi_http_error", path=path,
                      error=type(exc).__name__)
            raise ProviderUnavailable(detail=str(exc)) from exc
        if payload.get("status") != "ok":
            log_event(logger, logging.WARNING, "waqi_bad_status",
                      status=payload.get("status"), data=str(payload.get("data"))[:120])
            raise ProviderUnavailable(
                "The air-quality feed returned no data.",
                detail=str(payload.get("data"))[:200])
        return payload

    def stations_in_bounds(self, lat1: float, lon1: float, lat2: float,
                           lon2: float) -> list[WaqiStation]:
        latlng = f"{lat1},{lon1},{lat2},{lon2}"
        try:
            payload = self._call("/v2/map/bounds",
                                 {"latlng": latlng, "networks": "all"})
        except ProviderUnavailable:
            # the older v1 route answers for tokens the v2 one refuses
            payload = self._call("/map/bounds/", {"latlng": latlng})
        out: list[WaqiStation] = []
        for row in payload.get("data") or []:
            try:
                aqi = float(row.get("aqi"))
            except (TypeError, ValueError):
                aqi = None                      # "-" means offline
            station = row.get("station") or {}
            if not isinstance(station, dict):
                station = {"name": str(station)}
            out.append(WaqiStation(
                uid=int(row["uid"]), name=str(station.get("name") or "Station"),
                lat=float(row["lat"]), lon=float(row["lon"]), aqi=aqi,
                observed_at=_parse_iso(station.get("time") or row.get("time"))))
        return out

    def india_index(self) -> list[WaqiStation]:
        """Every WAQI station in India, refreshed at most every 10 minutes."""
        hit = cache.get("waqi:india-index")
        if hit is not None:
            return hit
        seen: dict[int, WaqiStation] = {}
        errors = 0
        last_error: Exception | None = None
        for tile in _INDIA_TILES:
            for attempt in (1, 2):                 # one retry per tile
                try:
                    for st in self.stations_in_bounds(*tile):
                        seen[st.uid] = st
                    break
                except ProviderUnavailable as exc:
                    if attempt == 2:
                        errors += 1
                        last_error = exc
        if not seen:
            stale = cache.get_stale("waqi:india-index")
            if stale is not None:
                return stale[0]
            raise ProviderUnavailable(
                "Could not load the WAQI station network.",
                detail=str(getattr(last_error, "detail", None) or last_error))
        stations = list(seen.values())
        cache.set("waqi:india-index", stations, INDEX_TTL)
        log_event(logger, logging.INFO, "waqi_index_loaded",
                  stations=len(stations), tile_errors=errors)
        return stations

    def station_feed(self, uid: int) -> AirQualityObservation:
        key = f"waqi:feed:{uid}"
        hit = cache.get(key)
        if hit is not None:
            return hit
        obs = self._normalise(self._call(f"/feed/@{uid}/")["data"])
        cache.set(key, obs, FEED_TTL)
        return obs

    def nearby(self, lat: float, lon: float, radius_km: float,
               max_age_h: float = MAX_STATION_AGE_H) -> list[tuple[WaqiStation, float]]:
        """Fresh, reporting stations within ``radius_km``, nearest first."""
        found = []
        for st in self.india_index():
            if st.aqi is None or st.aqi <= 0 or st.aqi > 999:
                continue
            age = st.age_hours()
            if age is not None and (age > max_age_h or age < -2):
                continue
            d = haversine_km(lat, lon, st.lat, st.lon)
            if d <= radius_km:
                found.append((st, d))
        found.sort(key=lambda pair: pair[1])
        return found

    def fetch(self, lat: float, lon: float,
              keyword: str | None = None,
              radius_km: float = 12.0) -> AirQualityObservation:
        """The real reading at the nearest fresh station to (lat, lon).

        The old version asked WAQI for ``geo:lat;lon``, which returns *a*
        station with no distance limit — so Amritsar got Chandigarh's numbers
        and every receptor in Mumbai got the same station. Now a station only
        counts if it is within ``radius_km`` and reported in the last 3 hours;
        otherwise the caller falls back to the (labelled) model.
        """
        near = self.nearby(lat, lon, radius_km)
        if not near:
            raise ProviderUnavailable(
                "No monitoring station reports near this location.",
                detail=f"no fresh WAQI station within {radius_km:.0f} km")
        last_exc: Exception | None = None
        for station, dist in near[:3]:
            try:
                obs = self.station_feed(station.uid)
            except ProviderUnavailable as exc:
                last_exc = exc
                continue
            obs.station_ref = str(station.uid)
            obs.quality_flags = list(obs.quality_flags) + [
                "source:waqi", f"station_km:{dist:.1f}"]
            return obs
        raise ProviderUnavailable("The nearest stations did not answer.",
                                  detail=str(last_exc))

    # -- helpers ------------------------------------------------------
    @staticmethod
    def _normalise(data: dict) -> AirQualityObservation:
        iaqi = data.get("iaqi", {}) or {}
        sub_indices: dict[str, float] = {}
        concentrations: dict[str, float | None] = {}
        flags: list[str] = []

        for key in _POLLUTANTS:
            raw = iaqi.get(key)
            if raw is None or raw.get("v") is None:
                concentrations[key] = None
                continue
            index = float(raw["v"])
            if index < 0 or index > 900:
                flags.append(f"{key}_out_of_range")
                concentrations[key] = None
                continue
            sub_indices[key] = index
            concentrations[key] = index_to_concentration(key, index)

        observed_at = _parse_time(data.get("time", {}))
        aqi = data.get("aqi")
        aqi = float(aqi) if isinstance(aqi, (int, float)) else None

        return AirQualityObservation(
            observed_at=observed_at,
            aqi=aqi,
            dominant_pollutant=data.get("dominentpol"),
            pm25=concentrations.get("pm25"),
            pm10=concentrations.get("pm10"),
            no2=concentrations.get("no2"),
            so2=concentrations.get("so2"),
            co=concentrations.get("co"),
            o3=concentrations.get("o3"),
            sub_indices=sub_indices,
            source_name="WAQI / AQICN",
            provenance="live",
            station_ref=str(data.get("idx")) if data.get("idx") is not None else None,
            quality_flags=flags,
        )


def _parse_time(time_block: dict) -> datetime:
    iso = time_block.get("iso")
    if iso:
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            pass
    epoch = time_block.get("v")
    if isinstance(epoch, (int, float)):
        return datetime.fromtimestamp(epoch, tz=timezone.utc)
    return datetime.now(timezone.utc)


def _parse_iso(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.strip().replace("Z", "+00:00")
                                    .replace(" ", "T", 1))
    except ValueError:
        return None
    # A naive WAQI timestamp is station-local; for India that is IST.
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
