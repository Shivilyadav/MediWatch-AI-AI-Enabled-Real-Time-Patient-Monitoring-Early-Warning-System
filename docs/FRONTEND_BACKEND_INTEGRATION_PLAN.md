# Frontend ↔ Backend Integration Plan

Read-only inspection of the **current** React 19 + Vite + Tailwind 4 + Recharts + Three.js
frontend and the **already-integrated** FastAPI backend (final-logreg-v1 / stage4-v2).
This document is the Phase 1 deliverable; implementation follows in Phase 2.

**Target flow:**
`Frontend → FastAPI REST/WebSocket → backend/ml_inference.py → ml_pipeline/inference.py → stage4-v2 → final_model_v1.pkl → probability + risk + explanations → dashboard`

> **Not a clinical tool.** The model score is an uncalibrated research/hackathon benchmark
> (artifact metrics: AUROC ≈ 0.648, FPR ≈ 0.59, precision ≈ 1.5%). Every surface keeps the
> existing prototype disclaimer. This phase does **not** touch `ml_pipeline/`,
> `final_model_v1.pkl`, `stage4-v2`, `model.pkl`, the threshold, or the backend endpoints
> (unless a change is unavoidable, in which case it is called out here).

---

## 0. Inspection scope

Every file under `frontend/` was read (48 files). Two of the 14 nominated inspection
targets **do not exist** in the current tree and are noted for the record:

- `frontend/src/api/` — **absent.** API lives in [`src/services/api.js`](../frontend/src/services/api.js).
- `frontend/src/data/` — **absent.** Seed data lives in [`src/simulator/demoData.js`](../frontend/src/simulator/demoData.js).

There is **no `node_modules`** in `frontend/`, so `npm install` is a prerequisite to any
build. `vite.config.js` has **no dev-server proxy**, so the browser calls the backend
cross-origin — the backend already sets `allow_origins=["*"]`, so CORS is satisfied.
There is no TypeScript, no typecheck script, and no test runner; `lint` is `oxlint`.

---

## 1. REST endpoints — frontend calls vs. backend reality

All frontend REST lives in [`src/services/api.js`](../frontend/src/services/api.js). Every
function short-circuits when `VITE_DEMO_MODE === 'true'` and otherwise **silently falls back
to local demo state on any error** — so a wrong URL never surfaces as a visible failure.

| Frontend function | Frontend calls | Backend actually serves | Verdict |
|---|---|---|---|
| `getPatients()` | `GET /api/patients` | `GET /api/patients` | ✅ path matches (shape differs, see §5) |
| `getPatientVitals(id)` | `GET /api/patients/{id}/vitals` | — | ❌ **does not exist** |
| `getPatientAlerts(id)` | `GET /api/patients/{id}/alerts` | — | ❌ **does not exist** |
| `getActiveAlerts()` | `GET /api/alerts/active` | `GET /api/alerts` | ❌ wrong path |
| `ingestVitals(data)` | `POST /api/vitals/ingest` | — | ❌ **does not exist** |
| `predictRisk(data)` | `POST /api/predict/risk` | — | ❌ **does not exist** |
| `acknowledgeAlert(id)` | `PUT /api/alerts/{id}/acknowledge` | `POST /api/alerts/acknowledge` `{alert_id}` | ❌ wrong method + shape |
| — | — | `GET /api/patients/{bed_id}` | ⚠️ backend has it; frontend never calls it |
| — | — | `GET /api/model/info` | ⚠️ backend has it; frontend never calls it |
| — | — | `POST /api/simulate` `{bed_id, condition}` | ⚠️ backend has it; frontend never calls it |

**Backend REST contract (source of truth):**
- `GET /api/patients` → list of `{id, name, age, gender, admission_type, doctor, vitals, analysis}`
- `GET /api/patients/{bed_id}` → same, plus `analysis.explanations`
- `GET /api/model/info` → artifact identity/threshold/bands/feature counts
- `POST /api/simulate` `{bed_id, condition}` → `{status, bed_id, new_condition, analysis}`
- `GET /api/alerts` → list (most recent first, capped 50)
- `POST /api/alerts/acknowledge` `{alert_id}` → `{status:"acknowledged", alert_id}`

