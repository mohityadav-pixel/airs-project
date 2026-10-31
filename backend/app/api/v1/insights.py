"""City-level live data, national ranking, history and forecast.

These endpoints back the redesigned dashboard. See ``services.live_air`` for
where each number comes from.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.common import resolve_city
from app.db.india_cities import STATE_OF
from app.db.session import get_db
from app.services import live_air, repository

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/cities")
def cities(db: Session = Depends(get_db)) -> list[dict]:
    """Every city with its state — small enough to ship whole for search."""
    return [{"slug": c.slug, "name": c.name, "state": STATE_OF.get(c.slug),
             "latitude": c.latitude, "longitude": c.longitude}
            for c in repository.list_cities(db)]


@router.get("/live")
def live(city: str | None = None, db: Session = Depends(get_db)) -> dict:
    return live_air.city_live(db, resolve_city(db, city))


@router.get("/forecast")
def forecast(city: str | None = None, db: Session = Depends(get_db)) -> dict:
    return live_air.city_forecast(db, resolve_city(db, city))


@router.get("/history")
def history(city: str | None = None,
            month: int | None = Query(default=None, ge=1, le=12),
            metric: str = Query(default="aqi",
                                pattern="^(aqi|pm25|pm10|co|no2|so2|o3)$"),
            db: Session = Depends(get_db)) -> dict:
    return live_air.city_history(db, resolve_city(db, city), month, metric)


@router.get("/india")
def india(db: Session = Depends(get_db)) -> dict:
    return live_air.india_live(db, repository.list_cities(db))


@router.get("/debug/tiles")
def debug_tiles() -> dict:
    """Station counts per bounds tile, to see whether WAQI truncates them."""
    from app.services.providers.waqi import _INDIA_TILES
    w = live_air.waqi
    out = {}
    for t in _INDIA_TILES[:0]:
        try:
            out[str(t)] = len(w.stations_in_bounds(*t))
        except Exception as exc:  # noqa: BLE001
            out[str(t)] = str(exc)
    for name, la, lo in (("delhi", 28.2, 76.8), ("mumbai", 18.8, 72.7),
                         ("hisar", 28.7, 75.3)):
        for step in (4.0, 2.0, 1.0, 0.5):
            try:
                out[f"{name}-box-{step}"] = len(
                    w.stations_in_bounds(la, lo, la + step, lo + step))
            except Exception as exc:  # noqa: BLE001
                out[f"{name}-box-{step}"] = str(exc)
    return out


@router.get("/debug")
def debug(city: str | None = None, db: Session = Depends(get_db)) -> dict:
    """What the live layer can actually see — for diagnosing wrong numbers."""
    from app.core import cache as cache_module
    from app.core.errors import AirsError
    from app.services.providers import openmeteo
    from app.services.providers.waqi import haversine_km
    c = resolve_city(db, city)
    out: dict = {"city": c.slug, "lat": c.latitude, "lon": c.longitude,
                 "waqi_token_set": live_air.waqi.available()}
    try:
        index = live_air.waqi.india_index()
        out["waqi_stations_in_india"] = len(index)
        near = sorted(((haversine_km(c.latitude, c.longitude, s.lat, s.lon), s)
                       for s in index), key=lambda p: p[0])[:8]
        out["nearest_stations"] = [
            {"uid": s.uid, "name": s.name, "km": round(d, 1), "aqi": s.aqi,
             "time": s.observed_at.isoformat() if s.observed_at else None,
             "age_h": round(s.age_hours(), 1) if s.age_hours() is not None else None}
            for d, s in near]
        out["used_stations"] = [s.uid for s, _ in live_air._select_stations(c, index)]
    except AirsError as exc:
        out["waqi_error"] = f"{exc.public_message} {exc.detail or ''}"
    for name, fn in (("open_meteo_air", lambda: openmeteo.OpenMeteoAirProvider()
                      .fetch(c.latitude, c.longitude).aqi),
                     ("open_meteo_weather", lambda: bool(openmeteo.weather_bundle(
                         c.latitude, c.longitude).get("current")))):
        try:
            out[name] = fn()
        except AirsError as exc:
            out[name + "_error"] = f"{exc.public_message} {exc.detail or ''}"
    out["provider_failures"] = cache_module.last_failures()
    return out


@router.get("/debug/raw")
def debug_raw(latlng: str = "18.8,72.7,19.8,73.7", keyword: str = "mumbai") -> dict:
    import httpx
    from app.core.config import settings
    tok = settings.waqi_token
    out = {}
    for label, url, params in (
            ("v2", "https://api.waqi.info/v2/map/bounds", {"latlng": latlng, "networks": "all"}),
            ("v2_official", "https://api.waqi.info/v2/map/bounds", {"latlng": latlng}),
            ("v1", "https://api.waqi.info/map/bounds/", {"latlng": latlng}),
            ("search", "https://api.waqi.info/search/", {"keyword": keyword}),
            ("feed", f"https://api.waqi.info/feed/{keyword}/", {})):
        try:
            r = httpx.get(url, params={**params, "token": tok}, timeout=20)
            if label == "search":
                import json as _j
                d = _j.loads(r.text).get("data") or []
                out[label] = [(x["uid"], x["aqi"], x["time"].get("stime"),
                               x["station"]["name"]) for x in d]
            else:
                out[label] = r.text[:1200]
        except Exception as exc:  # noqa: BLE001
            out[label] = f"ERR {exc}"
    return out


@router.get("/debug/ai")
def debug_ai() -> dict:
    from app.ai import gemini
    from app.core.config import settings
    key = (settings.gemini_api_key or "").strip()
    out = {"key_prefix": key[:4], "key_len": len(key), "model": settings.gemini_model}
    try:
        out["reply"] = gemini.generate("Reply with exactly: OK", "Reply now.",
                                       temperature=0, max_output_tokens=20)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {getattr(exc, 'detail', None) or exc}"[:1500]
    return out


@router.get("/debug/ai2")
def debug_ai2() -> dict:
    from google import genai
    from app.core.config import settings
    key = (settings.gemini_api_key or "").strip()
    out = {}
    import socket
    for host in ("aiplatform.googleapis.com", "generativelanguage.googleapis.com",
                 "us-central1-aiplatform.googleapis.com"):
        try:
            out["dns:" + host] = socket.gethostbyname(host)
        except Exception as exc:  # noqa: BLE001
            out["dns:" + host] = str(exc)
    for label, kw in (("vertex", {"vertexai": True, "api_key": key}),
                      ("studio", {"api_key": key})):
        try:
            c = genai.Client(**kw)
            try:
                out[label + "_url"] = str(c._api_client._http_options.base_url)
            except Exception:  # noqa: BLE001
                pass
            r = c.models.generate_content(model="gemini-2.5-flash", contents="Say OK")
            out[label] = (r.text or "")[:50]
        except Exception as exc:  # noqa: BLE001
            out[label] = f"{type(exc).__name__}: {exc}"[:400]
    return out


@router.get("/debug/models")
def debug_models() -> dict:
    import httpx
    from app.core.config import settings
    r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models",
                  params={"key": settings.gemini_api_key, "pageSize": 200}, timeout=20)
    try:
        ms = r.json().get("models", [])
    except Exception:  # noqa: BLE001
        return {"status": r.status_code, "text": r.text[:500]}
    return {"status": r.status_code,
            "models": [m["name"] for m in ms
                       if "generateContent" in m.get("supportedGenerationMethods", [])]}


@router.get("/debug/om")
def debug_om() -> dict:
    import httpx
    out = {}
    for label, params in (("one", {"latitude": 19.07, "longitude": 72.88, "current": "us_aqi"}),
                          ("many", {"latitude": ",".join(["19.07"] * 50),
                                    "longitude": ",".join(["72.88"] * 50),
                                    "hourly": "us_aqi", "past_days": 5, "forecast_days": 1})):
        try:
            r = httpx.get("https://air-quality-api.open-meteo.com/v1/air-quality",
                          params=params, timeout=30)
            out[label] = [r.status_code, r.text[:300]]
        except Exception as exc:  # noqa: BLE001
            out[label] = f"{type(exc).__name__}: {exc}"
    return out
