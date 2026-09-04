"""Turns observations + forecasts + source estimates into ranked city actions.

Rules first, language model second. The *decision* of which lever to pull is
made deterministically here — from the estimated source mix, the forecast and
the simulated benefit — because an official needs the same inputs to always
produce the same recommendation. The LLM (see :mod:`app.ai.explain`) only
rewrites the resulting reasoning into readable prose; it never invents an action
or a number.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.priority import compute_priority
from app.services.simulation import LeverInput, simulate
from app.services.source_attribution import SOURCE_LABELS

# Which lever answers which dominant source, and on what horizon.
PLAYBOOK: list[dict] = [
    {"source": "traffic", "key": "traffic_reduction", "horizon": "immediate",
     "action": "Restrict and re-route traffic through the affected corridor",
     "detail": "Divert freight and through-traffic away from the hotspot during "
               "the peak window, and hold the restriction until the forecast peak "
               "has passed."},
    {"source": "traffic", "key": "public_transport_boost", "horizon": "short",
     "action": "Raise bus and metro frequency on the affected corridor",
     "detail": "Add peak-hour services and suspend fares on the corridor so the "
               "restriction has somewhere for the displaced trips to go."},
    {"source": "construction_dust", "key": "road_dust_suppression", "horizon": "immediate",
     "action": "Deploy mechanised sweeping and water sprinkling on the hotspot corridor",
     "detail": "Coarse-fraction dust responds within hours, but the effect decays; "
               "schedule repeat passes through the episode."},
    {"source": "construction_dust", "key": "construction_halt", "horizon": "short",
     "action": "Suspend earthworks, demolition and open material handling in the zone",
     "detail": "Issue stop-work notices for uncovered material handling and "
               "require covered transport of aggregates."},
    {"source": "industrial", "key": "industrial_emission_control", "horizon": "immediate",
     "action": "Inspect and throttle high-emission industrial units in the airshed",
     "detail": "Prioritise units with a history of non-compliance; require "
               "scrubber operation logs for the episode window."},
    {"source": "biomass_burning", "key": "biomass_burning_control", "horizon": "immediate",
     "action": "Enforce against open waste and biomass burning in the catchment",
     "detail": "Night patrols in the catchment, plus a collection alternative so "
               "the waste has somewhere else to go."},
]

LONG_TERM: list[dict] = [
    {"action": "Redesign the corridor for lower idling and fewer conflict points",
     "reason": "Repeated NO₂ and CO peaks at commuting hours indicate stop-start "
               "congestion rather than total vehicle volume.",
     "expected_impact": "Structural reduction in traffic-attributed NO₂ at this "
                        "receptor; benefit accrues over months, not hours.",
     "trigger": "traffic"},
    {"action": "Extend green buffer and paved-shoulder coverage along the hotspot",
     "reason": "A persistently wide PM10/PM2.5 gap indicates a continuous "
               "resuspension source, which sweeping only suppresses temporarily.",
     "expected_impact": "Reduces the baseline coarse fraction that dust "
                        "suppression currently has to fight every day.",
     "trigger": "construction_dust"},
    {"action": "Tighten continuous emissions monitoring and reporting for the "
               "industrial cluster",
     "reason": "SO₂ elevated above urban background points to fuel sulphur that "
               "is not currently observable in real time.",
     "expected_impact": "Makes the industrial share measurable rather than "
                        "inferred, improving every downstream decision.",
     "trigger": "industrial"},
    {"action": "Expand the monitoring network in under-instrumented wards",
     "reason": "Source attribution confidence is limited by station density; "
               "hotspots between stations are currently invisible.",
     "expected_impact": "Higher-confidence attribution and earlier hotspot "
                        "detection across the city.",
     "trigger": "*"},
]


@dataclass
class GeneratedRecommendation:
    action: str
    reason: str
    expected_impact: str
    intervention_key: str | None
    time_horizon: str
    priority_score: float
    priority_factors: dict
    confidence: float
    station_id: int | None
    station_name: str | None
    modelled_improvement_pct: float | None


def recommend_for_station(*, station, current_aqi: float | None,
                          predicted_aqi: float | None,
                          concentrations: dict[str, float | None],
                          source_shares: dict[str, float],
                          interventions: dict[str, dict],
                          wind_speed_mps: float | None,
                          ventilation_index: float | None,
                          hours_until_peak: float | None = None,
                          max_population: int = 500_000
                          ) -> list[GeneratedRecommendation]:
    """One station in, a ranked list of actions out."""
    out: list[GeneratedRecommendation] = []
    ranked_sources = sorted(source_shares.items(), key=lambda kv: kv[1], reverse=True)
    top_sources = [s for s, share in ranked_sources if share >= 12.0][:3]

    for play in PLAYBOOK:
        if play["source"] not in top_sources:
            continue
        meta = interventions.get(play["key"])
        if not meta:
            continue
        # Model the benefit of a realistic, not heroic, magnitude.
        magnitude = min(30.0, meta.get("max_magnitude", 100.0))
        result = simulate(
            concentrations=concentrations, source_shares=source_shares,
            levers=[LeverInput(key=play["key"], magnitude=magnitude,
                               effectiveness=meta["effectiveness"],
                               label=meta["label"],
                               max_magnitude=meta.get("max_magnitude", 100.0))],
            wind_speed_mps=wind_speed_mps, ventilation_index=ventilation_index,
            population_exposed=station.population_exposed)
        improvement = result.deltas.get("improvement_pct")
        share = source_shares.get(play["source"], 0.0)

        priority = compute_priority(
            current_aqi=current_aqi, predicted_aqi=predicted_aqi,
            population_exposed=station.population_exposed,
            modelled_improvement_pct=improvement,
            hours_until_peak=hours_until_peak, max_population=max_population)

        reason = (f"{SOURCE_LABELS[play['source']]} is estimated to contribute "
                  f"{share:.0f}% of the current pollutant load at {station.name}"
                  + (f", and AQI is forecast to reach {predicted_aqi:.0f}"
                     if predicted_aqi else "") + ". " + play["detail"])
        impact = (f"A {magnitude:.0f}% intervention models to roughly "
                  f"{improvement:.1f}% lower AQI at this receptor "
                  f"({result.baseline['aqi']:.0f} → {result.simulated['aqi']:.0f})."
                  if improvement is not None and result.simulated.get("aqi") is not None
                  else "Modelled benefit could not be quantified from current data.")

        out.append(GeneratedRecommendation(
            action=play["action"], reason=reason, expected_impact=impact,
            intervention_key=play["key"], time_horizon=play["horizon"],
            priority_score=priority.score, priority_factors=priority.factors,
            confidence=round(min(result.confidence, 0.8), 2),
            station_id=station.id, station_name=station.name,
            modelled_improvement_pct=improvement))

    out.sort(key=lambda r: r.priority_score, reverse=True)
    return out


def long_term_actions(dominant_sources: list[str]) -> list[GeneratedRecommendation]:
    out = []
    for item in LONG_TERM:
        if item["trigger"] != "*" and item["trigger"] not in dominant_sources:
            continue
        out.append(GeneratedRecommendation(
            action=item["action"], reason=item["reason"],
            expected_impact=item["expected_impact"], intervention_key=None,
            time_horizon="long", priority_score=35.0,
            priority_factors={"note": {"value": None, "weight": 0,
                                        "explanation": "Structural actions are not "
                                        "scored on the episode-response scale."}},
            confidence=0.55, station_id=None, station_name=None,
            modelled_improvement_pct=None))
    return out
