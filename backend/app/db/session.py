from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("airs.db")

url = settings.database_url
connect_args: dict = {}

if url.startswith("sqlite"):
    # Make sure the directory for the sqlite file exists.
    path_part = url.split("///")[-1]
    if path_part and path_part != ":memory:":
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}

engine = create_engine(url, pool_pre_ping=True, future=True, connect_args=connect_args)

if url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False,
                            class_=Session, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
