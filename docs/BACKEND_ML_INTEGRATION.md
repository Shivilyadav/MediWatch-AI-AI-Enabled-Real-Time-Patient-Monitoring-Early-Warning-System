# Backend ↔ ML Integration (Implemented)

Implementation record for the backend integration of the FINAL sepsis-risk model.
Executed against [BACKEND_ML_INTEGRATION_PLAN.md](BACKEND_ML_INTEGRATION_PLAN.md).

**Model:** `final-logreg-v1` · **Features:** `stage4-v2` (52) · **Threshold:** `0.36061602358147954`

> **Not a clinical tool.** The risk score is an uncalibrated ordinal research/hackathon
> benchmark. The artifact's own test metrics are AUROC ≈ 0.648, FPR ≈ 0.59,
> precision ≈ 1.5% — it is explicitly not deployment-ready and must not inform patient care.

---

## 1. Files changed

| File | Change |
|---|---|
| [backend/ml_inference.py](../backend/ml_inference.py) | **NEW** — the only bridge between the backend and the ML pipeline |
| [backend/main.py](../backend/main.py) | **MODIFIED** — old detector replaced at all 4 call sites; virtual-hour cadence; warm-up seeding; `/api/model/info` added |
| [backend/requirements.txt](../backend/requirements.txt) | **MODIFIED** — added `joblib`; pinned `scikit-learn==1.9.0`; bounded `numpy` |
| [backend/test_backend_integration.py](../backend/test_backend_integration.py) | **NEW** — 46 stdlib-only integration tests |
| [backend/live_smoke_test.py](../backend/live_smoke_test.py) | **NEW** — 30 live HTTP + WebSocket checks against a real uvicorn server |
| [docs/BACKEND_ML_INTEGRATION.md](BACKEND_ML_INTEGRATION.md) | **NEW** — this document |

**Verified unchanged:** `ml_pipeline/` (git reports zero modifications), `final_model_v1.pkl`,
`model.pkl`, stage4-v2 feature code, and `frontend/`. No file was deleted.

---

## 2. What was implemented

### 2.1 The bridge — `backend/ml_inference.py`

The single place the backend touches ML. It contains **no feature maths**: the 52-vector is
produced only by `inference.transform_vitals_to_features` → `engineer_patient_rows_v2`
(proved by a test that patches the helper and asserts it is called).

**Import/path fix.** `inference.py` and `feature_engineering_v2.py` use bare sibling imports
(`from feature_engineering import …`), which resolve only when the `ml_pipeline` **directory**
is on `sys.path`; `main.py` previously added the project root only. The bridge derives both
paths from `__file__` and inserts them idempotently before importing `inference`. Nothing
depends on the current working directory, and no `ml_pipeline` file was edited.

**Model singleton.** `get_model()` loads `final_model_v1.pkl` once behind a double-checked
lock; `main.py` binds it at import so a missing artifact fails at boot, not mid-request.

**Vital-name adapter.** `adapt_snapshot()` renames generator keys to the names inference
accepts, drops the non-model `condition` field, and raises on any unmapped key so a future
generator change fails loudly rather than silently dropping a vital.

| generator | inference |
|---|---|
| `sys_bp` → `systolic_bp` | `dia_bp` → `diastolic_bp` |
| `resp_rate` → `respiratory_rate` | `temp` → `temperature` |
| `heart_rate`, `spo2`, `map` | unchanged |

**`evaluate(bed_id, vitals, commit, explain)`** appends to that bed's history (or scores
read-only), calls `predict()` and optionally `explain()`, and returns the model's dict
verbatim plus `bed_id`, `history_hours`, `history_sufficient`, `alert_actionable`,
`clinical_use: false`, and the disclaimer. Model-owned keys are never rewritten.

### 2.2 Patient history — `PatientHistoryStore`

A `Dict[bed_id, deque(maxlen=72)]` under a lock:

- **Isolation** — one deque per bed; nothing is shared or merged. Tested directly and via HTTP.
- **Chronology** — append-only at the tail.
- **No future data** — `window()` returns only what was already appended, so hour *t* can
  never see hour *t+1*. Tested by asserting the window sequence is exactly `[[80],[80,81],[80,81,82]]`.
