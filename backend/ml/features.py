"""Feature engineering for the AQI forecasting models.

The feature set is deliberately small and physically motivated rather than
exhaustive. With hourly city data, the dominant signal is autoregressive
(pollution is persistent), the second is meteorological (wind and the nocturnal
inversion decide whether emissions accumulate), and the third is the diurnal
traffic cycle. Adding hundreds of weak features to that would buy variance, not
accuracy.

Every feature is computable **at prediction time from data that already exists**
— no future weather is assumed, because a free API forecast would introduce an
error source we cannot audit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAG_HOURS = (1, 2, 3, 6, 12, 24)
ROLLING_WINDOWS = (6, 24)

BASE_COLUMNS = [
    "aqi", "pm25", "pm10", "no2", "so2", "co", "o3",
    "temperature_c", "humidity_pct", "pressure_hpa", "wind_speed_mps",
    "rain_1h_mm", "clouds_pct", "ventilation_index", "congestion_index",
]

ZONE_ORDER = ["residential", "green", "mixed", "commercial",
              "construction", "traffic_corridor", "industrial"]


def _cyclical(series: pd.Series, period: int, name: str) -> pd.DataFrame:
    radians = 2 * np.pi * series / period
    return pd.DataFrame({f"{name}_sin": np.sin(radians),
                         f"{name}_cos": np.cos(radians)}, index=series.index)


def build_frame(records: list[dict]) -> pd.DataFrame:
    """`records` are joined air-quality + weather + traffic rows for ONE station,
    ordered by time, each with an ``observed_at`` key."""
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["observed_at"] = pd.to_datetime(df["observed_at"], utc=True)
    df = df.sort_values("observed_at").drop_duplicates("observed_at")
    df = df.set_index("observed_at")

    # Regularise to a strict hourly grid so lags mean what they say. Short gaps
    # are interpolated; long gaps stay NaN and the model handles them natively.
    df = df.resample("1h").mean(numeric_only=True)
    for col in BASE_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    df[BASE_COLUMNS] = df[BASE_COLUMNS].interpolate(limit=3, limit_direction="both")
    return df


def add_features(df: pd.DataFrame, *, zone: str = "mixed",
                 near_road: bool = False, near_industrial: bool = False,
                 near_construction: bool = False,
                 city_baseline: float = 50.0) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()

    for col in ("aqi", "pm25", "pm10", "no2"):
        for lag in LAG_HOURS:
            out[f"{col}_lag{lag}"] = out[col].shift(lag)
        for window in ROLLING_WINDOWS:
            out[f"{col}_roll{window}"] = out[col].rolling(window, min_periods=2).mean()
    # Momentum: is the pollutant already climbing?
    out["aqi_delta_1h"] = out["aqi"] - out["aqi"].shift(1)
    out["aqi_delta_3h"] = out["aqi"] - out["aqi"].shift(3)
    out["aqi_delta_24h"] = out["aqi"] - out["aqi"].shift(24)
    out["pm_ratio"] = out["pm25"] / out["pm10"].replace(0, np.nan)

    # Meteorology, including the accumulated calm that precedes a smog episode.
    out["wind_roll6"] = out["wind_speed_mps"].rolling(6, min_periods=2).mean()
    out["ventilation_roll6"] = out["ventilation_index"].rolling(6, min_periods=2).mean()
    out["calm_hours_24"] = (out["wind_speed_mps"] < 1.5).rolling(24, min_periods=2).sum()

    idx = out.index
    local = idx.tz_convert("Asia/Kolkata")
    hour = pd.Series(local.hour, index=idx)
    out = pd.concat([out, _cyclical(hour, 24, "hour"),
                     _cyclical(pd.Series(local.dayofweek, index=idx), 7, "dow"),
                     _cyclical(pd.Series(local.month, index=idx), 12, "month")], axis=1)
    out["is_weekend"] = (pd.Series(local.dayofweek, index=idx) >= 5).astype(int)
    out["is_night"] = ((hour >= 21) | (hour <= 6)).astype(int)

    out["zone_rank"] = float(ZONE_ORDER.index(zone) if zone in ZONE_ORDER else 2)
    out["near_road"] = int(near_road)
    out["near_industrial"] = int(near_industrial)
    out["near_construction"] = int(near_construction)
    out["city_baseline"] = float(city_baseline)
    return out


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Exclude raw future-unknown columns; keep engineered + current-hour state."""
    drop = {"aqi"}
    return [c for c in df.columns if c not in drop]


def make_supervised(df: pd.DataFrame, horizon_hours: int,
                    target: str = "aqi") -> tuple[pd.DataFrame, pd.Series]:
    """y is the target `horizon_hours` into the future; X is everything known now."""
    y = df[target].shift(-horizon_hours)
    X = df[feature_columns(df)]
    mask = y.notna() & X.notna().sum(axis=1).gt(len(X.columns) * 0.5)
    return X[mask], y[mask]
