# Backend ↔ ML Integration Plan

**Status:** PLAN ONLY — no code has been changed. This document is the deliverable for
this phase. Implementation is a separate, later phase.

**Scope of this phase:** Read-only inspection + written plan. Backend only.

**Hard constraints (must hold through implementation):**

- Do **not** modify, retrain, re-threshold, or replace `ml_pipeline/saved_models/final_model_v1.pkl`.
- Do **not** modify stage4-v2 feature engineering (`ml_pipeline/feature_engineering.py`, `ml_pipeline/feature_engineering_v2.py`).
- Do **not** use the old `ml_pipeline/model.pkl`.
- Do **not** recreate the 52 features by hand in the backend — reuse the existing inference/feature code.
- Do **not** touch the frontend in this phase.
- Do **not** use the test set; do **not** invent metrics; do **not** claim clinical validity.
- Keep per-patient histories isolated; never use future observations.

---

## 1. Current backend ML flow

Source: [backend/main.py](../backend/main.py), [ml_pipeline/model.py](../ml_pipeline/model.py),
[ml_pipeline/signal_generator.py](../ml_pipeline/signal_generator.py).

### How vitals are produced
- Each patient in `PATIENTS_DB` ([backend/main.py:31](../backend/main.py)) owns a
  `VitalSignalGenerator` instance. There are 4 beds: `BED-101`…`BED-104`.
- Vitals are generated **on demand** by `generator.get_vital_snapshot()`
  ([signal_generator.py:91](../ml_pipeline/signal_generator.py)), which returns an
  **instantaneous** snapshot with keys:
  `heart_rate, spo2, sys_bp, dia_bp, map, resp_rate, temp, condition`.
- **No history is stored anywhere.** Each call is a fresh, noisy snapshot around the
  generator's current baseline. There is no hourly cadence and no per-patient buffer.

### How risk is computed (the OLD path to be replaced)
- `anomaly_detector = PatientAnomalyDetector()` is created once
  ([backend/main.py:28](../backend/main.py)).
- `PatientAnomalyDetector.__init__` loads the **old** `ml_pipeline/model.pkl` via `pickle`
  ([model.py:6,16‑19](../ml_pipeline/model.py)).
- `PatientAnomalyDetector.predict(vitals)` ([model.py:35](../ml_pipeline/model.py)) is a
  **rule-based** scorer over a single instantaneous reading, optionally adding an old-model
  probability from a 7-column frame `["HR","O2Sat","Temp","SBP","MAP","DBP","Resp"]`. It
  returns:
  ```json
  { "risk_score": 0-100, "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "sepsis_probability": 0.0, "detected_flags": ["..."], "is_anomaly": bool }
  ```

### Where the old detector is used (4 sites)
| Location | Endpoint | Call |
|---|---|---|
| [main.py:86](../backend/main.py)  | `GET /api/patients`           | `anomaly_detector.predict(vitals)` |
| [main.py:106](../backend/main.py) | `GET /api/patients/{bed_id}`  | `anomaly_detector.predict(vitals)` |
| [main.py:135](../backend/main.py) | `POST /api/simulate`          | `anomaly_detector.predict(vitals)` (drives alert insert) |
| [main.py:209](../backend/main.py) | `WS /ws/telemetry`            | `anomaly_detector.predict(vitals)` at the ~1 Hz vital tick |

### Cadence today
- REST endpoints compute a **fresh snapshot per request**.
- `/ws/telemetry` streams ECG/PPG waveforms at ~60 Hz and emits `vitals + analysis` at
  ~1 Hz ([main.py:171‑224](../backend/main.py)). Packet shape: `{ t, waveforms, vitals }`.

**Bottom line:** the current backend is *instantaneous, stateless, and rule-based*, using
the old `model.pkl`. It is structurally incompatible with a model that needs per-patient
hourly temporal history.

---

## 2. Final ML flow (target)

Source: [ml_pipeline/inference.py](../ml_pipeline/inference.py) and the artifact itself
(loaded and inspected for this plan).

```
patient hourly history (chronological, per-patient)
   -> transform_vitals_to_features()            # inference.py
        -> engineer_patient_rows_v2()           # stage4-v2, EXACT training code
             -> 52-feature vector (last hour)
   -> final_model_v1.pkl Pipeline               # median impute -> standardize -> LogReg
        -> probability
        -> risk level (LOW / MODERATE / HIGH)
        -> alert (probability >= threshold)
        -> explanation (log-odds contributions)
```