- **Bounded** — `maxlen` evicts the oldest hour; `max_hours < 5` is rejected because
  stage4-v2 reaches back to *t−4*.
- **Copy-on-read/write** — callers cannot mutate stored history.

### 2.3 Cadence — the key semantic decision

stage4-v2 rows are **hourly**; the generator emits instantaneous samples. Committing every
1 Hz sample as an "hour" would mislabel the time axis and corrupt every temporal feature, so:

| Path | Commits a virtual hour? |
|---|---|
| `GET /api/patients` | No (`commit=False`) — polling stays side-effect-free |
| `GET /api/patients/{bed_id}` | No (`commit=False`) |
| `POST /api/simulate` | Yes — a simulated event advances that bed's clock |
| `WS /ws/telemetry` | Yes, once per `VIRTUAL_HOUR_SECONDS` (5 s); the other 1 Hz ticks score read-only |

Each bed is seeded at startup with `WARMUP_HOURS = 4` hourly readings **from its own
generator**, so the first live prediction has populated temporal features instead of an
all-imputed cold start. These rows are synthetic (as is every reading in this simulator),
strictly in the past, and never cross beds.

### 2.4 `main.py` wiring

`PatientAnomalyDetector` is no longer imported or instantiated, and `model.pkl` is never
read — verified by spying on `builtins.open`/`pickle.load` across a full request lifecycle
(0 reads of `model.pkl`, 1 read of `final_model_v1.pkl`). `model.py`/`model.pkl` remain on
disk and importable; only the scoring path changed. `VitalSignalGenerator`, the roster, and
60 Hz waveform generation are untouched.

The WebSocket per-tick payload was extracted into `build_vitals_payload(commit_hour)` so the
telemetry logic is testable without a socket.

---

## 3. API changes

All existing routes keep their paths, methods, and top-level shapes. `analysis` gained
final-model fields; the old keys (`risk_score`, `is_anomaly`, `detected_flags`,
`sepsis_probability`) are gone because they were the old detector's output.

```json
"analysis": {
  "model_version": "final-logreg-v1",
  "feature_version": "stage4-v2",
  "probability": 0.371,
  "risk_level": "MODERATE",
  "alert": true,
  "alert_actionable": false,
  "threshold": 0.36061602358147954,
  "risk_bands": { "moderate_cut": 0.36061602358147954, "high_cut": 0.7542800224324719 },
  "hours_supplied": 5, "features_present": 41, "features_total": 52,
  "history_hours": 5, "history_sufficient": true,
  "bed_id": "BED-101", "clinical_use": false,
  "explanations": [ { "feature": "spo2_max_4h", "raw_value": null, "was_imputed": true,
                      "log_odds_contribution": 0.3144, "direction": "increases risk" } ],
  "disclaimer": "Research/hackathon benchmark only. NOT a clinical diagnostic tool…"
}
```

- **New route:** `GET /api/model/info` — artifact identity, threshold, bands, feature count.
- **Explanations** are returned on `GET /api/patients/{bed_id}` and `POST /api/simulate`;
  omitted from the roster list and the telemetry tick for cost reasons.
- **`/ws/telemetry`** keeps `{ t, waveforms, vitals }` and its 60 Hz waveform rate; only the
  1 Hz `analysis` content changed.
- **Alerts** keep every legacy key and add `probability`, `model_version`, `feature_version`,
  `disclaimer`. `flags` now lists the risk-increasing features from the model explanation
  instead of rule-based strings.

**Alert gating.** `alert` (raw, `probability ≥ 0.3606`) is reported verbatim, but alert
*creation* is gated on `alert_actionable` (HIGH band) because the artifact's FPR ≈ 0.59 makes
the raw flag fire almost constantly. **The threshold and risk bands were not modified** —
this is a separate downstream flag.

---

## 4. Dependencies

```
numpy>=1.24.0,<3
scikit-learn==1.9.0   # matches the artifact's created_with; keeps unpickling reproducible
joblib>=1.3.0         # required by inference.py to load final_model_v1.pkl
```

`joblib` was the one genuinely missing package. No test framework was added — `pytest` and
`httpx` are absent from the environment, so both suites are plain scripts.

---

## 5. Tests and results

