"""Builds the grounded fact sheet that every AI response must be based on.

This is the heart of AIRS's AI-safety story. The model receives a structured
block of *already-computed* values, each tagged with how it was produced
(OBSERVED / PREDICTED / ESTIMATED / SIMULATED). The system prompt forbids
producing any figure that is not in that block. So the language model does what
language models are good at — explaining and summarising — and never does what
it is bad at, which is arithmetic forecasting.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import City, Station
from app.domain.aqi import POLLUTANT_LABELS, categorize
from app.services import repository
from app.services.source_attribution import SOURCE_LABELS


def _fmt(value, unit: str = "", digits: int = 1) -> str:
    if value is None:
        return "not available"
    return f"{round(float(value), digits)}{unit}"


def build_station_context(db: Session, city: City, station: Station, *,
                          forecasts: list | None = None,
                          source_estimate=None,
                          history_hours: int = 24) -> dict:
    reading = repository.latest_air_quality(db, station.id)
    weather = repository.latest_weather(db, station.id)
    traffic = repository.latest_traffic(db, station.id)
    series = repository.air_quality_series(db, station.id, hours=history_hours)

    prev = series[-2] if len(series) >= 2 else None
    day_ago = series[0] if series else None

    facts: list[str] = []
    facts.append(f"[OBSERVED] Location: {station.name}, {city.name}. "
                 f"Zone type: {station.zone_type.value.replace('_', ' ')}. "
                 f"Population in catchment: {station.population_exposed or 'unknown'}.")

    if reading:
        category = categorize(reading.aqi)
        facts.append(
            f"[OBSERVED] Current AQI (US EPA scale) at "
            f"{reading.observed_at.isoformat()}: {_fmt(reading.aqi, digits=0)}"
            + (f" — category '{category.label}'." if category else ".")
            + f" Dominant pollutant: {reading.dominant_pollutant or 'unknown'}."
            + f" Data provenance: {reading.provenance.value}.")
        pollutants = ", ".join(
            f"{POLLUTANT_LABELS[p]} {_fmt(getattr(reading, p))}"
            for p in ("pm25", "pm10", "no2", "so2", "co", "o3")
            if getattr(reading, p, None) is not None)
        if pollutants:
            facts.append(f"[OBSERVED] Concentrations: {pollutants} "
                         f"(PM in µg/m³, NO₂/SO₂/O₃ in ppb, CO in ppm).")
        if prev and prev.aqi is not None and reading.aqi is not None:
            facts.append(f"[OBSERVED] AQI one hour ago: {_fmt(prev.aqi, digits=0)} "
                         f"(change {reading.aqi - prev.aqi:+.0f}).")
        if day_ago and day_ago.aqi is not None and reading.aqi is not None:
            facts.append(f"[OBSERVED] AQI {history_hours} hours ago: "
                         f"{_fmt(day_ago.aqi, digits=0)} "
                         f"(change {reading.aqi - day_ago.aqi:+.0f}).")
    else:
        facts.append("[OBSERVED] No current air-quality reading is available.")

    if weather:
        facts.append(
            f"[OBSERVED] Weather: temperature {_fmt(weather.temperature_c, '°C')}, "
            f"humidity {_fmt(weather.humidity_pct, '%')}, "
            f"wind {_fmt(weather.wind_speed_mps, ' m/s')}, "
            f"pressure {_fmt(weather.pressure_hpa, ' hPa')}, "
            f"ventilation index {_fmt(weather.ventilation_index, '', 2)} "
            f"(0 = stagnant, 1 = well mixed).")
    if traffic and traffic.congestion_index is not None:
        facts.append(f"[OBSERVED] Traffic congestion index: "
                     f"{_fmt(traffic.congestion_index, '', 2)} (0–1 scale), "
                     f"provenance {traffic.provenance.value}.")

    if forecasts:
        for fc in forecasts:
            facts.append(
                f"[PREDICTED] In {fc.horizon_hours}h ({fc.target_at.isoformat()}): "
                f"AQI {_fmt(fc.aqi, digits=0)} "
                f"(80% range {_fmt(fc.aqi_lower, digits=0)}–{_fmt(fc.aqi_upper, digits=0)}), "
                f"PM2.5 {_fmt(fc.pm25)}, confidence {fc.confidence}, "
                f"model tier '{fc.tier}'.")

    if source_estimate:
        shares = ", ".join(f"{SOURCE_LABELS[k]} {v}%"
                           for k, v in sorted(source_estimate.contributions.items(),
                                              key=lambda kv: kv[1], reverse=True))
        facts.append(f"[ESTIMATED] Likely source contributions: {shares}. "
                     f"Method: {source_estimate.method}, "
                     f"confidence {source_estimate.confidence}.")
        for item in source_estimate.evidence[:5]:
            facts.append(f"[ESTIMATED] Evidence — {item['signal']} = {item['value']}: "
                         f"{item['reading']}")

    return {
        "facts": facts,
        "station": {"id": station.id, "name": station.name, "code": station.code},
        "city": {"slug": city.slug, "name": city.name},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "has_observation": reading is not None,
    }


def context_to_prompt_block(context: dict) -> str:
    return "GROUNDED FACTS\n" + "\n".join(f"- {f}" for f in context["facts"])