### Entry point
- `SepsisRiskModel` ([inference.py:87](../ml_pipeline/inference.py)); loads the artifact via
  **joblib**. `DEFAULT_ARTIFACT` is resolved from `__file__`
  ([inference.py:34‑35](../ml_pipeline/inference.py)) → **CWD-independent**.
- `predict(readings)` accepts a **chronological list of hourly dicts** using the *friendly*
  vital names and returns:
  ```json
  { "model_version": "final-logreg-v1", "feature_version": "stage4-v2",
    "probability": 0.0-1.0, "risk_level": "LOW|MODERATE|HIGH",
    "alert": bool, "threshold": 0.3606…, "risk_bands": {...},
    "hours_supplied": N, "features_present": M, "features_total": 52,
    "disclaimer": "Research/hackathon benchmark; NOT a clinical diagnostic tool." }
  ```
- `explain(readings, top_k)` → list of
  `{ feature, raw_value, was_imputed, log_odds_contribution, direction }`.

### Accepted input schema (friendly names)
`heart_rate, spo2, respiratory_rate, temperature, systolic_bp, diastolic_bp, map`
(`VITAL_TO_PSV` + `map`, [inference.py:38‑46](../ml_pipeline/inference.py)). Unknown keys
raise `ValueError`. Missing/`None` values are allowed and treated as missing.

### Artifact facts (read from `final_model_v1.pkl` during this audit — do not change)
- `model_version`: **final-logreg-v1**
- `feature_version`: **stage4-v2** (52 features; matches `FEATURE_NAMES`)
- `threshold`: **0.36061602358147954**
- `risk_bands`: `moderate_cut = 0.36061602358147954`, `high_cut = 0.7542800224324719`
  (LOW < moderate_cut ≤ MODERATE < high_cut ≤ HIGH). The alert boundary equals the
  LOW/MODERATE boundary.
