"""The live layer: station selection, fallbacks, history and forecast.

No network: WAQI and Open-Meteo are replaced by in-memory fakes.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.core.cache import cache
from app.core.config import settings
from app.services import live_air
from app.services.providers import openmeteo
from app.services.providers.waqi import WaqiProvider

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime.now(timezone.utc)

# uid: (name, lat, lon, aqi, hours old)
STATIONS = {
    1: ("Vasundhara, Ghaziabad", 28.660, 77.357, 128, 0.5),
    2: ("Loni, Ghaziabad", 28.757, 77.278, 112, 0.5),
    3: ("Anand Vihar, Delhi", 28.647, 77.316, 190, 0.5),   # ~13 km from Ghaziabad
    4: ("Sector 22, Chandigarh", 30.735, 76.775, 68, 0.5),
    5: ("Golden Temple, Amritsar", 31.620, 74.876, 165, 0.5),
    6: ("Old station, Amritsar", 31.640, 74.860, 40, 30),   # stale
}


def _bounds():
    return {"status": "ok", "data": [
        {"uid": uid, "lat": lat, "lon": lon, "aqi": str(aqi),
         "station": {"name": name,
                     "time": (NOW - timedelta(hours=age)).isoformat()}}
        for uid, (name, lat, lon, aqi, age) in STATIONS.items()]}


def _feed(uid):
    name, lat, lon, aqi, age = STATIONS[uid]
    return {"status": "ok", "data": {
        "aqi": aqi, "idx": uid, "dominentpol": "pm25",
        "iaqi": {"pm25": {"v": aqi}, "pm10": {"v": aqi * 0.6},
                 "no2": {"v": 8}, "o3": {"v": 12}},
        "time": {"iso": (NOW - timedelta(hours=age)).isoformat()}}}


def _hourly(start: datetime, hours: int, base: float = 80.0) -> dict:
    times = [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00")
             for h in range(hours)]
    n = len(times)
    return {"time": times, "us_aqi": [base] * n, "pm2_5": [30.0] * n,
            "pm10": [60.0] * n, "carbon_monoxide": [400.0] * n,
            "nitrogen_dioxide": [20.0] * n, "sulphur_dioxide": [10.0] * n,
            "ozone": [50.0] * n, "us_aqi_pm2_5": [base] * n,
            "us_aqi_pm10": [40.0] * n, "us_aqi_carbon_monoxide": [5.0] * n,
            "us_aqi_nitrogen_dioxide": [10.0] * n,
            "us_aqi_sulphur_dioxide": [4.0] * n, "us_aqi_ozone": [20.0] * n}


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    cache.clear()
    monkeypatch.setattr(settings, "waqi_token", "test-token")
    monkeypatch.setattr(live_air, "HISTORY_DIR", tmp_path)

    def fake_call(self, path, params=None):
        if path == "/v2/map/bounds":
            lat1, lon1, lat2, lon2 = map(float, params["latlng"].split(","))
            data = _bounds()
            data["data"] = [r for r in data["data"]
                            if lat1 <= r["lat"] < lat2 and lon1 <= r["lon"] < lon2]
            return data
        if path.startswith("/feed/@"):
            return _feed(int(path.split("@")[1].strip("/")))
        raise AssertionError(path)

    monkeypatch.setattr(WaqiProvider, "_call", fake_call)

    def fake_get(url, params, timeout=20.0):
        if url == openmeteo.WEATHER_URL:
            today = datetime.now(IST).date()
            days = [(today + timedelta(days=i)).isoformat() for i in range(-1, 5)]
            return {"current": {"temperature_2m": 27.5, "relative_humidity_2m": 70,
                                "wind_speed_10m": 2.5, "weather_code": 61,
                                "is_day": 1, "uv_index": 5.7},
                    "daily": {"time": days, "weather_code": [61] * 6,
                              "temperature_2m_max": [31] * 6,
                              "temperature_2m_min": [24] * 6,
                              "precipitation_probability_max": [60] * 6,
                              "uv_index_max": [7] * 6,
                              "wind_speed_10m_max": [4] * 6}}
        if "current" in params:
            lats = str(params["latitude"]).split(",")
            items = [{"current": {"time": "2026-09-28T10:00", "us_aqi": 55,
                                  "pm2_5": 14.0}} for _ in lats]
            return items if len(lats) > 1 else items[0]
        if "start_date" in params:
            start = datetime.fromisoformat(params["start_date"])
            end = datetime.fromisoformat(params["end_date"])
            return {"hourly": _hourly(start, int((end - start).days + 1) * 24)}
        start = (datetime.now(IST) - timedelta(days=params.get("past_days", 0))
                 ).replace(hour=0, minute=0, second=0, microsecond=0)
        one = {"hourly": _hourly(start.replace(tzinfo=None),
                                 24 * (params.get("past_days", 0)
                                       + params.get("forecast_days", 5)))}
        lats = str(params["latitude"]).split(",")
        return [one] * len(lats) if len(lats) > 1 else one

    monkeypatch.setattr(openmeteo, "_get", fake_get)
    yield
    cache.clear()


def _city(slug):
    from sqlalchemy import select
    from app.db.models import City
    from app.db.session import SessionLocal
    db = SessionLocal()
    return db, db.scalar(select(City).where(City.slug == slug))


def test_gas_units_are_converted_to_ppb():
    assert openmeteo.to_airs_units("no2", 46.0055) == pytest.approx(24.45, abs=0.1)
    assert openmeteo.to_airs_units("co", 1145.0) == pytest.approx(1.0, abs=0.01)
    assert openmeteo.to_airs_units("pm25", 12.34) == 12.3


def test_amritsar_does_not_get_chandigarh(fakes):
    db, city = _city("amritsar")
    live = live_air.city_live(db, city)
    assert live["source"] == "measured"
    assert live["aqi"] == 165                       # stale station excluded
    assert [s["uid"] for s in live["stations"]] == [5]
    db.close()


def test_ghaziabad_uses_its_own_ring_not_delhi(fakes):
    db, city = _city("ghaziabad")
    live = live_air.city_live(db, city)
    uids = {s["uid"] for s in live["stations"]}
    assert 3 not in uids
    assert live["aqi"] == round((128 + 112) / 2) or live["aqi"] == 128
    assert live["pollutants"][0]["key"] == "pm25"
    assert live["weather"]["temperature_c"] == 27.5
    assert live["yesterday"]["aqi"] is not None
    db.close()


def test_city_without_station_falls_back_to_model(fakes):
    db, city = _city("leh")
    live = live_air.city_live(db, city)
    assert live["source"] == "modelled"
    assert live["provenance"]["kind"] == "estimated"
    assert live["aqi"] == 80
    db.close()


def test_india_ranks_every_city(fakes):
    db, _ = _city("delhi")
    from app.services import repository
    cities = repository.list_cities(db)
    out = live_air.india_live(db, cities)
    assert out["total_cities"] == len(cities) >= 200
    assert out["reporting_cities"] == len(cities)
    assert out["worst"][0]["aqi"] >= out["worst"][-1]["aqi"]
    assert out["measured_cities"] >= 3
    db.close()


def test_history_and_forecast_shapes(fakes):
    db, city = _city("mumbai")
    hist = live_air.city_history(db, city, month=9, metric="aqi")
    assert hist["years"][0] == 2022
    assert all(len(s["days"]) == 30 for s in hist["series"])
    assert hist["monthly"] and len(hist["monthly"][0]["months"]) == 12
    assert hist["calendar"]
    pm = live_air.city_history(db, city, month=9, metric="pm25")
    assert pm["unit"] == "µg/m³"
    fc = live_air.city_forecast(db, city)
    assert fc["hours"] and fc["days"]
    assert fc["provenance"]["kind"] == "predicted"
    db.close()


def test_insights_endpoints(fakes, client):
    assert client.get("/api/v1/insights/live?city=amritsar").status_code == 200
    assert client.get("/api/v1/insights/history?city=delhi&month=1").status_code == 200
    assert client.get("/api/v1/insights/history?city=delhi&metric=bad").status_code == 422
    cities = client.get("/api/v1/insights/cities").json()
    assert len(cities) >= 200 and all(c["state"] for c in cities)


def _oaq(loc, lat, lon, pm25, hours_old):
    from app.services.providers.openaq import OpenAQStation
    return OpenAQStation(location_id=loc, name=f"OAQ {loc}", lat=lat, lon=lon,
                         pm25=pm25, pm10=None,
                         observed_at=NOW - timedelta(hours=hours_old))


def test_fresh_openaq_station_counts_as_measured(fakes, monkeypatch):
    from app.services.providers import openaq
    monkeypatch.setattr(openaq, "available", lambda: True)
    monkeypatch.setattr(openaq, "stations",
                        lambda: [_oaq(1, 29.14, 75.74, 31.0, 0.5)])   # Hisar
    db, city = _city("hisar")
    live = live_air.city_live(db, city)
    assert live["source"] == "measured"
    assert 85 <= live["aqi"] <= 95          # PM2.5 31 µg/m³ ≈ AQI 91
    assert live["stations"][0]["network"] == "OpenAQ"
    db.close()


def test_stale_station_calibrates_the_model(fakes, monkeypatch):
    from app.services.providers import openaq
    monkeypatch.setattr(openaq, "available", lambda: True)
    # Leh: no fresh station within 200 km in the fakes, one 85 h-old reading
    monkeypatch.setattr(openaq, "stations",
                        lambda: [_oaq(2, 34.15, 77.58, 10.0, 85)])
    db, city = _city("leh")
    live = live_air.city_live(db, city)
    assert live["source"] == "calibrated"
    assert live["calibration_anchors"] == 1
    assert 45 <= live["aqi"] <= 60           # PM2.5 10 µg/m³ ≈ AQI 53
    assert live["provenance"]["kind"] == "estimated"
    db.close()


def test_regional_stations_beat_the_model(fakes, monkeypatch):
    """Hisar has no station of its own: fresh ones up to 200 km away are
    averaged by distance instead of trusting a model dust spike."""
    db, city = _city("hisar")
    live = live_air.city_live(db, city)
    assert live["source"] == "calibrated"
    assert "km away" in live["source_label"]
    db.close()
