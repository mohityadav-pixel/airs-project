from datetime import datetime, timedelta, timezone

from app.services import validation
from app.services.providers.base import AirQualityObservation


def _obs(**kw):
    base = dict(observed_at=datetime.now(timezone.utc), aqi=100.0,
                dominant_pollutant="pm25", pm25=40.0, pm10=90.0)
    base.update(kw)
    return AirQualityObservation(**base)


def test_impossible_values_are_nulled_and_flagged():
    result = validation.validate_air_quality(_obs(pm25=-5.0))
    assert result.pm25 is None
    assert "pm25_out_of_range" in result.quality_flags


def test_fine_fraction_above_coarse_is_flagged_not_silently_accepted():
    result = validation.validate_air_quality(_obs(pm25=120.0, pm10=40.0))
    assert "pm25_exceeds_pm10" in result.quality_flags


def test_old_readings_are_marked_stale():
    old = datetime.now(timezone.utc) - timedelta(hours=12)
    assert "stale" in validation.validate_air_quality(_obs(observed_at=old)).quality_flags


def test_completely_empty_reading_is_not_usable():
    empty = validation.validate_air_quality(
        _obs(aqi=None, pm25=None, pm10=None))
    assert not validation.is_usable(empty)


def test_a_good_reading_survives_untouched():
    result = validation.validate_air_quality(_obs())
    assert result.pm25 == 40.0
    assert validation.is_usable(result)
