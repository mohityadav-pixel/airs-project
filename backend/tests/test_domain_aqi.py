"""The AQI mathematics is the foundation everything else stands on."""
import pytest

from app.domain.aqi import (categorize, concentration_to_index,
                             index_to_concentration, overall_aqi, trend_of)


@pytest.mark.parametrize("pollutant,concentration,expected", [
    ("pm25", 0.0, 0.0),
    ("pm25", 9.0, 50.0),
    ("pm25", 35.4, 100.0),
    ("pm10", 54.0, 50.0),
    ("co", 4.4, 50.0),
])
def test_breakpoint_edges_are_exact(pollutant, concentration, expected):
    assert concentration_to_index(pollutant, concentration) == pytest.approx(expected, abs=0.6)


def test_values_in_published_breakpoint_gaps_do_not_fall_through():
    """The EPA table jumps from 9.0 to 9.1 for PM2.5. A naive `c_lo <= x <= c_hi`
    match drops 9.05 to the top of the scale — the bug this guards against."""
    assert concentration_to_index("pm25", 9.05) < 60
    assert concentration_to_index("pm10", 54.5) < 60


def test_index_to_concentration_round_trips():
    for value in (12.0, 45.0, 84.0, 150.0):
        index = concentration_to_index("pm25", value)
        assert index_to_concentration("pm25", index) == pytest.approx(value, rel=0.02)


def test_extreme_values_clamp_rather_than_extrapolate():
    assert concentration_to_index("pm25", 5000) == 500.0


def test_overall_aqi_is_the_max_sub_index():
    aqi, dominant = overall_aqi({"pm25": 120.0, "no2": 40.0, "o3": None})
    assert (aqi, dominant) == (120.0, "pm25")


def test_overall_aqi_with_no_data():
    assert overall_aqi({"pm25": None}) == (None, None)


@pytest.mark.parametrize("aqi,expected", [
    (25, "Good"), (75, "Moderate"), (120, "Unhealthy for Sensitive Groups"),
    (175, "Unhealthy"), (250, "Very Unhealthy"), (400, "Hazardous"),
])
def test_categories(aqi, expected):
    assert categorize(aqi).label == expected


def test_category_boundaries_have_no_gaps():
    """150.4 sits between the published bands; it must not become Hazardous."""
    assert categorize(150.4).label == "Unhealthy for Sensitive Groups"
    assert categorize(200.7).label == "Very Unhealthy"


def test_trend_reports_stability_rather_than_noise():
    assert trend_of(101, 100)["direction"] == "stable"
    assert trend_of(140, 100)["direction"] == "worsening"
    assert trend_of(60, 100)["direction"] == "improving"
    assert trend_of(100, None)["direction"] == "unknown"
