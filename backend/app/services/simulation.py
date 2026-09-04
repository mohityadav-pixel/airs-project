"""What-if intervention simulator.

Method (stated plainly, because officials will act on this)
-----------------------------------------------------------
1. Start from the station's *current measured* concentrations.
2. Split each pollutant into source-attributed fractions using
   :mod:`app.services.source_attribution`.
3. A lever only acts on the fraction of the pollutant its source actually
   contributes — halving traffic cannot remove dust that traffic did not
   create. This is the single most important correctness property here and it
   is why naive "AQI x 0.7" simulators overstate benefit so badly.
4. Apply the lever's effectiveness against that source (stored per intervention
   in the database, so a city can recalibrate without a redeploy) to that
   fraction. Effectiveness and source share are kept as separate numbers on
   purpose: conflating them is what makes naive simulators claim a 30% traffic
   cut yields a 30% AQI drop.
5. Meteorology scales the achievable benefit: in stagnant air a local emission
   cut is partly cancelled by continued accumulation, so the realised benefit
   is discounted.
6. Recombine the pollutants and recompute AQI with the same EPA function used
   for observations — never by scaling the AQI number directly, which is
   mathematically wrong across breakpoints.
7. Combine multiple levers multiplicatively on the remaining fraction, with a
   diminishing-returns term, so stacking five levers cannot reach a 100%
   reduction.

The output is a **modelled estimate**, not a guarantee, and is labelled as such
in every response. The engine is intentionally a single class so it can be
replaced with a causal or CTM-based implementation without touching the API.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.aqi import categorize, concentration_to_index, overall_aqi

ENGINE_VERSION = "source-apportioned-effectiveness-1.0"

# Which source bucket each lever can actually act on.
LEVER_SOURCE = {
    "traffic_reduction": ("traffic",),
    "public_transport_boost": ("traffic",),
    "industrial_emission_control": ("industrial",),
    "construction_halt": ("construction_dust",),
    "road_dust_suppression": ("construction_dust",),
    "biomass_burning_control": ("biomass_burning",),
}

POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")


@dataclass
class LeverInput:
    key: str
    magnitude: float          # percent, 0..max_magnitude
    effectiveness: dict[str, float]
    label: str = ""
    max_magnitude: float = 100.0


@dataclass
class SimulationResult:
    baseline: dict
    simulated: dict
    deltas: dict
    per_lever: list[dict]
    assumptions: list[str]
    confidence: float
    engine_version: str = ENGINE_VERSION
    caveat: str = ("Modelled estimate based on measured concentrations, estimated "
                   "source shares and published intervention effectiveness figures. Not a "
                   "guaranteed real-world outcome.")
    warnings: list[str] = field(default_factory=list)


def _meteorology_discount(wind_speed_mps: float | None,
                          ventilation_index: float | None) -> float:
    """In stagnant air, a local emission cut delivers less than its nominal benefit."""
    if ventilation_index is not None:
        return 0.55 + 0.45 * min(max(ventilation_index, 0.0), 1.0)
    if wind_speed_mps is None:
        return 0.8
    return 0.55 + 0.45 * min(wind_speed_mps, 5.0) / 5.0


def simulate(*, concentrations: dict[str, float | None],
             source_shares: dict[str, float],
             levers: list[LeverInput],
             wind_speed_mps: float | None = None,
             ventilation_index: float | None = None,
             population_exposed: int | None = None) -> SimulationResult:
    baseline_conc = {p: concentrations.get(p) for p in POLLUTANTS}
    base_subs = {p: concentration_to_index(p, v)
                 for p, v in baseline_conc.items() if v is not None}
    base_subs = {k: v for k, v in base_subs.items() if v is not None}
    base_aqi, base_dominant = overall_aqi(base_subs)

    discount = _meteorology_discount(wind_speed_mps, ventilation_index)
    assumptions = [
        "Levers act only on the share of each pollutant attributed to their own "
        "source category.",
        f"Realised benefit is scaled by a meteorological factor of {discount:.2f} "
        "(stagnant air suppresses the benefit of local emission cuts).",
        "Per-source effectiveness figures are planning estimates stored per "
        "intervention and are re-calibratable per city.",
        "Ozone is secondary and responds non-linearly to NOx; its modelled change "
        "is treated as indicative only.",
    ]
    warnings: list[str] = []

    # Remaining fraction per pollutant after all levers, multiplicatively.
    remaining = {p: 1.0 for p in POLLUTANTS}
    per_lever: list[dict] = []

    for lever in levers:
        magnitude = max(0.0, min(lever.magnitude, lever.max_magnitude)) / 100.0
        if magnitude <= 0:
            continue
        sources = LEVER_SOURCE.get(lever.key, ())
        share = sum(source_shares.get(s, 0.0) for s in sources) / 100.0
        if share <= 0:
            warnings.append(
                f"{lever.label or lever.key}: this source is not currently "
                f"contributing at this location, so the modelled benefit is ~0.")
        lever_effect = {}
        for pollutant in POLLUTANTS:
            effectiveness = lever.effectiveness.get(pollutant, 0.0)
            if not effectiveness:
                continue
            # The lever removes `effectiveness` of the share its source
            # contributes, scaled by how hard it is applied and by how well the
            # atmosphere converts an emission cut into a concentration cut.
            reduction = abs(effectiveness) * magnitude * share * discount
            reduction = min(reduction, 0.85)     # never claim total elimination
            remaining[pollutant] *= (1.0 - reduction)
            lever_effect[pollutant] = round(reduction * 100, 2)
        per_lever.append({
            "key": lever.key, "label": lever.label or lever.key,
            "magnitude_pct": round(lever.magnitude, 1),
            "attributable_source_share_pct": round(share * 100, 1),
            "pollutant_reduction_pct": lever_effect,
        })

    sim_conc: dict[str, float | None] = {}
    for pollutant, value in baseline_conc.items():
        if value is None:
            sim_conc[pollutant] = None
            continue
        sim_conc[pollutant] = round(value * remaining[pollutant], 2)

    sim_subs = {p: concentration_to_index(p, v)
                for p, v in sim_conc.items() if v is not None}
    sim_subs = {k: v for k, v in sim_subs.items() if v is not None}
    sim_aqi, sim_dominant = overall_aqi(sim_subs)

    def _cat(value):
        c = categorize(value)
        return {"label": c.label, "color": c.color, "key": c.key} if c else None

    improvement = None
    if base_aqi and sim_aqi is not None:
        improvement = round((base_aqi - sim_aqi) / base_aqi * 100, 1)

    # Confidence falls as the intervention gets more aggressive — these figures
    # are calibrated near the observed operating point, not at 60% traffic cuts.
    aggressiveness = sum(min(l.magnitude, l.max_magnitude) for l in levers) / 100.0
    confidence = round(max(0.25, 0.72 - 0.10 * aggressiveness - 0.05 * len(levers)), 2)

    exposure = None
    if population_exposed and improvement:
        exposure = {
            "population_exposed": population_exposed,
            "note": "People within the station's catchment who would experience "
                    "the modelled change.",
        }

    return SimulationResult(
        baseline={"aqi": base_aqi, "category": _cat(base_aqi),
                  "dominant_pollutant": base_dominant,
                  "concentrations": baseline_conc, "sub_indices": base_subs},
        simulated={"aqi": sim_aqi, "category": _cat(sim_aqi),
                   "dominant_pollutant": sim_dominant,
                   "concentrations": sim_conc, "sub_indices": sim_subs},
        deltas={"aqi": round((sim_aqi - base_aqi), 1) if base_aqi and sim_aqi is not None else None,
                "improvement_pct": improvement,
                "pm25": (round(sim_conc["pm25"] - baseline_conc["pm25"], 1)
                         if baseline_conc.get("pm25") is not None else None),
                "pm10": (round(sim_conc["pm10"] - baseline_conc["pm10"], 1)
                         if baseline_conc.get("pm10") is not None else None),
                "category_changed": (_cat(base_aqi) or {}).get("key") != (_cat(sim_aqi) or {}).get("key"),
                "exposure": exposure},
        per_lever=per_lever, assumptions=assumptions, confidence=confidence,
        warnings=warnings)
