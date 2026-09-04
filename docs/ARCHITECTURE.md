# AIRS architecture

## Layering

```
 EXTERNAL          WAQI / AQICN        OpenWeatherMap       (TomTom, future)
                        │                     │                    │
 PROVIDERS      services/providers/*  — one adapter per vendor, normalised
                        └───────────┬─────────┘
 VALIDATION         services/validation.py — range, cross-field, staleness
                                    │
 INGESTION          services/ingestion.py — mode resolution, TTL cache,
                                    │        last-known-good, persistence
 STORAGE            db/models.py — PostgreSQL (SQLite for dev)
                                    │
 FEATURES           ml/features.py — lags, rolling, cyclical time, context
                                    │
 MODELS             ml/model.py, ml/train.py — pooled HGB + quantile pair
                                    │
 INFERENCE          ml/predict.py — model tier, or a labelled baseline
                                    │
 INTELLIGENCE       source_attribution · simulation · priority ·
                    recommendations · alerts · health
                                    │
 AI                 ai/context.py → ai/prompts.py → ai/gemini.py
                    (grounded facts in, prose out, no new numbers)
                                    │
 API                api/v1/* — FastAPI, typed schemas, provenance on every
                                    │  payload, RBAC, rate limiting
 UI                 React + TypeScript — typed client, no business logic
```

Each arrow is one direction. The UI never reaches past the API; the API never
reaches past the services; ML never imports a router.

## Request lifecycle

A typical dashboard load:

1. `GET /api/v1/air-quality/current?city=delhi`
2. The router resolves the city and station, then calls `ensure_fresh`.
3. `ensure_fresh` checks how old the newest stored reading is. Under 20 minutes:
   nothing happens. Older: one upstream fetch, validated and persisted.
4. If the provider fails, the request continues on stored data and the payload is
   marked stale — a dead upstream never produces an empty screen or a 500.
5. `assembly.current_air_quality` maps rows to the response schema and stamps the
   provenance.

Upstream calls are additionally TTL-cached in-process for 10 minutes, so a
hundred page loads produce one API call.

## Data model

Measurement tables (`air_quality_readings`, `weather_readings`,
`traffic_readings`) share a shape: `station_id`, `observed_at`, `ingested_at`,
`provenance`, a unique key on `(station_id, observed_at)` and a composite index
on the same pair. Storing observation and ingestion time separately makes
staleness queryable rather than inferred.

Intelligence tables (`predictions`, `pollution_sources`, `alerts`,
`simulations`, `recommendations`) all record the method or model version that
produced them, so a stored result can be traced to the code that made it.

`interventions` holds the lever catalogue *including its coefficients*, so
recalibrating the simulator for a city is a data change, not a deploy.

## Failure behaviour

| Failure | Result |
|---|---|
| Air-quality provider down | serve last-known-good, marked `cached`; in `auto` mode fall through to labelled demo |
| Weather provider down | same; ventilation index becomes null and the attribution degrades gracefully |
| Gemini missing or failing | deterministic explanation engine takes over and says so; Copilot returns a clean 503 |
| No trained model | baseline forecaster, `tier: "baseline"` in the response |
| One station errors during a city ingest | that station is skipped and logged; the rest proceed |
| Any unhandled exception | 500 with a generic message; the detail goes to the structured log only |

## Security

- Passwords hashed with bcrypt; JWTs signed with `AIRS_SECRET_KEY`, 2-hour TTL.
- Hierarchical RBAC (`citizen < analyst < official < admin`); role is never
  accepted from the client at registration.
- Login returns an identical message for an unknown user and a wrong password.
- All input validated by Pydantic; SQL only through the ORM.
- Rate limiting via slowapi (240 req/min per IP by default).
- Structured JSON logging with credential redaction.
- Provider and AI keys stay server-side; only `VITE_*` variables reach the
  browser.
- User text is sanitised before reaching the model, and the system prompt treats
  it as data rather than instructions.

## Extension points

| To add | Change |
|---|---|
| Another city | one entry in `db/seed_data.py` |
| Another AQI provider | one class implementing `AirQualityProvider`, registered in `ingestion.py` |
| Real traffic | implement a `TrafficProvider`, replace `fetch_traffic` |
| A better forecaster | swap `_new_regressor` in `ml/model.py`; the interface is fixed |
| A causal simulator | replace `services/simulation.simulate`; the API contract is unchanged |
| IoT sensors | they are just another provider writing into the same normalised tables |