| # | Suite | Command | Result |
|---|---|---|---|
| 1 | Existing ML tests (regression) | `python test_inference.py` in `ml_pipeline/` | **17 passed, 0 failed** (unchanged baseline) |
| 2 | Backend integration — from project root | `python backend/test_backend_integration.py` | **46 passed, 0 failed** |
| 3 | Backend integration — from `backend/` | `python test_backend_integration.py` | **46 passed, 0 failed** |
| 4 | Live HTTP + WS — launched from project root | `python backend/live_smoke_test.py "PROJECT ROOT" 8021` | **30 passed, 0 failed** |
| 5 | Live HTTP + WS — launched from `backend/` | `python live_smoke_test.py "BACKEND DIR" 8022` | **30 passed, 0 failed** |
| 6 | `model.pkl` never read (open/pickle spy) | ad-hoc lifecycle probe | **PASS** — 0 old reads, 1 final-artifact read |
| 7 | Protected paths unmodified | `git status --porcelain -- ml_pipeline frontend` | **PASS** — no `ml_pipeline` entries |

**Total: 169 checks, 0 failures.**

Coverage by area — artifact identity (loads, singleton, `final-logreg-v1`, `stage4-v2`,
threshold `0.3606`, bands, 52 features, no old pickle, no duplicated feature code);
name adaptation (mapping, value fidelity, unknown-key rejection); history (isolation ×2,
chronology, no-future, external-mutation safety, bounds, invalid bound);
prediction (schema, probability validity, banding at every boundary, alert flag,
explanation shape, feature growth with history, `commit=False` purity, 4-bed concurrency,
non-clinical labelling); REST (`/api/model/info`, roster shape + legacy keys, read-only
purity, detail + explanations, both 404s, simulate isolation, alert generation and cap,
acknowledge + 404); WebSocket (payload shape, cadence boundary, 60 Hz waveforms, JSON
round-trip, handler accept/stream/cleanup on disconnect); imports (paths from `__file__`,
both launch dirs, both import styles, routes registered, roster intact).

### Reproduce

```bash
cd ml_pipeline && python test_inference.py
```

```bash
python backend/test_backend_integration.py
```

```bash
python backend/live_smoke_test.py "PROJECT ROOT" 8021
```

---

## 6. Remaining issues

1. **The model is weak and not deployment-ready.** FPR ≈ 0.59, precision ≈ 1.5%, AUROC ≈ 0.648.
   Every surface must keep the research-only disclaimer. Unchanged by this work — stated for the record.
2. **The frontend still does not consume this backend.** It runs in client-side demo mode and,
   in live mode, targets a different contract: `/api/predict/risk`, `/api/patients/{id}/vitals`,
   `/api/alerts/active`, `PUT /api/alerts/{id}/acknowledge`, and `ws://…/ws/vitals-stream`
   with per-patient messages and `P00x` ids (vs. `BED-10x` here). Reconciling this is the next
   phase; nothing was broken because nothing was connected.
3. **`MODERATE` has no frontend styling.** The model emits LOW/MODERATE/HIGH; the frontend
   knows LOW/MEDIUM/HIGH/CRITICAL, and `getRiskColor('MODERATE')` falls through to the green
   LOW style. A mapping is needed when the frontend is wired — deliberately not done here.
4. **A virtual hour is 5 s of wall clock**, chosen for demo responsiveness. It is a demo
   convention, not physiological time; `VIRTUAL_HOUR_SECONDS` is the single knob.
5. **Warm-up history is synthetic.** The 4 seeded hours come from the same synthetic generator
   as everything else in this simulator, but they are not real observations. `history_hours`
   and `features_present` expose the true state.
6. **History is in-process memory.** It resets on restart and is not shared across workers, so
   running uvicorn with `--workers > 1` would give each worker its own history. Single-worker
   is assumed, consistent with the existing in-memory `PATIENTS_DB` and `ALERTS_HISTORY`.
7. **`ml_pipeline/test_inference.py`'s consistency test** depends on local PhysioNet data
   (`data/processed_v2/`, `data/raw/physionet/`), so it is environment-dependent — it passed here.
8. **Not committed.** No `git commit` or `push` was performed, per instruction.
