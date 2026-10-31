"""Test fixtures.

Every test runs against a throwaway SQLite database seeded with the reference
data and a short synthetic history, with the data mode pinned to ``demo`` so no
test ever touches a real upstream provider or spends API quota.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

TMP_DB = Path(tempfile.gettempdir()) / "airs_test.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TMP_DB}"
os.environ["AIRS_DATA_MODE"] = "demo"
os.environ["AIRS_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["WAQI_TOKEN"] = ""
os.environ["OPENWEATHER_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENAQ_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.init_db import init  # noqa: E402
from app.db.models import (AirQualityReading, City, Provenance, Station,  # noqa: E402
                            TrafficReading, WeatherReading)
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.providers.demo import (synth_air_quality, synth_traffic,  # noqa: E402
                                          synth_weather)
from app.services.providers.openweather import ventilation_index  # noqa: E402


def _seed_history(hours: int = 96) -> None:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    with SessionLocal() as db:
        city = db.scalar(select(City).where(City.slug == "delhi"))
        stations = list(db.scalars(select(Station).where(Station.city_id == city.id)))
        existing = db.scalar(select(AirQualityReading).limit(1))
        if existing is not None:
            return
        rows = []
        for station in stations:
            zone = station.zone_type.value
            for h in range(hours, -1, -1):
                ts = now - timedelta(hours=h)
                aq = synth_air_quality(city.slug, station.code, zone, ts)
                wx = synth_weather(station.code, ts)
                tr = synth_traffic(station.code, zone, ts)
                rows.append(AirQualityReading(
                    station_id=station.id, observed_at=ts, ingested_at=now,
                    provenance=Provenance.demo, aqi=aq.aqi,
                    dominant_pollutant=aq.dominant_pollutant, pm25=aq.pm25,
                    pm10=aq.pm10, no2=aq.no2, so2=aq.so2, co=aq.co, o3=aq.o3,
                    sub_indices=aq.sub_indices, quality_flags=[]))
                rows.append(WeatherReading(
                    station_id=station.id, observed_at=ts, ingested_at=now,
                    provenance=Provenance.demo, temperature_c=wx.temperature_c,
                    humidity_pct=wx.humidity_pct, pressure_hpa=wx.pressure_hpa,
                    wind_speed_mps=wx.wind_speed_mps, wind_deg=wx.wind_deg,
                    rain_1h_mm=wx.rain_1h_mm, clouds_pct=wx.clouds_pct,
                    visibility_m=wx.visibility_m, condition=wx.condition,
                    ventilation_index=ventilation_index(
                        wx.wind_speed_mps, wx.temperature_c, ts.hour)))
                rows.append(TrafficReading(
                    station_id=station.id, observed_at=ts, ingested_at=now,
                    provenance=Provenance.demo,
                    congestion_index=tr.congestion_index,
                    speed_ratio=tr.speed_ratio,
                    vehicle_volume_est=tr.vehicle_volume_est))
        db.add_all(rows)
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def database():
    if TMP_DB.exists():
        TMP_DB.unlink()
    init()
    _seed_history()
    yield
    if TMP_DB.exists():
        TMP_DB.unlink()


@pytest.fixture(scope="session")
def client(database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def citizen_token(client) -> str:
    payload = {"email": "citizen@example.com", "full_name": "Test Citizen",
               "password": "a-long-enough-password"}
    response = client.post("/api/v1/auth/register", json=payload)
    if response.status_code == 400:
        response = client.post("/api/v1/auth/login", json={
            "email": payload["email"], "password": payload["password"]})
    return response.json()["access_token"]


@pytest.fixture
def official_token(client) -> str:
    """Promotes a user directly in the database — the API deliberately offers no
    way for a client to grant itself a role."""
    from app.db.models import Role, User
    from app.core.security import hash_password

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "official@example.com"))
        if user is None:
            user = User(email="official@example.com", full_name="Test Official",
                        hashed_password=hash_password("a-long-enough-password"),
                        role=Role.official)
            db.add(user)
        else:
            user.role = Role.official
        db.commit()
    return client.post("/api/v1/auth/login", json={
        "email": "official@example.com",
        "password": "a-long-enough-password"}).json()["access_token"]
