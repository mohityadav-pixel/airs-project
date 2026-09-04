"""Personalised (non-medical) health guidance.

Thresholds follow the US EPA AQI cautionary statements, tightened for the
groups that the evidence says respond at lower concentrations. This is public-
health guidance, not diagnosis, and every response carries that disclaimer.
"""
from __future__ import annotations

from app.db.models import SensitivityGroup
from app.domain.aqi import categorize

DISCLAIMER = ("General public-health guidance based on current air quality. "
              "AIRS is not a medical device and does not provide diagnosis or "
              "treatment. Follow your clinician's advice for any existing "
              "condition.")

# How much earlier each group should act, as an AQI offset.
GROUP_OFFSET = {
    SensitivityGroup.general: 0,
    SensitivityGroup.outdoor_worker: 30,
    SensitivityGroup.athlete: 40,
    SensitivityGroup.child: 45,
    SensitivityGroup.elderly: 45,
    SensitivityGroup.sensitive: 60,
}

GROUP_LABEL = {
    SensitivityGroup.general: "General population",
    SensitivityGroup.outdoor_worker: "Outdoor worker",
    SensitivityGroup.athlete: "Athlete / heavy exerciser",
    SensitivityGroup.child: "Child",
    SensitivityGroup.elderly: "Older adult",
    SensitivityGroup.sensitive: "Person with asthma, COPD or heart disease",
}


def _band(effective: float) -> int:
    for i, upper in enumerate((50, 100, 150, 200, 300)):
        if effective <= upper:
            return i
    return 5


OUTDOOR = [
    "Normal outdoor activity is fine.",
    "Outdoor activity is fine; take it easy if you notice irritation.",
    "Shorten time outdoors and avoid the busiest roads.",
    "Limit outdoor time; move essential trips away from peak hours.",
    "Stay indoors where you can; go out only when necessary.",
    "Avoid going outside.",
]
EXERCISE = [
    "Any outdoor exercise is fine.",
    "Outdoor exercise is fine; consider easing off long high-intensity sessions.",
    "Move hard sessions indoors or to early morning; keep easy sessions short.",
    "Do not exercise outdoors — the ventilation rate multiplies your dose.",
    "No outdoor exertion of any kind.",
    "No outdoor exertion. Keep indoor activity light too.",
]
MASK = [
    "No mask needed.",
    "No mask needed for most people.",
    "A well-fitted N95/FFP2 helps on busy streets and long trips.",
    "Wear a well-fitted N95/FFP2 outdoors.",
    "N95/FFP2 outdoors, and keep trips short.",
    "N95/FFP2 for any unavoidable time outdoors.",
]
VENTILATION = [
    "Open windows freely.",
    "Open windows freely; close them at the evening traffic peak if you are near a main road.",
    "Ventilate at midday when air is best; keep windows closed overnight.",
    "Keep windows closed; ventilate briefly at the cleanest hour of the day.",
    "Keep windows and doors closed. Use a HEPA purifier if you have one.",
    "Seal the home as far as possible and run a HEPA purifier continuously.",
]
EXPOSURE = [
    ["Nothing specific to do today."],
    ["Prefer side streets over main roads when walking or cycling."],
    ["Avoid main roads at the 8–10 am and 6–9 pm peaks.",
     "Keep car windows up and set ventilation to recirculate in traffic."],
    ["Shift errands to the cleanest part of the day (usually early afternoon).",
     "Keep children's outdoor play short."],
    ["Postpone non-essential outdoor work.",
     "Create one clean room at home with a purifier and closed windows."],
    ["Treat this as an emergency exposure: stay indoors, seal gaps, run filtration."],
]


def advisory(aqi: float | None, group: SensitivityGroup = SensitivityGroup.general,
             *, dominant_pollutant: str | None = None) -> dict:
    if aqi is None:
        return {"available": False, "disclaimer": DISCLAIMER,
                "message": "No current air-quality reading is available for this "
                           "location, so no guidance can be given."}
    effective = aqi + GROUP_OFFSET[group]
    band = _band(effective)
    category = categorize(aqi)

    notes = []
    if dominant_pollutant in ("pm25", "pm10"):
        notes.append("Particulate matter is the dominant pollutant, so filtration "
                     "(N95 outdoors, HEPA indoors) is the effective control.")
    elif dominant_pollutant == "o3":
        notes.append("Ozone peaks in the afternoon and is not filtered by a cloth "
                     "or surgical mask; shifting activity to the morning helps more.")
    elif dominant_pollutant == "no2":
        notes.append("NO₂ is highest beside traffic — a few streets away from a main "
                     "road makes a measurable difference.")

    return {
        "available": True,
        "group": group.value,
        "group_label": GROUP_LABEL[group],
        "aqi": aqi,
        "effective_aqi_for_group": round(effective, 1),
        "category": {"key": category.key, "label": category.label,
                     "color": category.color} if category else None,
        "risk_level": ["low", "low", "moderate", "high", "very high", "severe"][band],
        "outdoor_activity": OUTDOOR[band],
        "exercise": EXERCISE[band],
        "mask": MASK[band],
        "ventilation": VENTILATION[band],
        "exposure_reduction": EXPOSURE[band],
        "notes": notes,
        "disclaimer": DISCLAIMER,
    }