- `created_with`: `python 3.12.13, numpy 2.3.5, scikit_learn 1.9.0`
- Reported quality (the artifact's own metrics): test AUROC ≈ 0.648, **FPR ≈ 0.588,
  precision ≈ 0.015**. Explicitly *not deployment-ready*; ordinal research signal only.

### The critical rule
`transform_vitals_to_features` calls `engineer_patient_rows_v2("inference", raw_rows)` and
returns the **last** row's 52-vector ([inference.py:65‑84](../ml_pipeline/inference.py)).
The backend must therefore **hand the hourly history to `predict()`/`explain()` and never
build features itself**.

---

## 3. Patient-history design

The model needs per-patient temporal history; the backend currently has none. Proposed
(backend-only) design:

### Structure
- A per-patient **ordered buffer** of hourly readings, keyed by bed id
  (`BED-101` … `BED-104`). Conceptually `Dict[str, Deque[dict]]`.
- **Isolation:** one buffer per bed; readings are never shared or merged across beds.
- **Chronological, append-only:** new readings are appended to the end; nothing is inserted
  "in the past" and nothing after the current hour is ever fed in → **no future leakage**.
- The window passed to inference is exactly *"the current observation + available previous
  observations"* for that one patient.

### Reading schema (friendly names, via a key adapter)
The generator emits `sys_bp/dia_bp/resp_rate/temp`; inference expects
`systolic_bp/diastolic_bp/respiratory_rate/temperature`. A pure mapping is required:

| generator key | inference key |
|---|---|
| `heart_rate` | `heart_rate` |
| `spo2` | `spo2` |
| `sys_bp` | `systolic_bp` |
| `dia_bp` | `diastolic_bp` |
| `resp_rate` | `respiratory_rate` |
| `temp` | `temperature` |
| `map` | `map` |
| `condition` | *(dropped — not a model input)* |

### Window size (bounded — do not grow unbounded)
stage4-v2 temporal features look back at most to **t-4** (`change_4h`) with a 4-hour rolling
window (`t-3..t`). So the **minimum** window that fully populates the current hour's
temporal features is **5 hourly rows**. Recommendation: keep the last **~72** hourly rows
per patient (cheap, supports future charting) with a hard cap so memory is bounded.

### Cadence (the key semantic decision)
The generator is sub-second/instantaneous; stage4-v2 rows are **hourly** (1-based `ICULOS`
hour index synthesized in [inference.py:49‑62](../ml_pipeline/inference.py)). The backend
must define what constitutes "one hour" of history:
- **Recommended:** commit exactly **one representative reading per virtual hour** (advance a
  virtual clock per `/api/simulate` action and/or every fixed interval of the telemetry
  loop). One appended row = one model hour. This keeps `change_1h/change_4h` and the
  per-hour trend slope meaningful.
- **Avoid:** appending high-frequency (e.g. 1 Hz) snapshots and treating them as hourly —
  that mislabels the time axis and distorts every temporal feature.

### Cold start
Until ≥2 present values exist in a window, temporal features are `None` and get median-imputed
inside the Pipeline; early predictions lean on the imputation prior. This is expected and
must be surfaced (`hours_supplied`, `features_present`), not hidden.

---

## 4. Required backend changes (described, NOT implemented here)

1. **New backend helper module** (e.g. `backend/ml_inference.py`) that:
   - Resolves the import/path problem (see §6), then imports `SepsisRiskModel` from
     `ml_pipeline/inference.py`.
   - Loads the final model **once** (singleton) at import/startup.
   - Provides `adapt_snapshot(vitals) -> reading` (the key mapping above) and a
     `PatientHistoryStore` (append + bounded window, per bed).
   - Exposes a single `evaluate(bed_id, snapshot) -> analysis` that appends to history and
     calls `model.predict(window)` (+ `model.explain(window)` when an explanation is wanted).
   - **No feature math** lives here — it only marshals data in/out of `inference.py`.

2. **Swap the 4 call sites** ([main.py:86/106/135/209](../backend/main.py)) from
   `anomaly_detector.predict(vitals)` to the new `evaluate(...)`, preserving the surrounding
   response assembly.

3. **Keep `PatientAnomalyDetector` importable** (do not delete `model.py`/`model.pkl`), ideally
   behind a feature flag for rollback, but the new scoring path must **not** load `model.pkl`.

4. Keep `VitalSignalGenerator` and the waveform generation exactly as-is.

*(All of the above are backend-only and additive; none touch `ml_pipeline` code, the model,
or the frontend.)*

---

## 5. API / WebSocket impact

### REST (existing endpoints kept; fields added, not removed)
- `GET /api/patients`, `GET /api/patients/{bed_id}`, `POST /api/simulate`, `GET /api/alerts`,
  `POST /api/alerts/acknowledge` retain their paths and top-level shapes.
- The `analysis` object gains final-model fields (additive):
  `probability, risk_level (LOW|MODERATE|HIGH), alert, threshold, model_version,
  feature_version, hours_supplied, features_present`, and `explanations` where surfaced.
  Existing keys can be retained/derived for backward compatibility where practical.

### WebSocket `/ws/telemetry`
- Keep the 60 Hz waveform payload and the `{ t, waveforms, vitals }` packet shape.
- Change **only** the ~1 Hz vitals tick: commit a virtual-hour reading to that patient's
  history and compute the final-model `analysis` there (additive fields inside `analysis`).

### Frontend divergence (informational — out of scope this phase)
The React frontend currently runs in client-side **demo mode** and, in live mode, targets a
**different** REST/WS contract than the backend exposes:
`/api/predict/risk`, `/api/patients/{id}/vitals`, `/api/alerts/active`,
`PUT /api/alerts/{id}/acknowledge`, and WebSocket `/ws/vitals-stream` (per-patient messages).
It also uses the vocabulary `LOW/MEDIUM/HIGH/CRITICAL` and has no `MODERATE`. Reconciling
these is a **later** phase; because the frontend does not consume the current backend
endpoints, the backend changes above will not break it.

### Risk semantics (must be stated in responses)
`probability` is an **uncalibrated ordinal research signal**, not a clinical probability.
`alert` fires at `probability >= 0.3606…`. Bands: LOW < 0.3606… ≤ MODERATE < 0.7543… ≤ HIGH.

---

## 6. Import / path resolution (do it properly)

`inference.py` and `feature_engineering_v2.py` use **bare, sibling imports**
(`from feature_engineering import …`, `from feature_engineering_v2 import …`,
[inference.py:31‑32](../ml_pipeline/inference.py)). These resolve only when the
**`ml_pipeline/` directory itself** is on `sys.path` (which is why
[ml_pipeline/test_inference.py](../ml_pipeline/test_inference.py) works — it runs with
`ml_pipeline/` as `sys.path[0]`).

Today `backend/main.py:12` adds only the **project root**, and imports the package
(`from ml_pipeline import …`), whose `__init__` does not touch `inference.py`. Importing
`inference.py` under that setup would fail with `ModuleNotFoundError: feature_engineering`.

**Clean fix (backend-only, no edits to `ml_pipeline`):** in the new backend helper, compute
both the project root and the `ml_pipeline` directory from `__file__` and insert **both**
onto `sys.path` (idempotently) *before* importing `inference`. This is independent of the
launch directory (project root **or** `backend/`) and does not rely on CWD. No duplication
of `feature_engineering.py` or inference logic is introduced.

---

## 7. Dependency changes (`backend/requirements.txt`)

Current file lists: `fastapi, uvicorn, websockets, numpy, pydantic, scikit-learn (>=1.2.0),
pandas`.

- **Add `joblib`** — `inference.py` imports it directly; it is currently missing. (Required.)
- **Pin `scikit-learn==1.9.0`** to match the artifact's `created_with` (currently `>=1.2.0`,
  which risks unpickling breakage on a future major). The audit env already has 1.9.0 and
  loads the artifact cleanly.
