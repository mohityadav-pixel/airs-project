"""Generate the historical time series AIRS needs to train and to show trends.

Why this exists
---------------
Free air-quality APIs expose only the *current* hour. A forecasting model needs
months of history, and the analytics pages need something to plot on day one.
So AIRS backfills history from its physical synthetic model.

Every backfilled row is written with ``provenance='demo'`` and the API reports
that to the UI. Live rows accumulate alongside them from the moment the
scheduler starts running, and the ``/api/v1/system/status`` endpoint reports the
live/demo split so nobody can mistake one for the other.

Usage:
    python -m scripts.backfill_history --days 120
    python -m scripts.backfill_history --days 30 --city delhi
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.logging_config import configure_logging  # noqa: E402
from app.db.init_db import init  # noqa: E402
from app.db.models import (AirQualityReading, City, Provenance, Station,  # noqa: E402
                            TrafficReading, WeatherReading)
from app.db.session import SessionLocal  # noqa: E402
from app.services.providers.demo import (synth_air_quality, synth_traffic,  # noqa: E402
                                          synth_weather)
from app.services.providers.openweather import ventilation_index  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def backfill(days: int, city_slug: str | None, replace: bool) -> None:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    with SessionLocal() as db:
        cities = list(db.scalars(
            select(City).where(City.slug == city_slug) if city_slug else select(City)))
        if not cities:
            raise SystemExit(f"No city matched {city_slug!r}.")

        for city in cities:
            stations = list(db.scalars(
                select(Station).where(Station.city_id == city.id)))
            for station in stations:
                if replace:
                    for model in (AirQualityReading, WeatherReading, TrafficReading):
                        db.execute(delete(model).where(
                            model.station_id == station.id,
                            model.provenance == Provenance.demo))
                existing = set(db.scalars(select(AirQualityReading.observed_at).where(
                    AirQualityReading.station_id == station.id,
                    AirQualityReading.observed_at >= start)))
                zone = station.zone_type.value
                batch = []
                ts = start
                while ts <= now:
                    if ts not in existing:
                        aq = synth_air_quality(city.slug, station.code, zone, ts)
                        wx = synth_weather(station.code, ts)
                        tr = synth_traffic(station.code, zone, ts)
                        local_hour = ts.astimezone(IST).hour
                        batch.append(AirQualityReading(
                            station_id=station.id, observed_at=ts, ingested_at=now,
                            provenance=Provenance.demo, aqi=aq.aqi,
                            dominant_pollutant=aq.dominant_pollutant,
                            pm25=aq.pm25, pm10=aq.pm10, no2=aq.no2, so2=aq.so2,
                            co=aq.co, o3=aq.o3, sub_indices=aq.sub_indices,
                            quality_flags=[]))
                        batch.append(WeatherReading(
                            station_id=station.id, observed_at=ts, ingested_at=now,
                            provenance=Provenance.demo,
                            temperature_c=wx.temperature_c, humidity_pct=wx.humidity_pct,
                            pressure_hpa=wx.pressure_hpa, wind_speed_mps=wx.wind_speed_mps,
                            wind_deg=wx.wind_deg, rain_1h_mm=wx.rain_1h_mm,
                            clouds_pct=wx.clouds_pct, visibility_m=wx.visibility_m,
                            condition=wx.condition,
                            ventilation_index=ventilation_index(
                                wx.wind_speed_mps, wx.temperature_c, local_hour)))
                        batch.append(TrafficReading(
                            station_id=station.id, observed_at=ts, ingested_at=now,
                            provenance=Provenance.demo,
                            congestion_index=tr.congestion_index,
                            speed_ratio=tr.speed_ratio,
                            vehicle_volume_est=tr.vehicle_volume_est))
                    ts += timedelta(hours=1)
                    if len(batch) >= 3000:
                        db.add_all(batch); db.commit(); batch = []
                if batch:
                    db.add_all(batch); db.commit()
                print(f"  {city.slug}/{station.code} backfilled")
    print("Backfill complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=120)
    parser.add_argument("--city", type=str, default=None)
    parser.add_argument("--replace", action="store_true",
                        help="Delete existing demo rows first (live rows are kept).")
    args = parser.parse_args()
    configure_logging()
    init()
    backfill(args.days, args.city, args.replace)
