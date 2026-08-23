# MediWatch AI — ML Repository and Dataset Audit

**Scope:** Stage 1 audit only. No ML source, model artifact, backend API, or frontend code was changed.

## 1. Repository overview

The application has three coupled parts:

- `backend/main.py`: FastAPI service, REST endpoints, WebSocket telemetry, in-memory patient roster and alert history.
- `frontend/`: static HTML/CSS/JavaScript dashboard. It receives REST and WebSocket payloads and renders simulated telemetry and risk status.
- `ml_pipeline/`: a PhysioNet loader/trainer, a pickled model, a detector/inference wrapper, a data downloader, and a synthetic signal generator.

The dataset is stored in `ml_pipeline/data/raw/physionet/`, with 500 PSV files in `training_setA` and 500 in `training_setB`.

## 2. Current ML architecture

`backend/main.py` creates one `PatientAnomalyDetector` at process start. The detector attempts to load `ml_pipeline/model.pkl` once, then runs `predict(vitals)` for each REST request, simulation event, and one-Hz WebSocket vital update.

The detector is hybrid:

1. Hand-written threshold rules accumulate an `anomaly_score` and textual physiological flags.
2. If the pickle loads, a Random Forest probability is calculated from seven instantaneous vital signs.
3. A probability over 0.4 adds `probability * 30` to the rule-derived score. The capped score determines the displayed risk tier.

Therefore, the dashboard's risk score is **not** the ML probability and should not currently be described as a pure learned-model output.

## 3. Current model

- Expected model type: `sklearn.ensemble.RandomForestClassifier` (confirmed by training code and pickle metadata).
- Artifact: `ml_pipeline/model.pkl`, 3,178,536 bytes; pickle metadata records scikit-learn 1.9.0.
- Training parameters in source: `n_estimators=100`, `max_depth=10`, `random_state=42`, `class_weight="balanced"`.
- Features, in order: `HR`, `O2Sat`, `Temp`, `SBP`, `MAP`, `DBP`, `Resp`.
- Output used: `predict_proba(...)[0][1]`.

The audit environment does not have NumPy, pandas, or scikit-learn installed, so deserializing the pickle itself was not possible here. Its expected class and schema are nevertheless directly established by the source and embedded pickle metadata. In deployment, a pickle/version compatibility failure is silently swallowed by `model.py`, leaving `sepsis_probability` at `0.0`.

## 4. Current training pipeline

`train_physionet.py` recursively finds PSV files, takes up to 2,000 files, selects the seven features plus `SepsisLabel`, concatenates all patient rows, drops only rows where every feature is absent, and fills missing values with the median of the **entire combined dataset**.

It then calls `train_test_split(..., test_size=0.2, random_state=42, stratify=y)` on rows, trains the Random Forest, prints a classification report and AUROC, and overwrites `model.pkl`.

There is no validation set, no grouped split, no saved split manifest, no temporal features, no threshold selection, no feature pipeline artifact, and no experiment/metric metadata saved with the model.

## 5. Dataset statistics

| Measure | Observed value |
|---|---:|
| PSV files / patients | 1,000 / 1,000 |
| Total hourly readings | 38,890 |
| Mean readings per patient | 38.89 |
| Min / Q1 / median / Q3 / max readings | 8 / 24 / 39 / 47 / 327 |
| Temporal ordering | `ICULOS` increases exactly by 1 on all 37,890 within-file steps |
| First `ICULOS` value | Usually 1 (776 files); remaining files begin later, up to 30 |

The PSV schema has 41 columns:

`HR`, `O2Sat`, `Temp`, `SBP`, `MAP`, `DBP`, `Resp`, `EtCO2`, `BaseExcess`, `HCO3`, `FiO2`, `pH`, `PaCO2`, `SaO2`, `AST`, `BUN`, `Alkalinephos`, `Calcium`, `Chloride`, `Creatinine`, `Bilirubin_direct`, `Glucose`, `Lactate`, `Magnesium`, `Phosphate`, `Potassium`, `Bilirubin_total`, `TroponinI`, `Hct`, `Hgb`, `PTT`, `WBC`, `Fibrinogen`, `Platelets`, `Age`, `Gender`, `Unit1`, `Unit2`, `HospAdmTime`, `ICULOS`, `SepsisLabel`.

## 6. Missing-data analysis

The files encode missing numeric values as `NaN`, not blank cells. Core-vital missingness is:

| Feature | Missing readings | Missing % |
|---|---:|---:|
| HR | 3,861 | 9.93% |
| O2Sat | 5,147 | 13.23% |
| Temp | 25,701 | 66.09% |
| SBP | 5,541 | 14.25% |
| MAP | 4,779 | 12.29% |
| DBP | 11,798 | 30.34% |
| Resp | 6,276 | 16.14% |
| SepsisLabel | 0 | 0.00% |