- **numpy**: artifact built with 2.3.5; audit env has 2.4.6 and tests pass — keep compatible
  (advisory pin, e.g. `>=1.24,<3`).
- **pandas**: still used by the old `model.py`; keep unless the detector is fully removed.
- No other packages. **No test framework will be added** (see §8).

---

## 8. Testing strategy

### Preserve the baseline (verified during this audit)
- [ml_pipeline/test_inference.py](../ml_pipeline/test_inference.py) currently passes
  **17/17**. The integration must not shadow `feature_engineering`/`inference` or otherwise
  break this. It must stay green.

### New backend tests — standalone stdlib script (no new deps)
`httpx` and `pytest` are **not installed**, and the constraint is to avoid unrelated
packages. FastAPI's `TestClient` needs `httpx`, so tests will be written as a plain script
(same style as `test_inference.py`) that imports the backend app module and calls the route
functions and ML-helper directly. Coverage:
1. Model loads once (singleton).
2. Single-patient inference returns the full schema.
3. Patient-history isolation (BED-101 vs BED-102 never mix).
4. Chronological append behavior.
5. No-future-data guarantee (window ⊆ appended-so-far).
6. 52-feature path goes through `inference.py` (features not recomputed in backend).
7. `model_version == final-logreg-v1`.
8. `feature_version == stage4-v2`.
9. `threshold == 0.3606…` (unchanged).
10. Risk-level banding (LOW/MODERATE/HIGH).
11. Explanation shape.
12. Multiple patients concurrently.
13. Existing REST endpoint functions still return their expected shapes.
14. WS vitals-builder helper produces a valid packet.
15. `/api/simulate` still works.
16. Alert generation from the new path.
- Run the suite from **both** the project root and `backend/` to prove import robustness (§6).

---

## 9. Risks

- **Over-alerting.** Artifact FPR ≈ 0.59, precision ≈ 1.5%. Wired naively, alerts will flood.
  Mitigation (without changing threshold/bands): for demo UX, raise alerts only at the HIGH
  band while still reporting `probability`/`risk_level`; always show the benchmark disclaimer.
- **Cadence mislabeling.** Treating sub-hourly samples as hourly distorts every temporal
  feature. Mitigation: commit exactly one reading per virtual hour (§3).
- **Cold start.** Early predictions rely on median imputation until history accrues; report
  `hours_supplied`/`features_present`.
- **Vocabulary mismatch (future frontend phase).** Model emits `MODERATE`; the frontend has
  no such level (`getRiskColor` falls through to the LOW/green style and the badge prints the
  literal text). Must be mapped when the frontend is wired — not this phase.
- **Version skew on unpickling.** Mitigated by pinning `scikit-learn==1.9.0` (§7).
- **Performance.** Feature engineering runs per prediction over the window. Fine at the ~1 Hz
  vitals tick for 4 patients with a bounded window; **do not** call the model at the 60 Hz
  waveform rate.
- **Unbounded memory.** Mitigated by the capped per-patient buffer (§3).
- **Not clinical.** The signal is a research/hackathon benchmark only; no clinical claims.

---

## 10. What this phase does NOT do

- No `.py`, frontend, or model files are modified.
- The model is not retrained/re-thresholded; `model.pkl` is not used; the test set is not touched.
- Frontend contract reconciliation and the actual code edits are deferred to the
  implementation phase, to be executed against this plan.

**END OF PLAN — stopping here per instruction (no implementation in this phase).**
