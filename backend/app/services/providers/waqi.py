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

from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.errors import ProviderNotConfigured, ProviderUnavailable
from app.core.logging_config import get_logger, log_event
from app.domain.aqi import index_to_concentration
from app.services.providers.base import AirQualityObservation

import logging

logger = get_logger("airs.provider.waqi")

BASE_URL = "https://api.waqi.info"
_POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")


class WaqiProvider:
    name = "WAQI / AQICN"

    def available(self) -> bool:
        return bool(settings.waqi_token)

    def fetch(self, lat: float, lon: float,
              keyword: str | None = None) -> AirQualityObservation:
        if not self.available():
            raise ProviderNotConfigured("Air quality provider is not configured.")

        path = f"/feed/{keyword}/" if keyword else f"/feed/geo:{lat};{lon}/"
        try:
            with httpx.Client(timeout=12.0) as client:
                resp = client.get(f"{BASE_URL}{path}",
                                  params={"token": settings.waqi_token})
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            log_event(logger, logging.WARNING, "waqi_http_error", path=path,
                      error=type(exc).__name__)
            raise ProviderUnavailable(detail=str(exc)) from exc

        if payload.get("status") != "ok":
            log_event(logger, logging.WARNING, "waqi_bad_status",
                      status=payload.get("status"))
            raise ProviderUnavailable(
                "The air-quality feed returned no data for this location.")

        return self._normalise(payload["data"])

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