Most laboratory variables are highly missing (for example, lactate 97.29%, AST 98.26%, direct bilirubin 99.78%); they should not be added to a real-time model without an explicit missingness strategy. `Age`, `Gender`, `HospAdmTime`, `ICULOS`, and `SepsisLabel` are complete. `Unit1` and `Unit2` are each 37.91% missing.

The seven core measurements include extreme values: HR 26.5–180, O2Sat 24–100, temperature 23.6–40.5 C, SBP 20–269, MAP 20–294, DBP 23–287, and Resp 1–61.5. These require clinically reviewed artifact handling; they must not be blindly discarded as deterioration can be genuinely abnormal.

## 7. Class imbalance

| Label | Rows | Share |
|---|---:|---:|
| 0 | 38,216 | 98.27% |
| 1 | 674 | 1.73% |

There are 71 patients with at least one positive label and 929 with none. This is a severe row-level imbalance; accuracy is not an adequate evaluation measure. Future training should report AUPRC, sensitivity, specificity, PPV/NPV, F1, false-positive rate, confusion matrix, and AUROC on held-out patients.

## 8. Current feature list

The learned model uses only the instantaneous values: `HR`, `O2Sat`, `Temp`, `SBP`, `MAP`, `DBP`, and `Resp`.

## 9. Missing feature requirements

The project-required set has several gaps:

- Naming/adaptation is needed for simulator inputs (`heart_rate`, `spo2`, `resp_rate`, `sys_bp`, `dia_bp`, `temp`) versus PhysioNet columns.
- Core vital coverage exists except that pulse pressure is not available as a model feature.
- Missing derived features: pulse pressure, shock index, and SpO2/RR ratio. MAP is present as a raw measurement but should have a defined fallback/validation rule when absent.
- Missing temporal features: one- and four-hour changes, causal rolling mean/standard deviation/minimum/maximum, and causal trend/slope.
- Missing explicit data-quality/missingness indicators and any causal preprocessing feature schema.

## 10. Current target/label behavior

In the audited files, `SepsisLabel` is binary, never missing, and positive labels are terminal within every positive patient:

- All 71 positive patients have one contiguous positive run extending to the end of the recorded sequence.
- The positive run has 6–10 readings (median 10).
- First positive label occurs from ICU hour 0 through 265 (median 39).
- There are 62 observed `0 → 1` transitions, 603 `1 → 1` transitions, and no `1 → 0` transitions; 9 patients begin their available sequence already positive.

For the PhysioNet 2019 challenge convention, `SepsisLabel=1` denotes the sepsis-positive period beginning six hours before the dataset's sepsis-onset time and persisting thereafter. The observed terminal, persistent runs are consistent with that convention. Thus the current row label is a challenge label, not necessarily a clean "new deterioration in the next six hours" label at every positive row: it also labels ongoing/post-onset states.

**Recommended target:** preserve the original label for comparability, but construct and document a separate prospective target only after defining an onset proxy. For patients with a `0 → 1` transition, infer the challenge onset proxy as `first_positive_hour + 6`, then label only pre-onset rows whose prospective six-hour window contains that proxy. Exclude post-onset rows from prospective early-warning training/evaluation. Treat patients already positive at the first available row separately because their lead time cannot be established from the available record. This convention must be validated against the dataset documentation and written into the experiment manifest before implementation.

## 11. Leakage risks

### Patient-level leakage — present

The current `train_test_split` happens after rows from all patients have been concatenated. Readings from the same patient can therefore be in both train and test partitions. Correlated trajectories and patient-specific baselines make test performance optimistic. This must be replaced by a deterministic patient-level train/validation/test split (for example 70/15/15) before any model comparison.

### Temporal leakage — not explicit in current features, but unprotected

The present features are instantaneous, so there is no explicit future rolling window. However, the pipeline does not preserve patient identifiers or time after concatenation, so it cannot enforce causal feature construction in a future feature-engineering stage. Any temporal feature must use only rows at or before the prediction row and be calculated independently per patient.

### Future-label leakage — current target is unsuitable for a pure lead-time claim

Training directly on persistent `SepsisLabel` positives teaches both pre-onset and post-onset recognition. It does not by itself demonstrate that a model predicts a future event. The prospective target definition above is required for valid early-warning/lead-time evaluation.

### Preprocessing leakage — present

`combined_df.fillna(combined_df.median())` calculates medians across all patients before the train/test split. Test-patient values affect training imputation statistics. Fit imputation/range-processing parameters on training patients only, then apply them unchanged to validation/test patients and online inference.

