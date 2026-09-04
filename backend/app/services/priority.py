"""Intervention Priority Score — transparent by construction.

    Priority = 100 x (Severity^0.9 x Exposure^0.7 x PredictedRisk^0.8
                      x Impact^1.0 x Urgency^0.6) ^ (1/4)

Every factor is normalised to 0..1 and every factor is returned alongside the
score, with the raw quantity it came from. The geometric-style combination is
deliberate: a zone that scores zero on exposure (nobody lives there) should not
be ranked highly no matter how filthy the air is, which an additive weighting
would allow. The fractional exponents keep any single factor from dominating.

Nothing here is a black box, and the API returns the breakdown so a city can
argue with the ranking — which is the point.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriorityBreakdown:
    score: float
    factors: dict[str, dict]
    rationale: str


def _norm(value: float | None, lo: float, hi: float, default: float = 0.4) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def compute_priority(*, current_aqi: float | None, predicted_aqi: float | None,
                     population_exposed: int | None,
                     modelled_improvement_pct: float | None,
                     hours_until_peak: float | None = None,
                     max_population: int = 500_000) -> PriorityBreakdown:
    severity = _norm(current_aqi, 50, 350)
    exposure = _norm(population_exposed, 0, max_population, default=0.3)

    deterioration = None
    if current_aqi and predicted_aqi is not None:
        deterioration = predicted_aqi - current_aqi
    predicted_risk = max(_norm(predicted_aqi, 50, 350),
                         _norm(deterioration, 0, 80, default=0.3) * 0.9)

    impact = _norm(modelled_improvement_pct, 0, 35, default=0.35)
    urgency = 1.0 - _norm(hours_until_peak, 0, 24, default=0.5)

    product = (max(severity, 0.01) ** 0.9 * max(exposure, 0.01) ** 0.7
               * max(predicted_risk, 0.01) ** 0.8 * max(impact, 0.01) ** 1.0
               * max(urgency, 0.01) ** 0.6)
    score = round(100 * product ** 0.25, 1)

    factors = {
        "pollution_severity": {"value": round(severity, 3), "weight": 0.9,
                                "raw": current_aqi,
                                "explanation": "Current AQI mapped onto 50–350."},
        "population_exposure": {"value": round(exposure, 3), "weight": 0.7,
                                 "raw": population_exposed,
                                 "explanation": "People in the station catchment."},
        "predicted_risk": {"value": round(predicted_risk, 3), "weight": 0.8,
                            "raw": predicted_aqi,
                            "explanation": "Forecast level and the size of the "
                                           "expected deterioration."},
        "intervention_impact": {"value": round(impact, 3), "weight": 1.0,
                                 "raw": modelled_improvement_pct,
                                 "explanation": "Modelled AQI improvement from the "
                                                "best available lever here."},
        "urgency": {"value": round(urgency, 3), "weight": 0.6,
                     "raw": hours_until_peak,
                     "explanation": "How soon the predicted peak arrives."},
    }
    driver = max(factors, key=lambda k: factors[k]["value"] * factors[k]["weight"])
    rationale = (f"Ranked mainly on {driver.replace('_', ' ')}; "
                 f"the score is the weighted geometric mean of all five factors, "
                 f"so a zone with no exposed population cannot rank highly on "
                 f"severity alone.")
    return PriorityBreakdown(score=score, factors=factors, rationale=rationale)
