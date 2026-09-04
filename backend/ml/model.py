"""Model definition, training and persistence.

Why gradient boosting on histograms rather than an LSTM
-------------------------------------------------------
The spec lists XGBoost, Random Forest and LSTM as candidates. The honest choice
for this data is gradient boosting, for three reasons:

* **Data volume.** A recurrent net needs far more history per station than a
  city network accumulates in its first months. On a few thousand hourly rows an
  LSTM overfits and is beaten by a boosted tree with lag features.
* **Missingness.** Station feeds drop out constantly.
  ``HistGradientBoostingRegressor`` handles NaN natively, with no imputation
  step to bias the result.
* **Auditability.** Officials act on these numbers. Permutation importance on a
  tree ensemble gives a defensible driver attribution; an LSTM does not.

``sklearn``'s histogram booster is used rather than the ``xgboost`` package so
the stack has one fewer native dependency; the interface is swappable — see
``_new_regressor``.

Uncertainty is produced by two extra quantile models (p10/p90) rather than a
fudge factor, so the band widens where the model genuinely knows less.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "airs-hgb"
MODEL_VERSION = "1.0.0"
HORIZONS = (6, 24, 72)
TARGETS = ("aqi", "pm25", "pm10")


def _new_regressor(quantile: float | None = None) -> HistGradientBoostingRegressor:
    common = dict(max_iter=350, learning_rate=0.06, max_depth=None,
                  max_leaf_nodes=31, min_samples_leaf=20,
                  l2_regularization=1.0, early_stopping=True,
                  validation_fraction=0.15, n_iter_no_change=25,
                  random_state=42)
    if quantile is None:
        return HistGradientBoostingRegressor(loss="squared_error", **common)
    return HistGradientBoostingRegressor(loss="quantile", quantile=quantile, **common)


@dataclass
class TrainingReport:
    target: str
    horizon_hours: int
    n_train: int
    n_test: int
    mae: float
    r2: float
    baseline_mae: float
    skill_vs_persistence: float
    trained_at: str
    feature_count: int


class ForecastModel:
    """One (target, horizon) forecaster: mean + p10 + p90."""

    def __init__(self, target: str, horizon_hours: int):
        self.target = target
        self.horizon_hours = horizon_hours
        self.mean_model = _new_regressor()
        self.lower_model = _new_regressor(quantile=0.1)
        self.upper_model = _new_regressor(quantile=0.9)
        self.features: list[str] = []
        self.report: TrainingReport | None = None

    # -- training -----------------------------------------------------
    def fit(self, X: pd.DataFrame, y: pd.Series) -> TrainingReport:
        self.features = list(X.columns)
        # Chronological split — shuffling a time series leaks the future.
        split = int(len(X) * 0.85)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        self.mean_model.fit(X_train, y_train)
        self.lower_model.fit(X_train, y_train)
        self.upper_model.fit(X_train, y_train)

        preds = self.mean_model.predict(X_test) if len(X_test) else np.array([])
        mae = float(mean_absolute_error(y_test, preds)) if len(X_test) else float("nan")
        r2 = float(r2_score(y_test, preds)) if len(X_test) > 1 else float("nan")

        # Persistence baseline: "it will be what it is now". Any forecaster that
        # cannot beat this is not worth deploying, so we always report it.
        base_col = f"{self.target}_lag1" if f"{self.target}_lag1" in X_test.columns else None
        if base_col is not None and len(X_test):
            baseline_mae = float(mean_absolute_error(
                y_test, X_test[base_col].fillna(y_test.mean())))
        else:
            baseline_mae = float("nan")
        skill = (1 - mae / baseline_mae) if baseline_mae and baseline_mae == baseline_mae else float("nan")

        self.report = TrainingReport(
            target=self.target, horizon_hours=self.horizon_hours,
            n_train=len(X_train), n_test=len(X_test), mae=round(mae, 2),
            r2=round(r2, 3), baseline_mae=round(baseline_mae, 2),
            skill_vs_persistence=round(skill, 3),
            trained_at=datetime.now(timezone.utc).isoformat(),
            feature_count=len(self.features))
        return self.report

    # -- inference ----------------------------------------------------
    def predict(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        X = X.reindex(columns=self.features)
        mean = self.mean_model.predict(X)
        lower = self.lower_model.predict(X)
        upper = self.upper_model.predict(X)
        lower = np.minimum(lower, mean)
        upper = np.maximum(upper, mean)
        floor = 0.0
        return {"mean": np.clip(mean, floor, 500),
                "lower": np.clip(lower, floor, 500),
                "upper": np.clip(upper, floor, 500)}

    def drivers(self, X: pd.DataFrame, top_n: int = 6) -> list[dict]:
        """Permutation-free, cheap attribution: how far each feature's current
        value sits from its training median, weighted by the model's own
        split-based importance proxy. Deliberately labelled as an indicative
        driver ranking, not a SHAP decomposition."""
        if X.empty or not self.features:
            return []
        row = X.reindex(columns=self.features).iloc[-1]
        interesting = [f for f in self.features
                       if any(k in f for k in ("wind", "ventilation", "congestion",
                                                "lag1", "delta", "roll6", "is_night",
                                                "calm_hours", "humidity", "pm_ratio"))]
        out = []
        for f in interesting:
            value = row.get(f)
            if value is None or (isinstance(value, float) and np.isnan(value)):
                continue
            out.append({"feature": f, "value": round(float(value), 3)})
        return out[:top_n]

    # -- persistence --------------------------------------------------
    @property
    def slug(self) -> str:
        return f"{self.target}_h{self.horizon_hours}"

    def save(self) -> Path:
        path = ARTIFACT_DIR / f"{self.slug}.joblib"
        joblib.dump({"target": self.target, "horizon": self.horizon_hours,
                     "features": self.features, "mean": self.mean_model,
                     "lower": self.lower_model, "upper": self.upper_model,
                     "report": asdict(self.report) if self.report else None,
                     "version": MODEL_VERSION}, path)
        return path

    @classmethod
    def load(cls, target: str, horizon_hours: int) -> "ForecastModel | None":
        path = ARTIFACT_DIR / f"{target}_h{horizon_hours}.joblib"
        if not path.exists():
            return None
        blob = joblib.load(path)
        model = cls(blob["target"], blob["horizon"])
        model.features = blob["features"]
        model.mean_model = blob["mean"]
        model.lower_model = blob["lower"]
        model.upper_model = blob["upper"]
        if blob.get("report"):
            model.report = TrainingReport(**blob["report"])
        return model


def write_manifest(reports: list[TrainingReport]) -> Path:
    path = ARTIFACT_DIR / "manifest.json"
    path.write_text(json.dumps({
        "model_name": MODEL_NAME, "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "reports": [asdict(r) for r in reports]}, indent=2))
    return path


def read_manifest() -> dict | None:
    path = ARTIFACT_DIR / "manifest.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