### Imputation leakage — present and temporal risk

Global median imputation has the split leakage described above. A future within-patient forward-fill must be strictly causal, bounded by an allowed gap, reset at patient boundaries, and must never backfill from a future measurement.

### Feature-engineering leakage — no engineered features today; high implementation risk

No rolling or trend features exist today. Future features must use trailing windows only, must never cross patient boundaries, and must ensure scaling/imputation is fitted using training data alone.

## 12. Backend prediction contract

```text
VitalSignalGenerator.get_vital_snapshot()
  -> {heart_rate, spo2, sys_bp, dia_bp, map, resp_rate, temp, condition}
  -> PatientAnomalyDetector.predict(vitals)
  -> {risk_score, risk_level, sepsis_probability, detected_flags, is_anomaly}
  -> FastAPI REST /api/patients, /api/patients/{bed_id}, /api/simulate
     and 1-Hz vitals messages on /ws/telemetry
  -> frontend receives each patient’s {vitals, analysis}
```

Field semantics today:

- `risk_score`: integer 0–100 from hand-written rules plus a limited probability contribution.
- `risk_level`: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`, derived from score thresholds 15/35/60.
- `sepsis_probability`: rounded Random Forest probability, or `0.0` on absent/failed model inference.
- `detected_flags`: rule-triggered flags, optionally including `PHYSIONET_SEPSIS_RISK_(n%)`.
- `is_anomaly`: `risk_score >= 35`; controls whether a simulated event is placed in alert history.

These fields are required compatibility fields for subsequent integration work.

## 13. Frontend dependencies

`frontend/app.js` reads `analysis.risk_score`, `analysis.risk_level`, and `analysis.detected_flags` for the patient card, risk colors, tab badges, multi-bed display, alarms, and alert list. It does not currently display `sepsis_probability`, but it must remain stable for API compatibility. The UI also expects vital keys in simulator naming (`heart_rate`, `spo2`, `sys_bp`, `dia_bp`, `map`, `resp_rate`, `temp`).

## 14. Simulator compatibility

`VitalSignalGenerator` creates noisy 1-Hz snapshots, 60-Hz synthetic ECG/PPG waveforms, and scenario values for Normal, Bradycardia, Tachycardia, Arrhythmia, Hypoxia, and Fever. It has no patient history buffer and no deterministic random seed. A temporal model will need a per-bed, causal rolling buffer, a cold-start policy, and the current snapshot schema must be preserved.

## 15. Recommended ML architecture

Build a versioned sklearn-style pipeline around patient IDs and `ICULOS`:

1. deterministic 70/15/15 patient split with a saved manifest;
2. training-only physiological validation, causal bounded forward-fill, and training-fitted imputer/scaler;
3. causal core, derived, and temporal features with explicit availability/cold-start indicators;
4. documented prospective target and lead-time evaluation;
5. NEWS2 baseline, Logistic Regression, and Random Forest before XGBoost;
6. threshold optimization on validation patients only;
7. held-out test once, followed by SHAP only for the selected tree model;
8. a model bundle including estimator, transformer, ordered feature schema, threshold, version, split ID, and metrics;
9. an adapter in `PatientAnomalyDetector` that preserves all existing response fields and clearly separates ML probability from rule-based alert context.

## 16. Risks and issues

1. **Critical:** current row-level splitting causes patient leakage.
2. **Critical:** global pre-split median imputation leaks held-out patient information.
3. **High:** persistent labels cannot substantiate a "within six hours" early-warning claim without onset-aware target construction and evaluation.
4. **High:** `model.py` suppresses every inference exception; a model/schema/version mismatch can silently report `0.0` probability.
5. **High:** the displayed risk score conflates learned probability and rules. It must be presented as an alert score, not an ML probability.
6. **Medium:** extremely sparse temperature/laboratory data and extreme numeric values need clinically reviewed, causal quality handling.
7. **Medium:** simulator inference is stateless, so temporal features will have cold-start and history-management requirements.
8. **Medium:** no reproducible model manifest, group split, validation set, or saved metrics currently exists.

## 17. Proposed implementation order

1. Implement and test deterministic patient-level train/validation/test splitting and a saved split manifest.
2. Implement training-only, causal preprocessing with explicit missingness and artifact policies.
3. Add and test causal derived/temporal features per patient.
4. Implement, document, and unit-test the onset-aware prospective target.
5. Establish NEWS2, Logistic Regression, and Random Forest baselines with validation-only threshold selection.
6. Evaluate XGBoost and add SHAP to its selected inference path.
7. Compare models honestly on untouched test patients; then consider LSTM only if it improves the validated result.
8. Integrate the selected model via a compatibility-preserving backend adapter and a simulator history buffer.

No final model training or integration should begin until the target convention and patient split are approved.

## Stage 2 — Leakage-Safe Pipeline

### Split strategy and reproducibility

Stage 2 adds `ml_pipeline/data_split.py`. It assigns **patients**, never individual rows, to a deterministic stratified split with seed `42`. Stratification is by whether a patient has any positive `SepsisLabel`; chronological row order within each PSV file is retained unchanged. Patient IDs include their source set (for example, `training_setA/p000009`) to remain globally unique.

The assignments and machine-readable report are stored in `ml_pipeline/data/splits/`:

- `train_patients.txt`
- `validation_patients.txt`
- `test_patients.txt`
- `split_summary.json`
- `positive_label_timeline_examples.json`
- `preprocessing_params.json`

The 70/15/15 patient counts are exact, with rare-event stratification resulting in 50/11/10 positive patients:

| Split | Patients | Rows | Positive patients | Negative patients | Positive rows | Negative rows | Positive rows % |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 700 | 27,522 | 50 | 650 | 473 | 27,049 | 1.718625% |
| Validation | 150 | 5,714 | 11 | 139 | 105 | 5,609 | 1.837592% |
| Test | 150 | 5,654 | 10 | 140 | 96 | 5,558 | 1.697913% |

`verify_zero_patient_overlap()` explicitly checks all three pairwise intersections and raises `ValueError` on any overlap. Re-running the split with the same seed gives the same assignments.

### Missingness by split

Missing values are the literal `NaN` values in the PSV files. No values were changed in Stage 2.

| Feature | All missing (count / %) | Train % | Validation % | Test % |
|---|---:|---:|---:|---:|
| HR | 3,861 / 9.93% | 10.010174% | 9.730487% | 9.727626% |
| O2Sat | 5,147 / 13.23% | 13.124046% | 13.353168% | 13.654050% |
| Temp | 25,701 / 66.09% | 66.096214% | 65.365768% | 66.766891% |
| SBP | 5,541 / 14.25% | 14.624664% | 12.793140% | 13.883976% |
| MAP | 4,779 / 12.29% | 12.473657% | 11.533077% | 12.150690% |
| DBP | 11,798 / 30.34% | 31.225928% | 22.051103% | 34.382738% |
| Resp | 6,276 / 16.14% | 16.303321% | 15.610781% | 15.864874% |

### Preprocessing and temporal safety

`ml_pipeline/preprocessing.py` provides `TrainingOnlyMedianImputer`. Its `fit()` phase calculates medians from train rows only; `transform()` requires an already-fitted instance and never recomputes statistics. Stage 2 fitted and saved these train-only medians: HR 84.5, O2Sat 98.0, Temp 37.0, SBP 122.0, MAP 81.0, DBP 63.0, Resp 18.0. The validation and test transform paths were executed without refitting, and raw PSV files were not rewritten.

No forward fill, backfill, interpolation, rolling statistic, temporal resampling, scaling, artifact deletion, or target transformation has been applied. This avoids using a future observation to represent an earlier prediction. Such operations remain Stage 3+ work and must be causal and fit on training patients only.

### Target-label observations

`positive_label_timeline_examples.json` records ten deterministic examples without modifying labels. For example, `training_setA/p000009` becomes positive at `ICULOS=249`, remains positive through record end at `ICULOS=258`, and has 10 positive readings; `training_setA/p000056` is already positive at its first available row (`ICULOS=1`) and remains so through `ICULOS=9`. These examples reinforce the Stage 1 observation that positive labels persist to record end. Stage 2 does **not** claim that the labels alone establish a future six-hour prediction target and does not change `SepsisLabel`.

### Tests

`ml_pipeline/tests/test_data_pipeline.py` covers zero overlap, same-seed reproducibility, preservation of fitted training statistics during validation transformation, transformation of unseen rows without refitting, and intact chronological `ICULOS` ordering. All five tests passed using the supplied dataset.

## Stage 4 — Feature Engineering

Stage 4 adds a 52-feature, model-free causal engineering layer using the fixed seed-42 patient splits. It writes train/validation/test CSV datasets in `ml_pipeline/data/processed/`, a feature schema, and per-feature split missingness statistics. The target follows the approved Stage 3 one-to-six-hour event window: 300/66/60 positives in train/validation/test; 173/39/36 inferred onset/post-onset rows are excluded, with no patient or positive target loss. All temporal features reset at patient boundaries and use only current/trailing observations. `SepsisLabel` is excluded from predictor features. See `docs/FEATURE_ENGINEERING.md` for the schema and verification details.
