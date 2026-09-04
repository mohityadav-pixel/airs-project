"""Create tables and load reference data (idempotent)."""
from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.base import Base
from app.db.models import City, Intervention, Role, Station, User, ZoneType
from app.db.seed_data import CITIES, INTERVENTIONS
from app.db.session import SessionLocal, engine
from app.core.security import hash_password

logger = get_logger("airs.init_db")


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_reference_data(db: Session) -> None:
    for c in CITIES:
        city = db.scalar(select(City).where(City.slug == c["slug"]))
        if city is None:
            city = City(slug=c["slug"], name=c["name"], country=c["country"],
                        latitude=c["latitude"], longitude=c["longitude"],
                        population=c["population"], default_zoom=c["default_zoom"],
                        waqi_keyword=c["waqi_keyword"], aqi_scale=c["aqi_scale"])
            db.add(city)
            db.flush()
        for (code, name, lat, lon, zone, pop, road, ind, con) in c["stations"]:
            existing = db.scalar(select(Station).where(Station.city_id == city.id,
                                                       Station.code == code))
            if existing:
                continue
            db.add(Station(city_id=city.id, code=code, name=name, latitude=lat,
                           longitude=lon, zone_type=ZoneType(zone),
                           population_exposed=pop, near_major_road=road,
                           near_industrial=ind, near_construction=con))
    for i in INTERVENTIONS:
        if db.scalar(select(Intervention).where(Intervention.key == i["key"])):
            continue
        db.add(Intervention(**i))
    db.commit()


def seed_admin(db: Session) -> None:
    """Create a bootstrap admin only when explicitly requested via env vars."""
    email = os.getenv("AIRS_BOOTSTRAP_ADMIN_EMAIL")
    password = os.getenv("AIRS_BOOTSTRAP_ADMIN_PASSWORD")
    if not (email and password):
        return
    if db.scalar(select(User).where(User.email == email.lower())):
        return
    db.add(User(email=email.lower(), full_name="AIRS Administrator",
                hashed_password=hash_password(password), role=Role.admin))
    db.commit()
    logger.info("bootstrap admin created")


def init() -> None:
    create_tables()
    with SessionLocal() as db:
        seed_reference_data(db)
        seed_admin(db)


if __name__ == "__main__":
    from app.core.logging_config import configure_logging
    configure_logging()
    init()
    print("Database initialised.")