**Plan:** rewrite `api.js` to exactly these six routes. Drop `getPatientVitals`,
`getPatientAlerts`, `ingestVitals`, `predictRisk` (no backend counterpart; history now comes
from the live WS stream — see §2/§8). Add `getPatient(bedId)`, `getModelInfo()`,
`simulateCondition(bedId, condition)`. The `VITE_DEMO_MODE` flag is retained as an explicit
escape hatch, but live backend data becomes the default and primary path.

---

## 2. WebSocket URL & packet shape

| | Frontend ([`src/services/websocket.js`](../frontend/src/services/websocket.js)) | Backend ([`backend/main.py`](../backend/main.py)) |
|---|---|---|
| URL | `ws://localhost:8000/ws/vitals-stream` (via `VITE_WS_URL`) | `ws://localhost:8000/ws/telemetry` |
| Message the handler expects | a per-patient object with `data.patient_id` | a bed-keyed packet (below) |

**Backend packet (≈60 Hz waveforms, ≈1 Hz vitals):**
```json
{
  "t": 12.34,
  "waveforms": { "BED-101": {"ecg": 0.12, "ppg": 0.34}, "BED-102": {…}, … },
  "vitals": {
    "BED-101": { "vitals": { "heart_rate": 74, … }, "analysis": { …ML… } },
    …
  }
}
```
`vitals` is `null` on the ticks between 1 Hz boundaries; `analysis` in the WS stream is
computed with `explain=False` (no `explanations` array — those come from the REST detail
route and `/api/simulate`).

**Plan:** default `VITE_WS_URL` → `ws://localhost:8000/ws/telemetry`; the message handler
in `PatientContext` parses the bed-keyed `vitals` map (ignoring `waveforms` for the vitals
path — waveforms can drive the existing chart/ECG visuals later, but are out of scope for
the risk pipeline) and updates each matching patient. The `data.patient_id` branch is
replaced. Reconnect/backoff logic is kept as-is.

---

## 3. Patient ID format

- **Frontend:** `P001`–`P005` (5 patients), default selected `P003`; routes are
  `/patient/:patientId`, the mobile route hardcodes `/mobile-alert/ALT-P003-01`.
- **Backend:** `BED-101`–`BED-104` (4 beds), field name is `id` (not `patient_id`).

**Plan:** the backend is the source of truth → the frontend roster becomes the 4 real beds
keyed by `BED-10x`. A normalization layer maps backend `id → patient_id` so the existing
components (which read `patient.patient_id`) keep working without a wholesale rename.
The hardcoded `ALT-P003-01` nav link and the `patients[2]` fallback are updated to be
data-driven (first bed / first alert) so they don't dangle when ids change.

---

## 4. Vital-sign field names

| Concept | Backend `vitals` key | Frontend/UI key | ML/inference key |
|---|---|---|---|
| Heart rate | `heart_rate` | `heart_rate` | `heart_rate` |
| SpO₂ | `spo2` | `spo2` | `spo2` |
| Systolic BP | `sys_bp` | `systolic_bp` | `systolic_bp` |
| Diastolic BP | `dia_bp` | `diastolic_bp` | `diastolic_bp` |
| Resp. rate | `resp_rate` | `respiratory_rate` | `respiratory_rate` |
| Temperature | `temp` | `temperature` | `temperature` |
| MAP | `map` | (derived) | `map` |
| Condition | `condition` | — | (dropped before ML) |

The frontend everywhere uses the long names (`systolic_bp`, `respiratory_rate`,
`temperature`); the backend telemetry emits the short generator names (`sys_bp`, `resp_rate`,
`temp`). (Note: `backend/ml_inference.py` already remaps short→long for the *model*, but the
REST/WS `vitals` object the frontend receives still carries the **short** names.)

**Plan:** a single `adaptVitals(backendVitals)` helper in the frontend maps short→long once,
at the ingestion boundary (REST + WS), so all downstream components stay unchanged. This is
purely a display adapter; it does not touch the ML feature path.

---

## 5. Risk object structure

- **Frontend expects** `patient.risk = {score, level, predicted_event, time_horizon, explanations}`
  with `level ∈ {CRITICAL, HIGH, MEDIUM, LOW, NORMAL}` and `score` a 0–1 float rendered as a
  percentage.
