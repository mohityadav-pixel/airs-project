"""Estimate which sources are driving the pollution at a station right now.

This is **receptor-style reasoning, not a dispersion model**. Real source
apportionment needs chemical speciation (elemental carbon, potassium, metals)
that no free feed provides. What we do have is: the ratios between pollutants,
the time of day, the weather, the traffic state and what is physically around
the station. Those constrain the answer more than people expect:

* NO2 and CO are combustion-and-traffic tracers with a short lifetime; a NO2
  spike co-located with congestion is traffic, not regional transport.
* SO2 is overwhelmingly industrial (fuel sulphur) in Indian cities.
* A wide PM10/PM2.5 gap means coarse crustal material — road dust, construction,
  demolition — not combustion.
* A high PM2.5 with *low* NO2 and low wind is accumulation, not fresh emission:
  the meteorology is the story.
* Biomass burning raises PM2.5 and CO together while leaving NO2 comparatively
  low, and is strongly seasonal and nocturnal.

Each signal contributes evidence-weighted votes; the result is normalised to
shares and returned with the evidence that produced it, so an official can see
*why* the model said "construction dust", not just that it did. Output is
explicitly labelled an estimate everywhere it surfaces.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

SOURCES = ("traffic", "industrial", "construction_dust", "biomass_burning",
           "meteorological_accumulation", "other")

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class SourceEstimate:
    contributions: dict[str, float]
    evidence: list[dict]
    confidence: float
    method: str = "ratio-and-context heuristic v1"


def _zone_prior(zone: str, near_road: bool, near_industrial: bool,
                near_construction: bool) -> dict[str, float]:
    prior = {"traffic": 0.26, "industrial": 0.14, "construction_dust": 0.18,
             "biomass_burning": 0.10, "meteorological_accumulation": 0.22,
             "other": 0.10}
    if zone == "traffic_corridor" or near_road:
        prior["traffic"] += 0.12
    if zone == "industrial" or near_industrial:
        prior["industrial"] += 0.14
    if zone == "construction" or near_construction:
        prior["construction_dust"] += 0.10
    if zone == "green":
        prior["traffic"] -= 0.06
        prior["meteorological_accumulation"] += 0.04
    return prior


def estimate_sources(*, pm25: float | None, pm10: float | None, no2: float | None,
                     so2: float | None, co: float | None, o3: float | None,
                     wind_speed_mps: float | None, ventilation_index: float | None,
                     congestion_index: float | None, observed_at: datetime,
                     zone: str = "mixed", near_road: bool = False,
                     near_industrial: bool = False,
                     near_construction: bool = False) -> SourceEstimate:
    votes = _zone_prior(zone, near_road, near_industrial, near_construction)
    evidence: list[dict] = []
    signals = 0

    local = observed_at.astimezone(IST) if observed_at.tzinfo else observed_at
    hour = local.hour
    month = local.month

    # 1. Coarse-fraction gap -> mechanical dust.
    if pm25 and pm10 and pm25 > 0:
        ratio = pm10 / pm25
        signals += 1
        if ratio > 2.4:
            votes["construction_dust"] += 0.20
            evidence.append({"signal": "PM10/PM2.5 ratio", "value": round(ratio, 2),
                             "reading": "Wide coarse fraction — mechanical dust "
                                        "(road, construction, demolition) rather "
                                        "than combustion."})
        elif ratio < 1.5:
            votes["biomass_burning"] += 0.10
            votes["traffic"] += 0.08
            evidence.append({"signal": "PM10/PM2.5 ratio", "value": round(ratio, 2),
                             "reading": "Fine-dominated aerosol — combustion "
                                        "sources rather than dust."})

    # 2. NO2 with congestion -> fresh traffic emission.
    if no2 is not None:
        signals += 1
        if no2 > 45 and (congestion_index or 0) > 0.55:
            votes["traffic"] += 0.22
            evidence.append({"signal": "NO₂ + congestion", "value": round(no2, 1),
                             "reading": "Elevated NO₂ coinciding with heavy "
                                        "congestion — fresh vehicular emission."})
        elif no2 < 18 and (pm25 or 0) > 60:
            votes["meteorological_accumulation"] += 0.18
            evidence.append({"signal": "High PM with low NO₂", "value": round(no2, 1),
                             "reading": "Particulate is high while the traffic "
                                        "tracer is low — this is accumulated or "
                                        "transported aerosol, not new emission."})

    # 3. SO2 -> industrial fuel burning.
    if so2 is not None:
        signals += 1
        if so2 > 25:
            votes["industrial"] += 0.20
            evidence.append({"signal": "SO₂", "value": round(so2, 1),
                             "reading": "SO₂ above background points to fuel "
                                        "sulphur from industrial combustion."})

    # 4. CO with modest NO2 -> biomass / open burning.
    if co is not None and no2 is not None:
        signals += 1
        if co > 1.6 and no2 < 45:
            votes["biomass_burning"] += 0.18
            evidence.append({"signal": "CO relative to NO₂", "value": round(co, 2),
                             "reading": "CO elevated without a matching NO₂ rise — "
                                        "characteristic of biomass or waste burning."})

    # 5. Stagnation.
    if wind_speed_mps is not None:
        signals += 1
        if wind_speed_mps < 1.5 or (ventilation_index is not None and ventilation_index < 0.18):
            votes["meteorological_accumulation"] += 0.24
            evidence.append({"signal": "Ventilation", "value": round(wind_speed_mps, 2),
                             "reading": "Near-calm air with a shallow mixing layer — "
                                        "emissions are accumulating rather than dispersing."})
        elif wind_speed_mps > 4.0:
            votes["meteorological_accumulation"] -= 0.10
            evidence.append({"signal": "Ventilation", "value": round(wind_speed_mps, 2),
                             "reading": "Well-ventilated conditions — what is measured "
                                        "is being emitted locally, not accumulated."})

    # 6. Time of day and season.
    if 7 <= hour <= 10 or 18 <= hour <= 21:
        votes["traffic"] += 0.10
        evidence.append({"signal": "Time of day", "value": hour,
                         "reading": "Peak commuting window."})
    if 22 <= hour or hour <= 5:
        votes["biomass_burning"] += 0.06
        votes["construction_dust"] -= 0.04
    if month in (11, 12, 1):
        votes["biomass_burning"] += 0.08
        evidence.append({"signal": "Season", "value": month,
                         "reading": "Winter — crop-residue and heating fires "
                                    "contribute far more than the annual average."})
    if month in (7, 8, 9):
        votes["construction_dust"] -= 0.06

    # 7. Ozone is secondary; it should never be attributed to a primary source.
    if o3 is not None and o3 > 70:
        evidence.append({"signal": "O₃", "value": round(o3, 1),
                         "reading": "Ozone is formed photochemically downwind, so it "
                                    "reflects regional precursors rather than any "
                                    "single local source."})

    cleaned = {k: max(0.0, v) for k, v in votes.items()}
    total = sum(cleaned.values()) or 1.0
    contributions = {k: round(v / total * 100, 1) for k, v in cleaned.items()}
    # Fix rounding drift so the shares always total exactly 100.
    drift = round(100.0 - sum(contributions.values()), 1)
    if drift:
        top = max(contributions, key=contributions.get)
        contributions[top] = round(contributions[top] + drift, 1)

    confidence = round(min(0.82, 0.32 + 0.09 * signals + 0.02 * len(evidence)), 2)
    return SourceEstimate(contributions=contributions, evidence=evidence,
                          confidence=confidence)


SOURCE_LABELS = {
    "traffic": "Traffic",
    "industrial": "Industrial activity",
    "construction_dust": "Construction & road dust",
    "biomass_burning": "Biomass / waste burning",
    "meteorological_accumulation": "Weather & stagnation",
    "other": "Other / unresolved",
}
