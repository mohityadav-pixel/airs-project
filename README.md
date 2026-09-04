# AIRS — AI Response & Intervention System

**From predicting pollution to preventing it.**

AIRS is an urban air-quality intelligence platform. Most air-quality tools stop
at the number on the dial. AIRS answers the four questions that follow it:

> Why is pollution happening? · What happens next? · What can we do about it? ·
> What would that actually achieve?

It does that as one connected pipeline, not as a set of separate widgets:

```
live data → analysis → prediction → source attribution → AI explanation
          → intervention → simulation → prioritised decision
```

---

## The one thing to understand about AIRS

**Every number tells you what kind of number it is.**

A measurement, a forecast, a modelled scenario and a sentence written by a
language model are four different things. Conflating them is how air-quality
dashboards lose the trust of the people who have to act on them. So every
data-bearing API response carries a `provenance` block:

| kind | meaning |
|---|---|
| `observed` | measured by a monitoring station |
| `predicted` | ML forecast, with an 80% interval |
| `simulated` | what-if scenario output |
| `estimated` | model-based attribution (e.g. the source split) |
| `ai_generated` | LLM prose grounded on the above |

…plus a `mode` of `live`, `cached` or `demo`. The UI renders that as a badge on
every panel, and a test (`test_every_data_response_declares_its_provenance`)
enforces it. **Synthetic data is never labelled live**, on any code path.

The Copilot is given a fixed block of AIRS facts and is not permitted to state a
figure that is not in it. The grounding panel next to the chat shows the user
exactly what the model was allowed to see.

---

## Quick start

```bash
git clone <your-repo> airs-project && cd airs-project
cp .env.example .env          # then fill in your keys — see below
./scripts/dev.sh              # backend :8000, frontend :5173
```

Open **http://localhost:5173**. API docs are at **http://localhost:8000/docs**.

`dev.sh` creates the virtualenv, installs both dependency trees, initialises the
database and starts both servers. To do it by hand:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/python -m app.db.init_db
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# in a second terminal
cd frontend && npm install && npm run dev
```

### Getting data on screen

A brand-new install has reference data (cities, stations, intervention
catalogue) but no measurements. Two ways to fill it:

```bash
# A. Start collecting real readings — one snapshot per station per run.
.venv/bin/python -m scripts.ingest --loop --every 3600

# B. Generate a labelled synthetic history so the charts and the model have
#    something to work with today. Every row is stamped provenance='demo'.
.venv/bin/python -m scripts.backfill_history --days 120
```

Free air-quality APIs only expose the *current* hour, so (A) is how AIRS builds
genuine history — run it hourly from cron. (B) exists so the platform is
demonstrable on day one, and is honest about what it is.

### Training the forecaster

```bash
cd backend && ../.venv/bin/python -m ml.train --days 180
```

Writes model artifacts to `backend/ml/artifacts/` plus a `manifest.json` with
held-out metrics, which the UI renders as a model card. Without artifacts the
API still forecasts, using a transparent persistence-plus-climatology baseline —
and says so, in the `tier` field.

---

## Environment variables

All secrets live in `.env` at the repo root, shared by the backend and Vite.
`.env` is git-ignored; `.env.example` is the template.

| Variable | Required | What it does |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://…` in production; a SQLite path works for local dev |
| `AIRS_SECRET_KEY` | yes | JWT signing key — generate with `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `AIRS_DATA_MODE` | yes | `live`, `demo` or `auto` (see below) |
| `AIRS_CORS_ORIGINS` | yes | comma-separated allowed origins |
| `WAQI_TOKEN` | for live AQI | free token from aqicn.org/data-platform/token |
| `OPENWEATHER_API_KEY` | for live weather | free tier is sufficient |
| `GEMINI_API_KEY` | for the Copilot | aistudio.google.com/apikey |
| `GEMINI_MODEL` | no | defaults to `gemini-2.0-flash` |
| `TOMTOM_API_KEY` | no | not yet wired; traffic is modelled until it is |
| `VITE_API_BASE_URL` | dev only | where the Vite dev proxy sends `/api` |

Anything you leave blank simply disables that one feature — the platform reports
what is actually available at `/api/v1/system/status`, and the UI hides or
explains the rest. **Only `VITE_*` variables reach the browser. No API key is
ever sent to the client; the browser talks to AIRS, AIRS talks to the providers.**

### Data modes

| mode | behaviour |
|---|---|
| `live` | fetch upstream; on failure serve the last-known-good value marked `cached`; **never** substitute synthetic data |
| `demo` | never call upstream; every row is synthetic and stamped `demo`; a standing banner says so |
| `auto` | live → cached → demo, and the response always states which of the three it used |

---

## Architecture

```
airs-project/
├── backend/
│   ├── app/
│   │   ├── core/          config, logging, errors, cache, security
│   │   ├── domain/        AQI mathematics (EPA + CPCB scales)
│   │   ├── db/            SQLAlchemy models, session, seed data
│   │   ├── services/      providers, validation, ingestion, attribution,
│   │   │                  simulation, priority, recommendations, alerts, health
│   │   ├── ai/            Gemini client, grounding, Copilot, explanation engine
│   │   ├── api/v1/        routers
│   │   └── schemas/       typed request/response models
│   ├── ml/                features, dataset, model, train, predict
│   └── tests/             81 tests
├── frontend/src/
│   ├── lib/               API client, types, theme, selection, auth, viz tokens
│   ├── components/        design-system pieces
│   ├── charts/            Recharts wrappers on a validated palette
│   ├── maps/              Leaflet station map
│   └── pages/             landing, dashboard, map, predictions, analytics,
│                          simulator, copilot, command center, auth
├── scripts/               ingest.py, backfill_history.py, dev.sh
└── docs/                  ARCHITECTURE.md, DECISIONS.md, API.md
```

The layering rule is strict: **data → ML → business logic → AI → API → UI.**
No ML in a React component, no SQL in a router, no API key in the browser.

---

## API

Full interactive docs at `/docs`. The main surface:

```
GET  /api/v1/system/status              capabilities, data mode, model card
GET  /api/v1/air-quality/cities|stations
GET  /api/v1/air-quality/current        one station, full detail
GET  /api/v1/air-quality/summary        city roll-up + hotspots
GET  /api/v1/air-quality/map            every station, for the map
GET  /api/v1/air-quality/history        time series (hours= or start=/end=)
GET  /api/v1/predictions                6/24/72 h + hourly curve + explanation
GET  /api/v1/pollution-sources          estimated source split + evidence
GET  /api/v1/analytics/…                pollutants, correlations, compare,
                                        hourly-profile, station-ranking
