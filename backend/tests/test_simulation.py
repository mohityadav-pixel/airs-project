"""The simulator is the feature most likely to mislead if it is wrong."""
import pytest

from app.services.simulation import LeverInput, simulate

CONC = {"pm25": 100.0, "pm10": 200.0, "no2": 50.0, "so2": 10.0,
        "co": 1.0, "o3": 30.0}
TRAFFIC_HEAVY = {"traffic": 60.0, "industrial": 10.0, "construction_dust": 10.0,
                 "biomass_burning": 5.0, "meteorological_accumulation": 10.0,
                 "other": 5.0}
TRAFFIC_FREE = {"traffic": 0.0, "industrial": 10.0, "construction_dust": 60.0,
                "biomass_burning": 5.0, "meteorological_accumulation": 20.0,
                "other": 5.0}
TRAFFIC_LEVER = {"pm25": 0.85, "pm10": 0.70, "no2": 0.95, "co": 0.92}


def _run(shares, magnitude=30.0, **kw):
    return simulate(concentrations=CONC, source_shares=shares,
                    levers=[LeverInput(key="traffic_reduction",
                                       magnitude=magnitude,
                                       effectiveness=TRAFFIC_LEVER,
                                       label="Traffic", max_magnitude=60.0)],
                    wind_speed_mps=3.0, **kw)


def test_a_lever_cannot_reduce_pollution_its_source_did_not_cause():
    """The core correctness property: cutting traffic where traffic contributes
    nothing must produce essentially no benefit."""
    result = _run(TRAFFIC_FREE)
    assert result.deltas["improvement_pct"] == pytest.approx(0.0, abs=0.5)
    assert result.warnings, "a no-op lever should tell the user why"


def test_benefit_scales_with_the_attributable_source_share():
    heavy = _run(TRAFFIC_HEAVY).deltas["improvement_pct"]
    light = _run({**TRAFFIC_HEAVY, "traffic": 15.0}).deltas["improvement_pct"]
    assert heavy > light > 0


def test_a_30_percent_traffic_cut_does_not_cut_aqi_by_30_percent():
    """The classic naive-simulator error."""
    improvement = _run(TRAFFIC_HEAVY, magnitude=30.0).deltas["improvement_pct"]
    assert 0 < improvement < 20


def test_stagnant_air_suppresses_the_realised_benefit():
    calm = simulate(concentrations=CONC, source_shares=TRAFFIC_HEAVY,
                    levers=[LeverInput("traffic_reduction", 30.0, TRAFFIC_LEVER)],
                    wind_speed_mps=0.3, ventilation_index=0.05)
    breezy = simulate(concentrations=CONC, source_shares=TRAFFIC_HEAVY,
                      levers=[LeverInput("traffic_reduction", 30.0, TRAFFIC_LEVER)],
                      wind_speed_mps=5.0, ventilation_index=0.9)
    assert breezy.deltas["improvement_pct"] > calm.deltas["improvement_pct"]


def test_aqi_is_recomputed_from_concentrations_not_scaled_directly():
    result = _run(TRAFFIC_HEAVY)
    from app.domain.aqi import overall_aqi, concentration_to_index
    expected, _ = overall_aqi({k: concentration_to_index(k, v)
                               for k, v in result.simulated["concentrations"].items()
                               if v is not None})
    assert result.simulated["aqi"] == pytest.approx(expected, abs=0.2)


def test_stacked_levers_cannot_eliminate_all_pollution():
    result = simulate(
        concentrations=CONC, source_shares=TRAFFIC_HEAVY,
        levers=[LeverInput("traffic_reduction", 60.0, TRAFFIC_LEVER),
                LeverInput("industrial_emission_control", 50.0, {"pm25": 0.8}),
                LeverInput("construction_halt", 100.0, {"pm25": 0.55, "pm10": 0.85}),
                LeverInput("road_dust_suppression", 100.0, {"pm10": 0.6}),
                LeverInput("biomass_burning_control", 100.0, {"pm25": 0.88})],
        wind_speed_mps=4.0)
    assert result.simulated["aqi"] > 0
    assert result.simulated["concentrations"]["pm25"] > 0


def test_confidence_falls_as_the_intervention_gets_more_aggressive():
    mild = _run(TRAFFIC_HEAVY, magnitude=10.0).confidence
    extreme = _run(TRAFFIC_HEAVY, magnitude=60.0).confidence
    assert extreme < mild


def test_output_is_always_labelled_as_an_estimate():
    assert "not a guaranteed" in _run(TRAFFIC_HEAVY).caveat.lower()
