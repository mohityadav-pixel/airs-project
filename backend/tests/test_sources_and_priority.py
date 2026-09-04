from datetime import datetime, timezone

import pytest

from app.services.priority import compute_priority
from app.services.source_attribution import estimate_sources

NOON = datetime(2026, 3, 12, 6, 30, tzinfo=timezone.utc)   # 12:00 IST


def _estimate(**kw):
    base = dict(pm25=60.0, pm10=110.0, no2=30.0, so2=8.0, co=0.8, o3=25.0,
                wind_speed_mps=3.0, ventilation_index=0.5,
                congestion_index=0.4, observed_at=NOON)
    base.update(kw)
    return estimate_sources(**base)


def test_shares_always_total_one_hundred():
    for kwargs in ({}, {"so2": 60.0}, {"wind_speed_mps": 0.2},
                   {"pm10": 400.0}, {"no2": 90.0, "congestion_index": 0.9}):
        total = sum(_estimate(**kwargs).contributions.values())
        assert total == pytest.approx(100.0, abs=0.05)


def test_high_so2_points_at_industry():
    baseline = _estimate().contributions["industrial"]
    assert _estimate(so2=60.0).contributions["industrial"] > baseline


def test_wide_coarse_fraction_points_at_dust():
    baseline = _estimate().contributions["construction_dust"]
    assert _estimate(pm10=400.0).contributions["construction_dust"] > baseline


def test_no2_with_congestion_points_at_traffic():
    baseline = _estimate().contributions["traffic"]
    assert _estimate(no2=80.0, congestion_index=0.9).contributions["traffic"] > baseline


def test_calm_air_points_at_accumulation_not_at_a_source():
    calm = _estimate(wind_speed_mps=0.4, ventilation_index=0.05)
    breezy = _estimate(wind_speed_mps=6.0, ventilation_index=0.9)
    assert (calm.contributions["meteorological_accumulation"]
            > breezy.contributions["meteorological_accumulation"])


def test_every_estimate_carries_its_evidence():
    result = _estimate(so2=60.0, pm10=400.0)
    assert result.evidence
    assert all({"signal", "value", "reading"} <= set(item) for item in result.evidence)


def test_confidence_is_never_overstated():
    assert _estimate().confidence <= 0.82


def test_zone_context_shifts_the_prior():
    corridor = estimate_sources(pm25=60, pm10=110, no2=30, so2=8, co=0.8, o3=25,
                                wind_speed_mps=3, ventilation_index=0.5,
                                congestion_index=0.4, observed_at=NOON,
                                zone="traffic_corridor", near_road=True)
    park = estimate_sources(pm25=60, pm10=110, no2=30, so2=8, co=0.8, o3=25,
                            wind_speed_mps=3, ventilation_index=0.5,
                            congestion_index=0.4, observed_at=NOON, zone="green")
    assert corridor.contributions["traffic"] > park.contributions["traffic"]


# ── priority ───────────────────────────────────────────────────────────

def test_a_zone_with_nobody_in_it_cannot_outrank_a_populated_one():
    empty = compute_priority(current_aqi=320, predicted_aqi=340,
                             population_exposed=0, modelled_improvement_pct=20,
                             hours_until_peak=2)
    populated = compute_priority(current_aqi=180, predicted_aqi=200,
                                 population_exposed=400_000,
                                 modelled_improvement_pct=12, hours_until_peak=6)
    assert populated.score > empty.score


def test_every_factor_is_returned_with_its_reasoning():
    result = compute_priority(current_aqi=200, predicted_aqi=240,
                              population_exposed=250_000,
                              modelled_improvement_pct=10, hours_until_peak=4)
    assert set(result.factors) == {
        "pollution_severity", "population_exposure", "predicted_risk",
        "intervention_impact", "urgency"}
    assert all(f["explanation"] for f in result.factors.values())
    assert 0 <= result.score <= 100


def test_missing_inputs_do_not_crash_the_score():
    result = compute_priority(current_aqi=None, predicted_aqi=None,
                              population_exposed=None,
                              modelled_improvement_pct=None)
    assert 0 <= result.score <= 100
