"""Alert engine.

Alerts answer four questions in order — what happened, where, why it matters,
what to do — because an alert that only reports a number is noise. Each rule is
idempotent within its dedup window so a persistent episode raises one alert, not
one per polling cycle.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, AlertSeverity, City, Station
from app.domain.aqi import POLLUTANT_LABELS, categorize

DEDUP_WINDOW = timedelta(hours=6)

# Concentration thresholds that matter clinically, not just categorically.
POLLUTANT_THRESHOLDS = {
    "pm25": (120.0, "24-hour exposure at this level is associated with measurable "
                    "respiratory and cardiovascular effects."),
    "pm10": (250.0, "Coarse particulate at this level irritates airways and reduces "
                    "visibility."),
    "no2": (200.0, "Short-term NO₂ at this level aggravates asthma."),
    "so2": (180.0, "SO₂ at this level triggers bronchoconstriction in asthmatics."),
    "o3": (110.0, "Ozone at this level reduces lung function during exertion."),
}


def _recent_alert(db: Session, city_id: int, station_id: int | None,
                  kind: str, now: datetime) -> Alert | None:
    return db.scalar(select(Alert).where(
        Alert.city_id == city_id, Alert.station_id == station_id,
        Alert.kind == kind, Alert.is_active.is_(True),
        Alert.raised_at >= now - DEDUP_WINDOW))


def _raise(db: Session, *, city: City, station: Station | None, kind: str,
           severity: AlertSeverity, title: str, what: str, why: str,
           action: str, duration: int | None, now: datetime,
           context: dict | None = None) -> Alert | None:
    if _recent_alert(db, city.id, station.id if station else None, kind, now):
        return None
    alert = Alert(city_id=city.id, station_id=station.id if station else None,
                  kind=kind, severity=severity, title=title, what_happened=what,
                  why_it_matters=why, recommended_action=action,
                  expected_duration_hours=duration, raised_at=now,
                  expires_at=now + timedelta(hours=duration or 6),
                  is_active=True, context=context or {})
    db.add(alert)
    return alert


def evaluate_station(db: Session, city: City, station: Station, *,
                     reading, forecast_peak: float | None,
                     hours_to_peak: float | None,
                     source_shares: dict[str, float] | None = None,
                     now: datetime | None = None) -> list[Alert]:
    now = now or datetime.now(timezone.utc)
    raised: list[Alert] = []
    if reading is None:
        return raised

    aqi = reading.aqi
    category = categorize(aqi) if aqi is not None else None
    top_source = (max(source_shares, key=source_shares.get)
                  if source_shares else None)

    # 1. Extreme current AQI.
    if aqi is not None and aqi >= 300:
        a = _raise(db, city=city, station=station, kind="extreme_aqi",
                   severity=AlertSeverity.emergency,
                   title=f"Hazardous air at {station.name}",
                   what=f"AQI has reached {aqi:.0f} ({category.label}).",
                   why="At this level everyone is affected, not only sensitive "
                       "groups, and outdoor exertion carries real risk.",
                   action="Advise the public to stay indoors, suspend outdoor work "
                          "and school activity, and activate emergency response "
                          "measures in the catchment.",
                   duration=6, now=now,
                   context={"aqi": aqi, "station": station.code})
        if a: raised.append(a)
    elif aqi is not None and aqi >= 200:
        a = _raise(db, city=city, station=station, kind="high_aqi",
                   severity=AlertSeverity.warning,
                   title=f"Very unhealthy air at {station.name}",
                   what=f"AQI is {aqi:.0f} ({category.label}).",
                   why="Sustained exposure at this level affects the whole "
                       "population and sharply raises risk for people with heart "
                       "or lung disease.",
                   action="Issue a public advisory to limit outdoor exertion and "
                          "prioritise this zone for immediate intervention.",
                   duration=6, now=now, context={"aqi": aqi})
        if a: raised.append(a)

    # 2. Predicted deterioration.
    if aqi is not None and forecast_peak is not None and forecast_peak - aqi >= 25:
        window = (f"in about {hours_to_peak:.0f} hours"
                  if hours_to_peak else "over the coming hours")
        a = _raise(db, city=city, station=station, kind="predicted_spike",
                   severity=AlertSeverity.watch,
                   title=f"AQI forecast to worsen at {station.name}",
                   what=f"AQI is {aqi:.0f} now and is forecast to reach "
                        f"{forecast_peak:.0f} {window}.",
                   why="Acting before the peak is far cheaper than responding "
                       "after it; the same intervention applied now avoids "
                       "several hours of elevated exposure."
                       + (f" The dominant estimated driver here is "
                          f"{top_source.replace('_', ' ')}." if top_source else ""),
                   action="Pre-position the intervention that targets the dominant "
                          "source in this zone and notify sensitive groups now.",
                   duration=int(hours_to_peak or 6) + 3, now=now,
                   context={"current_aqi": aqi, "forecast_peak": forecast_peak,
                            "hours_to_peak": hours_to_peak})
        if a: raised.append(a)

    # 3. Individual pollutant threshold crossings.
    for pollutant, (threshold, why) in POLLUTANT_THRESHOLDS.items():
        value = getattr(reading, pollutant, None)
        if value is None or value < threshold:
            continue
        a = _raise(db, city=city, station=station,
                   kind=f"threshold_{pollutant}", severity=AlertSeverity.warning,
                   title=f"{POLLUTANT_LABELS[pollutant]} above threshold at {station.name}",
                   what=f"{POLLUTANT_LABELS[pollutant]} measured at {value:.0f}, "
                        f"above the {threshold:.0f} advisory threshold.",
                   why=why,
                   action="Target the source category associated with this "
                          "pollutant and advise the catchment population.",
                   duration=6, now=now,
                   context={"pollutant": pollutant, "value": value})
        if a: raised.append(a)

    return raised


def deactivate_expired(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    stale = list(db.scalars(select(Alert).where(
        Alert.is_active.is_(True), Alert.expires_at.isnot(None),
        Alert.expires_at < now)))
    for alert in stale:
        alert.is_active = False
    return len(stale)


def detect_hotspots(readings: dict[int, object], stations: list[Station],
                    *, k: float = 1.25) -> list[int]:
    """A hotspot is a station materially worse than its own city's median — an
    absolute threshold would flag every station in Delhi and none in Bengaluru."""
    values = [(s.id, getattr(readings.get(s.id), "aqi", None)) for s in stations]
    values = [(sid, v) for sid, v in values if v is not None]
    if len(values) < 3:
        return []
    ordered = sorted(v for _, v in values)
    median = ordered[len(ordered) // 2]
    return [sid for sid, v in values if v >= median * k]