- **Backend provides** `patient.analysis = {model_version, feature_version, probability,
  risk_level, alert, alert_actionable, threshold, risk_bands, hours_supplied, features_present,
  features_total, history_hours, history_sufficient, bed_id, clinical_use, disclaimer,
  explanations?}` with `risk_level ∈ {LOW, MODERATE, HIGH}` and `probability` a 0–1 float.

**Plan:** map backend `analysis` → the frontend `risk` object at the adapter boundary:
`score ← probability`, `level ← risk_level`, `explanations ← explanations`. `predicted_event`
and `time_horizon` have no backend equivalent — derive them from `risk_level` (via the
existing `riskUtils` helpers, relabelled as descriptive, non-predictive text) or drop the
"predicted event / time horizon" framing to avoid implying a calibrated forecast. Carry the
benchmark fields (`probability`, `threshold`, `history_sufficient`, `features_present/total`,
`disclaimer`, `clinical_use`) through so the UI can label the score honestly (§ MODEL SCORE).

### Risk-level vocabulary mapping (the required explicit mapping)

The model emits **three** ordinal bands; the UI has **four** visual tiers. Mapping, chosen so
no band is ever misrepresented and `MODERATE` never renders as green/LOW:

| Backend `risk_level` | Meaning (band) | Frontend visual tier | Color |
|---|---|---|---|
| `HIGH` | `probability ≥ 0.7543` | **HIGH** (most severe tier shown) | red |
| `MODERATE` | `0.3606 ≤ p < 0.7543` | **MODERATE** (new amber tier) | amber |
| `LOW` | `p < 0.3606` | **LOW** | green |

- The 4th UI tier (`CRITICAL`) is **retained in the styling map** but is **not produced by the
  model** — it is only reachable by the demo/simulator engine or legacy alerts. Live ML risk
  therefore renders in exactly the three real bands. This is documented in the UI (a small
  "3-band model" note) rather than silently collapsing tiers.
- `getRiskColor()` gains an explicit `MODERATE` case (amber) — today `MODERATE` falls through
  the `switch` to the green LOW/NORMAL default, which would misrepresent a moderate-risk
  patient as stable. This is the single most important correctness fix in the UI layer.
- `getRiskLevelFromScore()` (score→label thresholds `0.85/0.65/0.45`) is **demo-only** and is
  kept for the simulator; it is not applied to backend results (which already carry a label).

---

## 6. Alert structure

- **Frontend expects** `{alert_id, patient_id, patient_name, severity, reason, risk_score,
  news2_score?, timestamp (ISO), status ∈ {ACTIVE,ACKNOWLEDGED,RESOLVED}, vitals_snapshot?}`.
- **Backend provides** `{alert_id, bed_id, patient_name, timestamp ("HH:MM:SS"), risk_level,
  flags:[feature names], vitals, acknowledged: bool, probability, model_version,
  feature_version, disclaimer}`.

Divergences: `patient_id`↔`bed_id`; `severity`↔`risk_level`; `reason` (prose) ↔ `flags`
(feature-name list); `risk_score`↔`probability`; `status` (tri-state string) ↔ `acknowledged`
(bool); `timestamp` is a full ISO string on the frontend but a bare `HH:MM:SS` on the backend.

**Plan:** map backend alerts → the frontend alert shape at the adapter boundary:
`patient_id ← bed_id`, `severity ← risk_level` (LOW/MODERATE/HIGH), `risk_score ← probability`,
`status ← acknowledged ? 'ACKNOWLEDGED' : 'ACTIVE'`, and synthesize `reason` from `flags`
(join the risk-increasing feature names into readable text). `acknowledgeAlertAction` calls
`POST /api/alerts/acknowledge {alert_id}` and reconciles `acknowledged`. Because the backend
only creates alerts on the HIGH band (`alert_actionable`), the Active Alert Queue is driven by
`GET /api/alerts`, not by client-side generation.

---

## 7. Explanation structure ("SHAP")

