# Architectural decisions

Short records of the choices that shaped AIRS, and what would make each one
wrong. Written so a reviewer can disagree with a decision on its merits rather
than reverse-engineering it from the code.

---

## ADR-001 — Provenance is a first-class field, not documentation

**Decision.** Every data-bearing API response carries a `provenance` object with
a `kind` (`observed` / `predicted` / `simulated` / `estimated` / `ai_generated`)
and a `mode` (`live` / `cached` / `demo`). The frontend renders a badge from it
on every panel.

**Why.** The failure mode that destroys trust in an air-quality dashboard is not
inaccuracy — it is a forecast presented as a measurement, or a demo dataset
presented as live. Encoding the distinction in a Pydantic model makes it
impossible to add a new endpoint that forgets it, and a test asserts it across
every data endpoint.

**Cost.** Slightly more verbose payloads and one more thing every new endpoint
has to fill in.

---

## ADR-002 — Reuse the existing collectors, but fix the sub-index bug

**Decision.** The WAQI and OpenWeather adapters descend from the original
`src/data_collection/` scripts in this repo rather than being rewritten. One
behaviour changed: WAQI's `iaqi` block publishes **AQI sub-indices**, not
concentrations. The original code stored them as if they were µg/m³.

**Why.** Storing a sub-index in a concentration column understates PM2.5 in the
healthy range and overstates it in the unhealthy range — quietly, with no error.
The EPA function is piecewise-linear and invertible, so `index_to_concentration`
recovers the true value exactly.

**What would make this wrong.** Switching to a provider that publishes real
concentrations (OpenAQ, a CPCB feed) — then the inversion must be removed, not
merely bypassed.

---

## ADR-003 — Gradient boosting, not an LSTM

**Decision.** `HistGradientBoostingRegressor` per (target, horizon), pooled
across stations, with two quantile models for the 80% interval.

**Why.** Three reasons, in order of weight:

1. *Data volume.* A recurrent network needs far more history per station than a
   city network accumulates in its first months. On a few thousand hourly rows an
   LSTM overfits and loses to a boosted tree with lag features.
2. *Missingness.* Station feeds drop out constantly. Histogram boosting handles
   NaN natively — no imputation step to bias the result.
3. *Auditability.* Officials act on these numbers. A tree ensemble supports a
   defensible driver attribution; an LSTM does not.

Pooling across stations (with zone and proximity as features) lets a station with
two weeks of data borrow strength from one with six months.

**What would make this wrong.** Several years of dense multi-station history, or
a requirement to model long-range spatial transport — at which point a sequence
or graph model earns its complexity.

---

## ADR-004 — Effectiveness and source share are separate numbers

**Decision.** Each intervention stores, per pollutant, the fraction of **its own
source's contribution** it removes at full magnitude. The simulator multiplies
that by the source's live share at the station, by the lever magnitude, and by a
meteorological discount.

**Why.** The seductive shortcut is a single "elasticity" that means "fraction of
ambient PM2.5 removed if you eliminate traffic". That number already contains the
source share, so multiplying it by the share again double-discounts — and using
it without the share produces the classic nonsense where a 30% traffic cut
delivers a 30% AQI drop at a site where traffic contributes 12% of the load.
Keeping the two apart is what makes the simulator defensible.

**Cost.** Two numbers to calibrate instead of one. Both live in the database
rather than in code, so a city can recalibrate without a redeploy.

---

## ADR-005 — Rules decide, the LLM writes

**Decision.** Which intervention to recommend, how it is scored and what the
forecast is are all computed deterministically. The language model only turns
that reasoning into readable prose, and is forbidden from producing a figure not
present in the grounded-facts block it is given.

**Why.** An official needs the same inputs to produce the same recommendation,
every time, and needs to be able to audit why. Language models are excellent at
explanation and unreliable at arithmetic forecasting. Letting the LLM choose the
action would also make the system's behaviour depend on a vendor's model
version.

**Consequence.** Every AI-touched surface degrades to a deterministic template
when no key is configured or the call fails. The explanation engine reports which
tier produced the text.

---

## ADR-006 — Synthetic history is generated, labelled, and never disguised

**Decision.** `scripts/backfill_history.py` generates a physically-motivated
synthetic history (diurnal traffic peaks, nocturnal inversion, monsoon washout,
zone offsets, wind-driven dispersion, AQI computed from the concentrations
rather than drawn independently). Every row is stored with
`provenance='demo'`, `/api/v1/system/status` reports the live/demo split, and
the UI shows a standing banner.

**Why.** Free APIs expose only the current hour, so a new install has nothing to
plot and nothing to train on. The alternative — shipping a dead product until
months of history accumulate — is worse. The alternative failure — passing
synthetic data off as measurement — is much worse, so it is structurally
prevented rather than merely avoided.

**Known consequence.** Model metrics trained on backfilled history are
optimistic, because the model is scored against its own generator. The model
card says so on screen.

---

## ADR-007 — SQLAlchemy with a UTC-normalising column type

**Decision.** A `UtcDateTime` `TypeDecorator` on every timestamp column.

**Why.** SQLite has no native timezone support: values written as aware come back
naive, and every comparison against `datetime.now(timezone.utc)` raises. Fixing
that at each call site is a permanent source of bugs; fixing it in the column
type makes SQLite and PostgreSQL behave identically.

---

## ADR-008 — Relative hotspots, not an absolute threshold

**Decision.** A hotspot is a station at or above 1.25× its own city's median AQI.

**Why.** Any absolute threshold flags every station in Delhi and none in
Bengaluru, which is useless for both. The operational question — "where in *this*
city should we act first?" — is inherently relative.

---

## ADR-009 — The chart palette is validated, not chosen

**Decision.** The categorical palette is a fixed slot order bound to source
identity, validated in both themes against the AIRS surfaces (lightness band,
chroma floor, colour-vision-deficiency separation, normal-vision floor,
contrast). Three light-mode slots fall below 3:1 contrast on white, so every
categorical chart ships direct value labels as the relief.

**Why.** "Pick some nice colours" produces palettes that are unreadable for ~8%
of men and illegible when a filter changes the series count. Binding colour to
the entity rather than to its rank means re-sorting a list never repaints a
category.

AQI band colours are a separate, fixed scale: they are defined by the EPA and are
data, not decoration, so they are identical in both themes.
