# AIRS API reference

Base path `/api/v1`. Interactive docs (OpenAPI) at `/docs`.

Every data-bearing response includes a `provenance` object:

```json
{
  "kind": "observed",
  "mode": "live",
  "source": "WAQI / AQICN + OpenWeatherMap",
  "observed_at": "2026-09-04T17:00:00Z",
  "generated_at": "2026-09-04T17:12:03Z",
  "note": null,
  "is_stale": false
}
```

`kind` ∈ `observed` · `predicted` · `simulated` · `estimated` · `ai_generated`
`mode` ∈ `live` · `cached` · `demo`

Errors are always shaped:

```json
{ "error": { "code": "provider_unavailable", "message": "…" } }
```

| code | status | meaning |
|---|---|---|
| `invalid_request` | 400 | bad parameter, unknown city or lever |
| `not_authorized` | 403 | missing, invalid or insufficient credentials |
| `data_unavailable` | 404 | nothing stored for this request |
| `provider_unavailable` / `provider_not_configured` | 503 | upstream down or no key |
| `ai_unavailable` | 503 | Gemini not configured or unreachable |
| `internal_error` | 500 | unexpected; details go to the log, never to the client |

---

## System

**`GET /system/status`** — what is actually working. Drives the UI's data-mode
banner and hides unconfigured features.

```json
{
  "data_mode": "live",
  "capabilities": { "air_quality_provider": true, "weather_provider": true,
                    "traffic_provider": false, "ai_copilot": true,
                    "ml_models_trained": true },
  "data": { "live_readings": 812, "demo_readings": 108030, "total_readings": 108842 },
  "model": { "model_name": "airs-hgb", "model_version": "1.0.0",
             "trained_at": "…", "reports": [ … ] }
}
```

**`GET /system/aqi-scale?scale=us_epa|cpcb`** — category bands, colours, advice.
**`GET /system/health`** — liveness probe.

---

## Air quality

| Endpoint | Purpose |
|---|---|
| `GET /air-quality/cities` | configured cities with station counts |
| `GET /air-quality/stations?city=` | stations with zone and context flags |
| `GET /air-quality/current?city=&station_id=` | full current reading |
| `GET /air-quality/summary?city=` | city roll-up, best/worst, hotspot ids |
| `GET /air-quality/map?city=` | every station plus the legend |
| `GET /air-quality/history?city=&station_id=&hours=` | time series + stats |

`station_id` is optional everywhere; omitted, AIRS picks the station with the
freshest reading. `history` also accepts `start=` and `end=` ISO timestamps
instead of `hours=`.

`current` returns concentrations *and* AQI sub-indices per pollutant, plus
`share_of_aqi` (100% marks the driver), 1-hour and 24-hour trends, the joined
weather and traffic state, and any `quality_flags` raised by validation.

---

## Predictions

**`GET /predictions?city=&station_id=&curve_hours=24&explain=true&persist=false`**

```json
{
  "current_aqi": 134.0,
  "horizons": [ { "horizon_hours": 6, "aqi": 151.0, "aqi_lower": 143.2,
                  "aqi_upper": 162.1, "pm25": 59.6, "confidence": 0.78,
                  "risk_category": "Unhealthy", "tier": "model" } ],
  "curve": [ … hourly points for charting … ],
  "peak": { … }, "trough": { … },
  "model": { "model_name": "airs-hgb", "model_version": "1.0.0", "tier": "model" },
  "explanation": { "headline": "…", "simple": "…", "technical": "…",
                   "factors": ["…"], "tier": "llm" }
}
```

`tier` is `model` (trained artifacts) or `baseline` (persistence + diurnal
climatology, used when no artifact exists or the station is too new). AIRS never
silently downgrades a forecast. `explanation.tier` is `llm` or `deterministic`.
`persist=true` writes the horizons to the `predictions` table.

---

## Pollution sources

**`GET /pollution-sources?city=&station_id=&persist=false`**

Shares always total exactly 100. `evidence` explains each signal that moved the
estimate; `confidence` is capped at 0.82 by construction.