GET  /api/v1/simulation/interventions   the lever catalogue
POST /api/v1/simulation                 run a what-if scenario
GET  /api/v1/recommendations            ranked city actions
GET  /api/v1/alerts                     what happened, why, what to do
GET  /api/v1/health-advisory            personalised, non-medical guidance
POST /api/v1/copilot                    grounded conversational answers
GET  /api/v1/command-center             official view (role-gated)
POST /api/v1/auth/register|login        JWT auth
```

See `docs/API.md` for request and response detail.

---

## How the interesting parts work

**Source attribution** (`services/source_attribution.py`) is receptor-style
reasoning, not a dispersion model — real apportionment needs chemical speciation
no free feed provides. It reads the pollutant ratios (a wide PM10/PM2.5 gap means
mechanical dust, not combustion), the tracers (SO₂ is industrial, NO₂ with
congestion is fresh traffic), the meteorology (calm air means accumulation, not
new emission) and the site context. Every estimate ships with the evidence that
produced it.

**The simulator** (`services/simulation.py`) applies each lever *only to the
share of each pollutant its own source contributes*, then discounts the result by
how well the atmosphere is currently dispersing, then recomputes AQI from the
resulting concentrations with the same EPA function used for measurements. This
is why a 30% traffic cut yields single-digit AQI improvement rather than 30% —
and the test suite asserts it, because the naive version is the classic error.

**The forecaster** (`ml/`) is a pooled histogram gradient-boosting model per
(target, horizon), with two extra quantile models for the 80% interval. Gradient
boosting rather than an LSTM because the data volume is small, station feeds drop
out constantly (trees handle NaN natively), and officials need an auditable
model. Every run is scored against a persistence baseline and the skill number is
shown in the UI.

**The priority score** (`services/priority.py`) is a weighted geometric mean of
severity, exposure, predicted risk, modelled impact and urgency. Geometric, so a
zone with nobody in it cannot rank top on severity alone. Every factor is
returned with its raw value and its reasoning so a city can argue with the
ranking.

---

## Testing

```bash
cd backend && ../.venv/bin/python -m pytest -q     # 81 tests
cd frontend && npm run lint && npm run build       # typecheck + production build
```

Tests run against a throwaway SQLite database in `demo` mode, so they never call
a real provider or spend API quota. `tests/test_demo_scenario.py` walks the whole
observe → attribute → predict → explain → alert → recommend → simulate →
prioritise flow as a single test.

---

## Deployment

```bash
cp .env.example .env    # fill in keys and a real AIRS_SECRET_KEY
docker compose up --build
```

Brings up PostgreSQL, the API on `:8000` and the built frontend behind nginx on
`:8080`, with `/api` proxied so the browser sees one origin. For production also:

- set `AIRS_ENV=production` and a strong `AIRS_SECRET_KEY`
- restrict `AIRS_CORS_ORIGINS` to your real domain
- terminate TLS in front of nginx
- run `scripts/ingest.py --loop` as a separate always-on process or a cron job
- retrain periodically (`ml.train`) as live history accumulates

---

## Honest limitations

- **Source shares are estimates**, from ratios and context — not measured
  apportionment. Confidence is capped at 0.82 and surfaced everywhere.
- **Simulation output is a modelled estimate**, not a guaranteed outcome. The
  effectiveness figures are planning values, stored per-intervention in the
  database so a city can recalibrate them without a code change.
- **Model metrics trained on backfilled history are optimistic.** A model scored
  against its own generator looks better than it will on live data. The model
  card says this on screen, and the numbers will fall — correctly — as real
  history replaces synthetic.
- **Traffic is modelled, not measured**, until a TomTom key is wired in. It is
  labelled `demo` provenance in the meantime.
- **Health guidance is general public-health information**, not medical advice.
