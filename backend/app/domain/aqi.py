"""Air Quality Index mathematics.

Two scales are implemented because AIRS needs both:

* **US EPA** — the scale the WAQI/AQICN feed reports. WAQI's ``iaqi`` block
  contains *sub-indices* (already-converted AQI numbers), **not** raw
  concentrations. To show a citizen "PM2.5 = 84 ug/m3" we therefore have to
  invert the EPA piecewise-linear function. That inversion is exact, and is
  the only honest way to report concentrations from that feed.
* **CPCB (India)** — the National Air Quality Index used by Indian cities and
  the scale officials actually act on.

Both are piecewise linear over published breakpoints:

    I = (I_hi - I_lo) / (C_hi - C_lo) * (C - C_lo) + I_lo
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

Scale = Literal["us_epa", "cpcb"]

# (C_lo, C_hi, I_lo, I_hi) — concentration units per pollutant noted below.
# PM2.5 / PM10 in ug/m3; O3, NO2, SO2 in ppb; CO in ppm.
US_EPA_BREAKPOINTS: dict[str, list[tuple[float, float, float, float]]] = {
    "pm25": [(0.0, 9.0, 0, 50), (9.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
             (55.5, 125.4, 151, 200), (125.5, 225.4, 201, 300), (225.5, 325.4, 301, 500)],
    "pm10": [(0, 54, 0, 50), (55, 154, 51, 100), (155, 254, 101, 150),
             (255, 354, 151, 200), (355, 424, 201, 300), (425, 604, 301, 500)],
    "o3":   [(0, 54, 0, 50), (55, 70, 51, 100), (71, 85, 101, 150),
             (86, 105, 151, 200), (106, 200, 201, 300)],
    "no2":  [(0, 53, 0, 50), (54, 100, 51, 100), (101, 360, 101, 150),
             (361, 649, 151, 200), (650, 1249, 201, 300), (1250, 2049, 301, 500)],
    "so2":  [(0, 35, 0, 50), (36, 75, 51, 100), (76, 185, 101, 150),
             (186, 304, 151, 200), (305, 604, 201, 300), (605, 1004, 301, 500)],
    "co":   [(0.0, 4.4, 0, 50), (4.5, 9.4, 51, 100), (9.5, 12.4, 101, 150),
             (12.5, 15.4, 151, 200), (15.5, 30.4, 201, 300), (30.5, 50.4, 301, 500)],
}

# CPCB National AQI — all concentrations in ug/m3 except CO (mg/m3).
CPCB_BREAKPOINTS: dict[str, list[tuple[float, float, float, float]]] = {
    "pm25": [(0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200),
             (91, 120, 201, 300), (121, 250, 301, 400), (251, 500, 401, 500)],
    "pm10": [(0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200),
             (251, 350, 201, 300), (351, 430, 301, 400), (431, 600, 401, 500)],
    "no2":  [(0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200),
             (181, 280, 201, 300), (281, 400, 301, 400), (401, 600, 401, 500)],
    "so2":  [(0, 40, 0, 50), (41, 80, 51, 100), (81, 380, 101, 200),
             (381, 800, 201, 300), (801, 1600, 301, 400), (1601, 2400, 401, 500)],
    "o3":   [(0, 50, 0, 50), (51, 100, 51, 100), (101, 168, 101, 200),
             (169, 208, 201, 300), (209, 748, 301, 400), (749, 1000, 401, 500)],
    "co":   [(0, 1.0, 0, 50), (1.1, 2.0, 51, 100), (2.1, 10, 101, 200),
             (10.1, 17, 201, 300), (17.1, 34, 301, 400), (34.1, 50, 401, 500)],
}

POLLUTANT_UNITS_US = {"pm25": "µg/m³", "pm10": "µg/m³", "o3": "ppb",
                      "no2": "ppb", "so2": "ppb", "co": "ppm"}
POLLUTANT_UNITS_CPCB = {"pm25": "µg/m³", "pm10": "µg/m³", "o3": "µg/m³",
                        "no2": "µg/m³", "so2": "µg/m³", "co": "mg/m³"}

POLLUTANT_LABELS = {
    "pm25": "PM2.5", "pm10": "PM10", "o3": "O₃", "no2": "NO₂",
    "so2": "SO₂", "co": "CO",
}


@dataclass(frozen=True)
class AqiCategory:
    key: str
    label: str
    lower: int
    upper: int
    color: str
    short_advice: str


US_CATEGORIES: list[AqiCategory] = [
    AqiCategory("good", "Good", 0, 50, "#00A86B",
                "Air quality is satisfactory; outdoor activity is fine."),
    AqiCategory("moderate", "Moderate", 51, 100, "#F4C542",
                "Acceptable, but unusually sensitive people should watch symptoms."),
    AqiCategory("usg", "Unhealthy for Sensitive Groups", 101, 150, "#F08A24",
                "Children, older adults and people with heart or lung disease should limit exertion outdoors."),
    AqiCategory("unhealthy", "Unhealthy", 151, 200, "#E14B4B",
                "Everyone may feel effects; limit prolonged outdoor exertion."),
    AqiCategory("very_unhealthy", "Very Unhealthy", 201, 300, "#8B5CF6",
                "Health alert — avoid outdoor exertion."),
    AqiCategory("hazardous", "Hazardous", 301, 500, "#7E1F2B",
                "Emergency conditions — stay indoors with filtered air."),
]

CPCB_CATEGORIES: list[AqiCategory] = [
    AqiCategory("good", "Good", 0, 50, "#00A86B", "Minimal impact."),
    AqiCategory("satisfactory", "Satisfactory", 51, 100, "#9ACD32",
                "Minor breathing discomfort to sensitive people."),
    AqiCategory("moderate", "Moderate", 101, 200, "#F4C542",
                "Breathing discomfort to people with lung or heart disease."),
    AqiCategory("poor", "Poor", 201, 300, "#F08A24",
                "Breathing discomfort to most people on prolonged exposure."),
    AqiCategory("very_poor", "Very Poor", 301, 400, "#E14B4B",
                "Respiratory illness on prolonged exposure."),
    AqiCategory("severe", "Severe", 401, 500, "#7E1F2B",
                "Affects healthy people; serious impact on those with existing disease."),
]


def _table(scale: Scale) -> dict[str, list[tuple[float, float, float, float]]]:
    return US_EPA_BREAKPOINTS if scale == "us_epa" else CPCB_BREAKPOINTS


def concentration_to_index(pollutant: str, concentration: float,
                           scale: Scale = "us_epa") -> float | None:
    """Piecewise-linear concentration -> AQI sub-index."""
    if concentration is None or concentration < 0:
        return None
    bands = _table(scale).get(pollutant)
    if not bands:
        return None
    # NOTE: published breakpoint tables are not contiguous (PM2.5 jumps from
    # 9.0 to 9.1), so we match on the upper edge only. Matching `c_lo <= x <=
    # c_hi` would drop values that land in those gaps.
    for c_lo, c_hi, i_lo, i_hi in bands:
        if concentration <= c_hi:
            lo = max(c_lo, 0.0)
            if c_hi == lo:
                return round(float(i_hi), 1)
            frac = (concentration - lo) / (c_hi - lo)
            frac = min(max(frac, 0.0), 1.0)
            return round((i_hi - i_lo) * frac + i_lo, 1)
    # Above the top band: clamp at the scale maximum rather than extrapolating.
    return float(bands[-1][3])


def index_to_concentration(pollutant: str, index: float,
                           scale: Scale = "us_epa") -> float | None:
    """Inverse of :func:`concentration_to_index`.

    Required because the WAQI feed publishes sub-indices, not concentrations.
    """
    if index is None or index < 0:
        return None
    bands = _table(scale).get(pollutant)
    if not bands:
        return None
    for c_lo, c_hi, i_lo, i_hi in bands:
        if index <= i_hi:
            value = (c_hi - c_lo) / (i_hi - i_lo) * (index - i_lo) + c_lo
            return round(max(value, 0.0), 1)
    return round(float(bands[-1][1]), 1)


def overall_aqi(sub_indices: dict[str, float | None]) -> tuple[float | None, str | None]:
    """Overall AQI is the maximum sub-index; the argmax is the dominant pollutant."""
    valid = {k: v for k, v in sub_indices.items() if v is not None}
    if not valid:
        return None, None
    dominant = max(valid, key=lambda k: valid[k])
    return round(valid[dominant], 1), dominant


def categorize(aqi: float | None, scale: Scale = "us_epa") -> AqiCategory | None:
    if aqi is None:
        return None
    table = US_CATEGORIES if scale == "us_epa" else CPCB_CATEGORIES
    # The published bands are integer ranges, so a value of 150.4 falls in the
    # gap between "USG" (…150) and "Unhealthy" (151…). AQI is reported as a
    # whole number, so we assign by the rounded value: 150.4 is USG, 150.6 is
    # Unhealthy. Matching `lower <= aqi <= upper` instead would drop every
    # in-gap value through to the Hazardous band.
    for cat in table:
        if aqi <= cat.upper + 0.5:
            return cat
    return table[-1]


def categories_payload(scale: Scale = "us_epa") -> list[dict]:
    table = US_CATEGORIES if scale == "us_epa" else CPCB_CATEGORIES
    return [
        {"key": c.key, "label": c.label, "lower": c.lower, "upper": c.upper,
         "color": c.color, "advice": c.short_advice}
        for c in table
    ]


def trend_of(current: float | None, previous: float | None) -> dict:
    """Direction + percentage change, with 'stable' for movement under 2%."""
    if current is None or previous in (None, 0):
        return {"direction": "unknown", "change": None, "change_pct": None}
    change = current - previous
    pct = (change / previous) * 100
    if abs(pct) < 2:
        direction = "stable"
    elif change > 0:
        direction = "worsening"
    else:
        direction = "improving"
    return {"direction": direction, "change": round(change, 1),
            "change_pct": round(pct, 1)}


def mean(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None