```json
{
  "contributions": [ { "key": "traffic", "label": "Traffic", "share_pct": 42.1 } ],
  "evidence": [ { "signal": "PM10/PM2.5 ratio", "value": 2.44,
                  "reading": "Wide coarse fraction — mechanical dust …" } ],
  "confidence": 0.74,
  "method": "ratio-and-context heuristic v1"
}
```

---

## Analytics

| Endpoint | Returns |
|---|---|
| `GET /analytics/pollutants?hours=168` | per-pollutant current/24 h/7 d, min/max, correlation with AQI, % of time dominant |
| `GET /analytics/correlations?hours=336` | Pearson r of each driver vs AQI and PM2.5, with an interpretation string |
| `GET /analytics/compare?mode=day\|week\|month` | this period vs the previous one |
| `GET /analytics/hourly-profile?days=30` | average AQI by local hour and weekday |
| `GET /analytics/station-ranking?hours=24` | stations ordered worst-first |

---

## Simulation

**`GET /simulation/interventions`** — the lever catalogue, in the order a city
would reach for them. Each entry carries `max_magnitude`, `lag_hours`,
`cost_band`, an `evidence_note` and the per-pollutant `effectiveness` map.

**`POST /simulation`**

```json
{ "city_slug": "delhi", "station_id": 1,
  "levers": [ { "key": "traffic_reduction", "magnitude": 30 } ],
  "save": false }
```

Response contains `baseline`, `simulated`, `deltas` (including
`improvement_pct`, `category_changed` and exposed population), `per_lever` (with
`attributable_source_share_pct` — the share the lever could actually act on),
`assumptions`, `warnings`, `confidence`, `engine_version` and `caveat`.

`magnitude` is 0–100 and additionally clamped to the lever's own
`max_magnitude`. Unknown lever keys are a 400.

---

## Actions

**`GET /recommendations?city=`** — actions bucketed into `immediate`,
`short_term` and `long_term`, each with `reason`, `expected_impact`,
`priority_score`, the full `priority_factors` breakdown and `confidence`. The
same lever is never repeated once per station; it appears once, naming the other
affected zones. `methodology` explains how selection, impact and priority were
computed.

**`GET /alerts?city=&evaluate=true`** — active alerts. Each answers what
happened, why it matters and what to do, with a severity of `info`, `watch`,
`warning` or `emergency`. Re-evaluated on request and deduplicated within a
6-hour window so a persistent episode raises one alert, not one per poll.

**`GET /health-advisory?city=&station_id=&group=`** — guidance for `general`,
`outdoor_worker`, `athlete`, `child`, `elderly` or `sensitive`. Signed-in users
get their saved profile by default. Always carries a disclaimer.
`GET /health-advisory/groups` lists the options.

---

## Copilot

**`POST /copilot`**

```json
{ "question": "Why is the AQI high right now?", "city_slug": "delhi",
  "station_id": 1, "conversation_id": null }
```

Returns the answer plus `grounding.facts` — the exact tagged fact block the model
was given. The UI displays it, so a user can check any claim. Returns 503
`ai_unavailable` when no key is configured; nothing else in AIRS is affected.

`GET /copilot/suggestions`, `GET /copilot/conversations`,
`GET /copilot/conversations/{id}` support the chat UI.

---

## Command Center

**`GET /command-center?city=`** — requires the `official` role or higher.

One request returns the whole operations view: `headline` counters, `zones`
ranked by priority (each with predicted peak, hours to peak, dominant source,
best available lever and its modelled benefit, and the full priority factor
breakdown), `deteriorating`, `alerts` and `methodology`.

---

## Auth

| Endpoint | Notes |
|---|---|
| `POST /auth/register` | always creates a **citizen**; a client-supplied role is ignored |
| `POST /auth/login` | identical error for unknown user and wrong password |
| `POST /auth/logout` | audit record; tokens are stateless, the client discards it |
| `GET`/`PATCH /auth/me` | profile, including health sensitivity group |
| `GET /auth/users` | admin only |
| `PATCH /auth/users/{id}/role` | admin only; cannot remove your own admin role |

Send the token as `Authorization: Bearer <token>`.
