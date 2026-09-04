"""Train the AQI / PM2.5 / PM10 forecasters across every station.

One pooled model per (target, horizon) rather than one per station: stations
share physics, and pooling lets a station with two weeks of data borrow strength
from one with six months. Station identity enters through zone and proximity
features instead of a separate model.

    python -m ml.train --days 180
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.logging_config import configure_logging, get_logger  # noqa: E402
from app.db.models import Station  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from ml import features as F  # noqa: E402
from ml.dataset import station_context, station_records  # noqa: E402
from ml.model import HORIZONS, TARGETS, ForecastModel, write_manifest  # noqa: E402
from sqlalchemy import select  # noqa: E402

logger = get_logger("airs.ml.train")


def build_training_frame(days: int) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with SessionLocal() as db:
        stations = list(db.scalars(select(Station).where(Station.is_active.is_(True))))
        for station in stations:
            records = station_records(db, station.id, days=days)
            if len(records) < 72:
                continue
            ctx = station_context(db, station)
            frame = F.add_features(F.build_frame(records), **ctx)
            frame["__station_id"] = station.id
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames).sort_index()


def main(days: int) -> int:
    frame = build_training_frame(days)
    if frame.empty:
        print("No training data. Run scripts/backfill_history.py first.")
        return 1

    reports = []
    for target in TARGETS:
        for horizon in HORIZONS:
            per_station = []
            for _, group in frame.groupby("__station_id"):
                group = group.drop(columns=["__station_id"])
                X, y = F.make_supervised(group, horizon, target=target)
                if len(X) < 50:
                    continue
                per_station.append((X, y))
            if not per_station:
                continue
            X = pd.concat([x for x, _ in per_station])
            y = pd.concat([s for _, s in per_station])
            order = X.index.argsort()
            X, y = X.iloc[order], y.iloc[order]

            model = ForecastModel(target, horizon)
            report = model.fit(X, y)
            model.save()
            reports.append(report)
            print(f"{target:>5} h={horizon:>2}  MAE={report.mae:<7} "
                  f"R2={report.r2:<7} persistence MAE={report.baseline_mae:<7} "
                  f"skill={report.skill_vs_persistence}")
    write_manifest(reports)
    print(f"\nTrained {len(reports)} models -> ml/artifacts/")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=180)
    args = parser.parse_args()
    configure_logging()
    raise SystemExit(main(args.days))
