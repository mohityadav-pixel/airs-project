"""Endpoint contract tests, including the provenance guarantee."""
import pytest

CITY = "delhi"


def test_status_reports_capabilities_honestly(client):
    body = client.get("/api/v1/system/status").json()
    assert body["data_mode"] == "demo"
    # No provider keys are set in the test environment.
    assert body["capabilities"]["air_quality_provider"] is False
    assert body["capabilities"]["ai_copilot"] is False
    assert body["data"]["demo_readings"] > 0


def test_cities_and_stations(client):
    cities = client.get("/api/v1/air-quality/cities").json()
    assert {c["slug"] for c in cities} >= {"delhi", "mumbai", "pune", "bengaluru"}
    stations = client.get(f"/api/v1/air-quality/stations?city={CITY}").json()
    assert len(stations) >= 8


def test_current_reading_shape(client):
    body = client.get(f"/api/v1/air-quality/current?city={CITY}").json()
    assert body["aqi"] is not None
    assert body["category"]["label"]
    assert body["pollutants"]
    assert body["provenance"]["kind"] == "observed"


@pytest.mark.parametrize("path,kind", [
    ("/api/v1/air-quality/current", "observed"),
    ("/api/v1/air-quality/summary", "observed"),
    ("/api/v1/air-quality/map", "observed"),
    ("/api/v1/air-quality/history", "observed"),
    ("/api/v1/predictions", "predicted"),
    ("/api/v1/pollution-sources", "estimated"),
    ("/api/v1/recommendations", "estimated"),
])
def test_every_data_response_declares_its_provenance(client, path, kind):
    """The product promise, enforced as a test: a client can always tell what
    kind of number it received, and whether it is live or demo."""
    body = client.get(f"{path}?city={CITY}").json()
    assert body["provenance"]["kind"] == kind
    assert body["provenance"]["mode"] == "demo"
    assert body["provenance"]["source"]


def test_demo_data_is_never_labelled_live(client):
    for path in ("/api/v1/air-quality/current", "/api/v1/predictions",
                 "/api/v1/pollution-sources"):
        assert client.get(f"{path}?city={CITY}").json()["provenance"]["mode"] != "live"


def test_predictions_have_intervals_and_beat_nothing_silently(client):
    body = client.get(f"/api/v1/predictions?city={CITY}").json()
    assert {h["horizon_hours"] for h in body["horizons"]} == {6, 24, 72}
    for h in body["horizons"]:
        assert h["aqi_lower"] <= h["aqi"] <= h["aqi_upper"]
        assert 0 < h["confidence"] <= 1
        assert h["tier"] in {"model", "baseline"}
    assert body["curve"]
    assert body["explanation"]["headline"]


def test_source_shares_total_one_hundred(client):
    body = client.get(f"/api/v1/pollution-sources?city={CITY}").json()
    total = sum(c["share_pct"] for c in body["contributions"])
    assert total == pytest.approx(100.0, abs=0.05)


def test_history_respects_the_requested_window(client):
    body = client.get(f"/api/v1/air-quality/history?city={CITY}&hours=24").json()
    assert 0 < len(body["points"]) <= 26
    assert body["stats"]["average_aqi"] is not None


def test_simulation_endpoint(client):
    body = client.post("/api/v1/simulation", json={
        "city_slug": CITY,
        "levers": [{"key": "traffic_reduction", "magnitude": 30}]}).json()
    assert body["provenance"]["kind"] == "simulated"
    assert body["simulated"]["aqi"] <= body["baseline"]["aqi"]
    assert body["assumptions"]
    assert body["per_lever"][0]["attributable_source_share_pct"] >= 0


def test_simulation_rejects_an_unknown_lever(client):
    response = client.post("/api/v1/simulation", json={
        "city_slug": CITY, "levers": [{"key": "wishful_thinking", "magnitude": 50}]})
    assert response.status_code == 400


def test_simulation_rejects_an_out_of_range_magnitude(client):
    response = client.post("/api/v1/simulation", json={
        "city_slug": CITY,
        "levers": [{"key": "traffic_reduction", "magnitude": 500}]})
    assert response.status_code == 422


def test_recommendations_carry_reasoning_and_a_scored_priority(client):
    body = client.get(f"/api/v1/recommendations?city={CITY}").json()
    actions = body["immediate"] + body["short_term"]
    assert actions
    for action in actions:
        assert action["reason"] and action["expected_impact"]
        assert 0 <= action["priority_score"] <= 100
        assert action["priority_factors"]
    # The same lever must not be repeated once per station.
    keys = [a["intervention_key"] for a in body["immediate"]]
    assert len(keys) == len(set(keys))


def test_alerts_answer_what_why_and_what_to_do(client):
    for alert in client.get(f"/api/v1/alerts?city={CITY}").json():
        assert alert["what_happened"] and alert["why_it_matters"]
        assert alert["recommended_action"]
        assert alert["severity"] in {"info", "watch", "warning", "emergency"}


def test_copilot_fails_cleanly_without_a_key(client):
    """No Gemini key is configured in tests: the endpoint must refuse rather
    than invent an answer, and must not take the rest of the API down."""
    response = client.post("/api/v1/copilot", json={
        "question": "Why is the AQI high?", "city_slug": CITY})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_unavailable"
    assert client.get("/api/v1/system/health").status_code == 200


def test_unknown_city_is_a_clean_400(client):
    response = client.get("/api/v1/air-quality/current?city=atlantis")
    assert response.status_code == 400
    assert "atlantis" in response.json()["error"]["message"].lower()


def test_errors_never_leak_internals(client):
    body = client.get("/api/v1/air-quality/current?city=atlantis").json()
    serialized = str(body)
    assert "Traceback" not in serialized
    assert "sqlite" not in serialized.lower()


def test_analytics_endpoints(client):
    correlations = client.get(f"/api/v1/analytics/correlations?city={CITY}").json()
    assert correlations["correlations"]
    wind = next(c for c in correlations["correlations"]
                if c["driver"] == "wind_speed_mps")
    # Physics: wind disperses pollution, so the relationship must be negative.
    assert wind["vs_aqi"] is None or wind["vs_aqi"] < 0

    profile = client.get(f"/api/v1/analytics/hourly-profile?city={CITY}").json()
    assert len(profile["by_hour"]) == 24
    assert len(profile["by_weekday"]) == 7

    ranking = client.get(f"/api/v1/analytics/station-ranking?city={CITY}").json()
    averages = [s["average_aqi"] for s in ranking["stations"]]
    assert averages == sorted(averages, reverse=True)


def test_health_advisory_varies_by_group(client):
    general = client.get(f"/api/v1/health-advisory?city={CITY}&group=general").json()
    sensitive = client.get(
        f"/api/v1/health-advisory?city={CITY}&group=sensitive").json()
    assert sensitive["effective_aqi_for_group"] > general["effective_aqi_for_group"]
    assert general["disclaimer"]
