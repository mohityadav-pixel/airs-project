"""Inference service.

Two-tier by design:

* **Trained tier** — the boosted models, when artifacts exist and the station
  has enough recent history.
* **Baseline tier** — a transparent persistence-plus-diurnal-climatology
  forecast used when a model is missing or the station is too new.

The tier used is returned to the caller and rendered in the UI. AIRS never
silently downgrades a forecast without saying so.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.db.models import Station
from app.domain.aqi import categorize
from ml import features as F
from ml.dataset import station_context, station_records
from ml.model import HORIZONS, MODEL_NAME, MODEL_VERSION, ForecastModel

logger = get_logger("airs.ml.predict")
_CACHE: dict[str, ForecastModel | None] = {}


def _get_model(target: str, horizon: int) -> ForecastModel | None:
    key = f"{target}_h{horizon}"
    if key not in _CACHE:
        _CACHE[key] = ForecastModel.load(target, horizon)
    return _CACHE[key]


def clear_model_cache() -> None:
    _CACHE.clear()


@dataclass
class PointForecast:
    target_at: datetime
    horizon_hours: int
    aqi: float | None
    aqi_lower: float | None
    aqi_upper: float | None
    pm25: float | None
    pm10: float | None
    confidence: float
    risk_category: str | None
    tier: str
    drivers: list[dict]


def _diurnal_profile(frame: pd.DataFrame) -> dict[int, float]:
    """Average multiplicative deviation of AQI by local hour, from history."""
    if frame.empty or "aqi" not in frame:
        return {}
    local_hours = frame.index.tz_convert("Asia/Kolkata").hour
    tmp = pd.DataFrame({"aqi": frame["aqi"].values, "hour": local_hours})
    overall = tmp["aqi"].mean()
    if not overall or np.isnan(overall):
        return {}
    return (tmp.groupby("hour")["aqi"].mean() / overall).to_dict()


def _baseline_forecast(frame: pd.DataFrame, horizon: int,
                       issued_at: datetime) -> PointForecast:
    """Persistence anchored to the station's own diurnal climatology, with a
    confidence band that widens with the horizon and with recent volatility."""
    latest = frame.iloc[-1]
    current = float(latest.get("aqi") or 0.0)
    profile = _diurnal_profile(frame)
    target_at = issued_at + timedelta(hours=horizon)
    target_hour = target_at.astimezone(timezone(timedelta(hours=5, minutes=30))).hour
    now_hour = issued_at.astimezone(timezone(timedelta(hours=5, minutes=30))).hour
    shape = (profile.get(target_hour, 1.0) / profile.get(now_hour, 1.0)
             if profile.get(now_hour) else 1.0)
    predicted = max(0.0, min(500.0, current * shape))

    volatility = float(frame["aqi"].tail(48).std() or 12.0)
    spread = volatility * (0.6 + horizon / 24.0)
    pm25 = float(latest.get("pm25") or np.nan)
    pm10 = float(latest.get("pm10") or np.nan)
    return PointForecast(
        target_at=target_at, horizon_hours=horizon,
        aqi=round(predicted, 1),
        aqi_lower=round(max(0.0, predicted - spread), 1),
        aqi_upper=round(min(500.0, predicted + spread), 1),
        pm25=round(pm25 * shape, 1) if pm25 == pm25 else None,
        pm10=round(pm10 * shape, 1) if pm10 == pm10 else None,
        confidence=round(max(0.25, 0.62 - horizon / 240.0), 2),
        risk_category=(categorize(predicted).label if predicted else None),
        tier="baseline",
        drivers=[{"feature": "persistence + diurnal climatology",
                  "value": round(shape, 3)}])


def forecast_station(db: Session, station: Station,
                     horizons: tuple[int, ...] = HORIZONS,
                     history_days: int = 30) -> tuple[list[PointForecast], dict]:
    records = station_records(db, station.id, days=history_days)
    frame = F.build_frame(records)
    if frame.empty:
        return [], {"model_name": MODEL_NAME, "model_version": MODEL_VERSION,
                    "tier": "unavailable"}
    ctx = station_context(db, station)
    frame = F.add_features(frame, **ctx)
    issued_at = frame.index[-1].to_pydatetime()

    results: list[PointForecast] = []
    tiers: set[str] = set()

    for horizon in horizons:
        aqi_model = _get_model("aqi", horizon)
        if aqi_model is None or len(frame) < 30:
            fc = _baseline_forecast(frame, horizon, issued_at)
            tiers.add(fc.tier)
            results.append(fc)
            continue

        X = frame[F.feature_columns(frame)].tail(1)
        aqi_pred = aqi_model.predict(X)
        pm25_model = _get_model("pm25", horizon)
        pm10_model = _get_model("pm10", horizon)
        pm25 = float(pm25_model.predict(X)["mean"][0]) if pm25_model else None
        pm10 = float(pm10_model.predict(X)["mean"][0]) if pm10_model else None

        mean = float(aqi_pred["mean"][0])
        lower = float(aqi_pred["lower"][0])
        upper = float(aqi_pred["upper"][0])
        # Confidence from band width relative to the value: a tight band on a
        # high value is a confident forecast.
        width = max(upper - lower, 1.0)
        confidence = float(np.clip(1.0 - width / max(mean, 40.0) / 2.2, 0.2, 0.95))

        tiers.add("model")
        results.append(PointForecast(
            target_at=issued_at + timedelta(hours=horizon),
            horizon_hours=horizon, aqi=round(mean, 1),
            aqi_lower=round(lower, 1), aqi_upper=round(upper, 1),
            pm25=round(pm25, 1) if pm25 is not None else None,
            pm10=round(pm10, 1) if pm10 is not None else None,
            confidence=round(confidence, 2),
            risk_category=categorize(mean).label if mean else None,
            tier="model", drivers=aqi_model.drivers(X)))

    meta = {"model_name": MODEL_NAME, "model_version": MODEL_VERSION,
            "tier": "model" if tiers == {"model"} else
                    ("mixed" if len(tiers) > 1 else next(iter(tiers), "unavailable")),
            "issued_at": issued_at, "history_hours": len(frame)}
    return results, meta


def hourly_curve(db: Session, station: Station, hours: int = 24) -> list[PointForecast]:
    """A smooth hour-by-hour curve for charting: model points at 6/24/72h,
    monotone-interpolated in between so the line has no artificial kinks."""
    horizons = tuple(range(1, hours + 1))
    anchors, _ = forecast_station(db, station, horizons=(6, 24, 72))
    if not anchors:
        return []
    records = station_records(db, station.id, days=7)
    frame = F.add_features(F.build_frame(records), **station_context(db, station))
    if frame.empty:
        return []
    issued_at = frame.index[-1].to_pydatetime()
    current = float(frame["aqi"].iloc[-1] or 0)

    known_h = [0] + [a.horizon_hours for a in anchors]
    known_v = [current] + [a.aqi or current for a in anchors]
    known_lo = [current] + [a.aqi_lower or current for a in anchors]
    known_hi = [current] + [a.aqi_upper or current for a in anchors]
    profile = _diurnal_profile(frame)

    out: list[PointForecast] = []
    for h in horizons:
        base = float(np.interp(h, known_h, known_v))
        lo = float(np.interp(h, known_h, known_lo))
        hi = float(np.interp(h, known_h, known_hi))
        target_at = issued_at + timedelta(hours=h)
        hour_local = target_at.astimezone(timezone(timedelta(hours=5, minutes=30))).hour
        # Re-impose the diurnal shape the linear interpolation would flatten.
        shape = profile.get(hour_local, 1.0)
        neighbours = [profile.get((hour_local + d) % 24, 1.0) for d in (-2, -1, 0, 1, 2)]
        shape = shape / (sum(neighbours) / len(neighbours) or 1.0)
        value = float(np.clip(base * (0.75 + 0.25 * shape), 0, 500))
        out.append(PointForecast(
            target_at=target_at, horizon_hours=h, aqi=round(value, 1),
            aqi_lower=round(min(lo, value), 1), aqi_upper=round(max(hi, value), 1),
            pm25=None, pm10=None,
            confidence=round(max(0.2, 0.9 - h / 120.0), 2),
            risk_category=categorize(value).label,
            tier="model-interpolated", drivers=[]))
    return out
