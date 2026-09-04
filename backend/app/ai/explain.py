"""Explanation engine.

Two tiers, and the tier is always reported:

* **LLM tier** — Gemini rewrites the computed evidence into readable prose.
* **Deterministic tier** — when no key is configured or the call fails, AIRS
  still explains itself from the same evidence using templates. The product does
  not lose a core feature because an external service is down; it loses only the
  fluency of the wording.
"""
from __future__ import annotations

import json

from app.ai import gemini
from app.ai.prompts import EXPLANATION_SYSTEM
from app.core.errors import AIUnavailable
from app.domain.aqi import categorize


def _parse_json(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned[4:] if cleaned.lower().startswith("json") else cleaned
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _deterministic(*, current_aqi, forecast, weather, source_estimate,
                   station_name: str) -> dict:
    direction = "stay about the same"
    delta = None
    if current_aqi is not None and forecast and forecast.aqi is not None:
        delta = forecast.aqi - current_aqi
        if delta > 10:
            direction = "worsen"
        elif delta < -10:
            direction = "improve"

    factors: list[str] = []
    if weather is not None:
        if weather.wind_speed_mps is not None and weather.wind_speed_mps < 1.8:
            factors.append("Light winds are letting pollution accumulate")
        elif weather.wind_speed_mps is not None and weather.wind_speed_mps > 4:
            factors.append("Steady winds are dispersing pollution")
        if weather.ventilation_index is not None and weather.ventilation_index < 0.25:
            factors.append("A shallow overnight mixing layer is trapping emissions "
                           "near the ground")
    if source_estimate:
        top = max(source_estimate.contributions,
                  key=source_estimate.contributions.get)
        share = source_estimate.contributions[top]
        factors.append(f"{top.replace('_', ' ').title()} is the largest estimated "
                       f"contributor at about {share:.0f}%")
    if forecast and forecast.horizon_hours >= 12:
        factors.append("The evening traffic peak and the overnight inversion "
                       "usually raise levels after sunset")
    if not factors:
        factors.append("Conditions are close to this location's recent average")

    category = categorize(forecast.aqi) if forecast and forecast.aqi else None
    headline = (f"AQI at {station_name} is expected to {direction}"
                + (f" to about {forecast.aqi:.0f}" if forecast and forecast.aqi else "")
                + (f" ({category.label})" if category else ""))

    horizon = f"over the next {forecast.horizon_hours} hours" if forecast else "shortly"
    lead = {
        "worsen": f"Conditions {horizon} favour accumulation rather than dispersal",
        "improve": f"Conditions {horizon} favour dispersal",
        "stay about the same": f"Nothing in the data {horizon} points to a large move "
                               "in either direction",
    }[direction]
    delta_note = ("" if delta is None
                  else f" That is {abs(delta):.0f} AQI "
                       f"{'above' if delta > 0 else 'below'} the current reading.")
    simple = f"{lead}. " + " ".join(f + "." for f in factors[:2]) + delta_note
    technical_bits = []
    if weather is not None:
        technical_bits.append(
            f"wind {weather.wind_speed_mps} m/s, ventilation index "
            f"{weather.ventilation_index}")
    if forecast is not None:
        technical_bits.append(
            f"forecast 80% interval {forecast.aqi_lower}–{forecast.aqi_upper} "
            f"at +{forecast.horizon_hours}h from the {forecast.tier} tier")
    technical = ("Drivers: " + "; ".join(technical_bits) + "."
                 if technical_bits else "Insufficient data for a technical breakdown.")

    return {"headline": headline[:120], "simple": simple, "technical": technical,
            "factors": factors[:5], "tier": "deterministic",
            "kind": "estimated"}


def explain_forecast(*, current_aqi, forecast, weather, source_estimate,
                     station_name: str, facts: list[str]) -> dict:
    """Always returns an explanation; ``tier`` says how it was produced."""
    fallback = _deterministic(current_aqi=current_aqi, forecast=forecast,
                              weather=weather, source_estimate=source_estimate,
                              station_name=station_name)
    if not gemini.available():
        return fallback
    prompt = ("GROUNDED FACTS\n" + "\n".join(f"- {f}" for f in facts)
              + "\n\nExplain what is expected next at this location and why.")
    try:
        raw = gemini.generate(EXPLANATION_SYSTEM, prompt, temperature=0.25,
                              max_output_tokens=700)
    except AIUnavailable:
        return fallback
    parsed = _parse_json(raw)
    if not parsed or "headline" not in parsed:
        return fallback
    return {"headline": str(parsed.get("headline", ""))[:160],
            "simple": str(parsed.get("simple", "")),
            "technical": str(parsed.get("technical", "")),
            "factors": [str(f) for f in (parsed.get("factors") or [])][:5],
            "tier": "llm", "kind": "ai_generated"}