- **Frontend** ([`SHAPExplainer.jsx`](../frontend/src/components/patient/SHAPExplainer.jsx))
  expects `{feature, value, contribution (signed float), status (label), direction:'positive'|'negative'}`,
  labels the panel **"Explainable AI (SHAP) … XGBoost SHAP Live Output"**, and says "Positive
  SHAP values push predicted risk higher." The values are **fabricated** by
  [`riskEngine.generateSHAPExplanations()`](../frontend/src/simulator/riskEngine.js) with
  hardcoded weights, and it invents a pseudo-feature "NEWS2 Score."
- **Backend** returns `{feature, raw_value, was_imputed, log_odds_contribution (signed float),
  direction:'increases risk'|'decreases risk'}` — real **logistic-regression log-odds
  contributions**, top-k, from `model.explain()`. There is **no SHAP and no XGBoost** anywhere
  in the final pipeline.

**Plan:** rewrite `SHAPExplainer` to consume the backend shape:
`contribution ← log_odds_contribution`, positive/negative ← `direction === 'increases risk'`,
`value ← raw_value` (showing "imputed" when `was_imputed`). Rename the panel to
**"Model Feature Contributions"** with subtitle *"Logistic-regression log-odds contributions
(research benchmark)."* Remove every "SHAP"/"XGBoost" string. The fabricated generator is
demoted to demo-mode only. The footer text changes to explain log-odds, not SHAP.

---

## 8. Current simulator / risk-engine usage

- [`PatientContext`](../frontend/src/context/PatientContext.jsx) runs a **client-side clock**
  (`setInterval`, `2000/speed` ms) that calls
  [`runSimulationTick`](../frontend/src/simulator/patientSimulator.js) →
  [`calculateDemoRisk`](../frontend/src/simulator/riskEngine.js) →
  [`checkAndGenerateAlerts`](../frontend/src/simulator/alertEngine.js) for the selected patient
  and `NORMAL` for the rest. This is the **primary** risk path today and it **never contacts
  the backend**.
- [`scenarios.js`](../frontend/src/simulator/scenarios.js) defines 5 scenarios with **hardcoded
  `riskScore` per stage** — pure demo theatrics.
- The Simulator page ([`Simulator.jsx`](../frontend/src/pages/Simulator.jsx)) drives all of the
  above via `SimulatorControls` / `ScenarioSelector` / `SimulationStatus`.

**Plan (PATIENT DATA directive — backend is source of truth):**
- **Live mode (default):** the client-side risk clock is **disabled as the primary source**.
  Vitals + ML risk come from the WS telemetry stream and REST. `calculateDemoRisk` is **not**
  used to produce the displayed risk while connected.
