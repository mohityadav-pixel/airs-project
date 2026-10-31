"""OpenAQ v3 adapter — the CPCB network plus low-cost sensors across India.

WAQI stopped receiving most Indian CPCB feeds in mid-2026, so OpenAQ is the
second station source. Two quirks shape this module:

* OpenAQ has no "latest values in this country" filter, so the per-parameter
  latest listing is paged in full and cut to India by coordinates. That is
  ~20 requests, so it runs on a background thread every 15 minutes and page
  loads only ever read the cached result.
* CPCB data frequently reaches OpenAQ days late. Readings are therefore
  returned with their age; ``live_air`` decides what counts as "now" and uses
  older readings only to calibrate the model, never as the current value.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core import http

from app.core.config import settings
from app.core.logging_config import get_logger, log_event
from app.domain.aqi import concentration_to_index

logger = get_logger("airs.provider.openaq")
BASE = "https://api.openaq.org/v3"
INDIA_BBOX = (68.0, 6.0, 97.5, 37.5)       # lon/lat min, lon/lat max
REFRESH_SECONDS = 900
PARAMS = {2: "pm25", 1: "pm10"}


@dataclass
class OpenAQStation:
    location_id: int
    name: str
    lat: float
    lon: float
    pm25: float | None
    pm10: float | None
    observed_at: datetime | None
    source: str = "OpenAQ"

    @property
    def uid(self) -> int:
        return 10_000_000 + self.location_id

    @property
    def aqi(self) -> float | None:
        subs = [concentration_to_index("pm25", self.pm25) if self.pm25 is not None else None,
                concentration_to_index("pm10", self.pm10) if self.pm10 is not None else None]
        subs = [s for s in subs if s is not None]
        return max(subs) if subs else None

    def age_hours(self) -> float | None:
        if self.observed_at is None:
            return None
        return (datetime.now(timezone.utc) - self.observed_at).total_seconds() / 3600


_state: dict = {"stations": [], "loaded_at": 0.0, "names": {}, "names_at": 0.0,
                "error": None}
_lock = threading.Lock()
_thread: threading.Thread | None = None


def available() -> bool:
    return bool(settings.openaq_api_key)


def _get(path: str, params: dict) -> dict:
    headers = {"X-API-Key": settings.openaq_api_key or ""}
    resp = http.get(f"{BASE}{path}", params=params, headers=headers)
    if resp.status_code == 429:                     # rate limited: back off once
        time.sleep(5)
        resp = http.get(f"{BASE}{path}", params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


def _in_india(lat: float, lon: float) -> bool:
    return INDIA_BBOX[1] <= lat <= INDIA_BBOX[3] and INDIA_BBOX[0] <= lon <= INDIA_BBOX[2]


def _load_names() -> dict[int, tuple[str, str]]:
    names: dict[int, tuple[str, str]] = {}
    for page in range(1, 6):
        data = _get("/locations", {"bbox": ",".join(map(str, INDIA_BBOX)),
                                   "limit": 1000, "page": page})
        rows = data.get("results") or []
        for r in rows:
            names[int(r["id"])] = (str(r.get("name") or "Station"),
                                   ((r.get("country") or {}).get("code") or ""))
        if len(rows) < 1000:
            break
    return names


def _load_latest() -> list[OpenAQStation]:
    if not _state["names"] or time.time() - _state["names_at"] > 86400:
        _state["names"] = _load_names()
        _state["names_at"] = time.time()
    names = _state["names"]
    values: dict[int, dict] = {}
    for pid, key in PARAMS.items():
        for page in range(1, 40):
            data = _get(f"/parameters/{pid}/latest", {"limit": 1000, "page": page})
            rows = data.get("results") or []
            for r in rows:
                c = r.get("coordinates") or {}
                lat, lon = c.get("latitude"), c.get("longitude")
                if lat is None or lon is None or not _in_india(lat, lon):
                    continue
                loc = int(r["locationsId"])
                if names and names.get(loc, ("", "IN"))[1] not in ("IN", ""):
                    continue                      # Pakistan, Nepal, Bangladesh …
                v = r.get("value")
                if v is None or v < 0 or v > 1500:
                    continue
                try:
                    ts = datetime.fromisoformat(r["datetime"]["utc"].replace("Z", "+00:00"))
                except (KeyError, TypeError, ValueError):
                    continue
                slot = values.setdefault(loc, {"lat": lat, "lon": lon, "at": ts})
                # keep the freshest reading of each parameter
                if key not in slot or ts >= slot[f"{key}_at"]:
                    slot[key], slot[f"{key}_at"] = float(v), ts
                slot["at"] = max(slot["at"], ts)
            if len(rows) < 1000:
                break
    return [OpenAQStation(location_id=loc, name=names.get(loc, ("Station", ""))[0],
                          lat=s["lat"], lon=s["lon"], pm25=s.get("pm25"),
                          pm10=s.get("pm10"), observed_at=s["at"])
            for loc, s in values.items()]


def _refresh_forever() -> None:
    while True:
        try:
            stations = _load_latest()
            with _lock:
                _state.update(stations=stations, loaded_at=time.time(), error=None)
            fresh = sum(1 for s in stations if (s.age_hours() or 99) <= 3)
            log_event(logger, logging.INFO, "openaq_loaded",
                      stations=len(stations), fresh=fresh)
        except Exception as exc:                   # keep last good copy
            with _lock:
                _state["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
            log_event(logger, logging.WARNING, "openaq_failed",
                      error=type(exc).__name__, detail=str(exc)[:200])
        time.sleep(REFRESH_SECONDS)


def start_background() -> None:
    global _thread
    if not available() or (_thread and _thread.is_alive()):
        return
    _thread = threading.Thread(target=_refresh_forever, name="openaq-refresh",
                               daemon=True)
    _thread.start()


def stations() -> list[OpenAQStation]:
    start_background()
    with _lock:
        return list(_state["stations"])


def status() -> dict:
    with _lock:
        st = _state["stations"]
        return {"configured": available(), "stations": len(st),
                "fresh_3h": sum(1 for s in st if (s.age_hours() or 99) <= 3),
                "loaded_seconds_ago": round(time.time() - _state["loaded_at"])
                if _state["loaded_at"] else None,
                "error": _state["error"]}
