from app.db.models import SensitivityGroup
from app.services.health import advisory


def test_sensitive_groups_are_advised_to_act_earlier():
    aqi = 110.0
    general = advisory(aqi, SensitivityGroup.general)
    child = advisory(aqi, SensitivityGroup.child)
    assert child["effective_aqi_for_group"] > general["effective_aqi_for_group"]
    assert child["exercise"] != general["exercise"]


def test_no_reading_means_no_guidance_rather_than_a_guess():
    result = advisory(None, SensitivityGroup.general)
    assert result["available"] is False
    assert "no guidance" in result["message"].lower()


def test_disclaimer_is_always_present():
    for aqi in (None, 20.0, 350.0):
        assert "not a medical device" in advisory(aqi, SensitivityGroup.general)["disclaimer"]


def test_guidance_gets_stricter_as_air_gets_worse():
    clean = advisory(20.0, SensitivityGroup.general)
    filthy = advisory(400.0, SensitivityGroup.general)
    assert clean["risk_level"] == "low"
    assert filthy["risk_level"] == "severe"
    assert "avoid" in filthy["outdoor_activity"].lower()


def test_ozone_guidance_mentions_that_masks_do_not_filter_it():
    result = advisory(140.0, SensitivityGroup.athlete, dominant_pollutant="o3")
    assert any("ozone" in note.lower() for note in result["notes"])