- **Simulator controls are preserved** but rewired: the scenario/condition selector maps to
  the backend's `POST /api/simulate {bed_id, condition}` (backend conditions: Normal,
  Bradycardia, Tachycardia, Arrhythmia, Hypoxia, Fever), so a demo action advances the **real**
  model on the **real** bed. The relationship is made explicit in the UI ("Sends condition to
  backend; risk below is the live model's response"), satisfying "do not allow the frontend
  simulator to silently override backend ML results."
- The frontend scenario multi-stage curves (which have no backend analog) are kept only as a
  **demo-mode** fallback (`VITE_DEMO_MODE=true`), clearly labelled; they do not run in live
  mode.

---

## 9. Current NEWS2 usage

- [`news2.js`](../frontend/src/utils/news2.js) implements the standard NEWS2 score and derived
  vitals (MAP, shock index, pulse pressure); it is computed client-side from vitals and shown
  in [`RiskGauge`](../frontend/src/components/patient/RiskGauge.jsx),
  [`PatientCard`](../frontend/src/components/dashboard/PatientCard.jsx),
  [`NEWS2Timeline`](../frontend/src/components/patient/NEWS2Timeline.jsx), and the KPI/alert
  copy. The backend does **not** compute NEWS2.

**Plan (NEWS2 directive — keep, and keep separate):** NEWS2 stays as a **client-side reference
score** computed from the live backend vitals. It is visually and textually separated from the
ML benchmark: the ML card is labelled "Model risk (benchmark)"; the NEWS2 card is labelled
"NEWS2 (reference score)". They are never summed or conflated. `news2.js` is unchanged; it just
receives real vitals instead of simulated ones. The fabricated "NEWS2 Score" pseudo-feature is
removed from the ML explanation panel (§7).

---

## 10. Current SHAP / explanation usage

Covered in §7. Summary of the three inaccuracies being corrected: (a) the panel is labelled
SHAP/XGBoost though the model is logistic regression with log-odds contributions; (b) the
values are fabricated client-side; (c) a non-model "NEWS2 Score" is injected as a feature.
All three are fixed by rendering the backend `explanations` array and relabelling the panel.

---

## Divergence summary (one place)

| # | Divergence | Resolution |
|---|---|---|
| 1 | 5 frontend REST routes don't exist + wrong ack method | Rewrite `api.js` to the 6 real routes |
| 2 | WS path `/ws/vitals-stream` vs `/ws/telemetry` | Repoint default URL |
| 3 | WS handler wants `data.patient_id`; backend sends bed-keyed packet | Rewrite handler to parse `vitals` map |
| 4 | IDs `P00x` vs `BED-10x`, field `patient_id` vs `id` | Adapter maps `id→patient_id`; roster = 4 real beds |
| 5 | Vital keys `systolic_bp/…` vs `sys_bp/…` | `adaptVitals()` short→long at ingestion |
| 6 | `risk{score,level}` vs `analysis{probability,risk_level}` | Adapter maps analysis→risk |
| 7 | 4 UI tiers vs 3 model bands; `MODERATE` renders green | Add `MODERATE` amber case; documented mapping |
| 8 | Alert shape mismatch (7 field diffs) | Adapter maps backend alert→frontend alert |
| 9 | Explanation: fabricated SHAP/XGBoost vs real log-odds | Render backend fields; relabel "Model Feature Contributions" |
| 10 | Client-side `calculateDemoRisk` is primary risk | Demote to demo-only; live = backend |
| 11 | `isDemoMode` defaults `true` | Default to live; demo is explicit opt-in |
| 12 | Score shown as clinical % | Relabel as uncalibrated benchmark; keep disclaimer |
| 13 | No `node_modules` | `npm install` before build |

---

## Phase 2 implementation order

1. **`.env.example`** — `VITE_DEMO_MODE=false`, `VITE_WS_URL=…/ws/telemetry`.
2. **`src/services/api.js`** — rewrite to the 6 real routes; add `adaptVitals`/`adaptAnalysis`/
   `adaptPatient`/`adaptAlert` adapters (or place adapters in a small `src/services/adapters.js`).
3. **`src/services/websocket.js`** — default URL → `/ws/telemetry`.
4. **`src/context/PatientContext.jsx`** — load roster via REST on mount; consume bed-keyed WS
   packet; per-bed history buffer (bounded, isolated, chronological, append-only); default live;
   `summaryMetrics` gains a `moderateCount`; simulator actions call `POST /api/simulate`.
5. **`src/utils/formatters.js`** — add `MODERATE` case to `getRiskColor`.
6. **`src/components/patient/SHAPExplainer.jsx`** — backend explanation shape + relabel.
7. **`RiskGauge` / `PatientCard` / `MobileAlert` / `KPISection` / `StatusBadge`** — MODERATE
   tier, benchmark labelling, NEWS2 separation, ack wiring.
8. **Simulator components** — map scenario/condition to `POST /api/simulate`; label the
   backend relationship; keep demo curves behind `VITE_DEMO_MODE`.

## Testing (Phase 2 exit criteria)

Build & static: `npm install` → `npm run build` (must succeed) → `npm run lint`.
Live: run backend (`uvicorn main:app` from `backend/`), serve the frontend, verify REST reaches
backend, WS connects to `/ws/telemetry`, patient cards render real vitals, charts update, real
ML risk + band render, `MODERATE` shows amber (never green), alerts display, feature
contributions render from backend, NEWS2 stays separate, patient switching works, beds stay
isolated. Regression: `ml_pipeline/test_inference.py` (17/17) and
`backend/test_backend_integration.py` (46/46) must still pass. **No commit, no push.**

## Guardrails (unchanged, restated)

Do **not** modify `ml_pipeline/`, `final_model_v1.pkl`, `stage4-v2`, `model.pkl`, the threshold,
or the risk bands. Do **not** retrain. Do **not** fabricate metrics or claim clinical validity.
Prefer adapting the frontend over changing the tested backend endpoints. Do **not** commit or
push.
