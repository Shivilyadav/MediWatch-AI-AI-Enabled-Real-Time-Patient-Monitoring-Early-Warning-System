# MediWatch AI — ML Project Context

## 1. Project

**Name:** MediWatch AI  
**Description:** AI-Enabled Real-Time Patient Monitoring & Early Warning System.

The system continuously monitors patient vital signs and provides an early-warning risk prediction for deterioration/sepsis. It is a clinical decision-support prototype, not an autonomous diagnostic system.

The project document describes an architecture using wearable/bedside vital data, preprocessing/artifact rejection, FastAPI, ML, SHAP explainability, alert prioritization, dashboard/mobile interfaces, FHIR integration, PostgreSQL and InfluxDB. The documented ML strategy is XGBoost as the primary tabular classifier, LSTM for temporal sequence modeling, Random Forest as a comparison/fallback, and NEWS2 as the rule-based benchmark.

## 2. User's role

The user is the **ML/AI Engineer**.

Their ML responsibilities are:
- model building
- training
- optimization
- explainability with SHAP
- model evaluation
- integration with the existing system

## 3. Existing repository / ML implementation

The current repository contains an ML pipeline roughly organized as:

```text
ml_pipeline/
├── model.py
├── train_physionet.py
├── signal_generator.py
├── download_physionet.py
├── model.pkl
└── data/
    └── raw/
        └── physionet/
```

The backend contains `backend/main.py`, and the frontend contains `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css`.

The existing backend uses `PatientAnomalyDetector` and expects the ML layer to provide a prediction compatible with the existing application.

The current prototype's learned model is a Random Forest.

The current Random Forest uses seven instantaneous features:

```text
HR
O2Sat
Temp
SBP
MAP
DBP
Resp
```

The existing detector also contains hand-written physiological anomaly/risk rules. These include checks for abnormal HR, oxygen saturation, blood pressure, respiratory rate and temperature. These rule-based checks may remain useful for safety/alert context, but they must not be presented as learned ML.

The existing prediction contract includes fields such as:

```text
risk_score
risk_level
sepsis_probability
detected_flags
is_anomaly
```

Do not break this contract unnecessarily.

## 4. Current major ML issue

The existing training approach performs a normal row-level train/test split after combining patient rows.

This creates a potential **patient leakage** problem because rows from the same patient can occur in both training and testing.

The new pipeline MUST split by patient.

Recommended project split:

```text
70% patients → train
15% patients → validation
15% patients → test
```

Use deterministic seeds and ensure no patient appears in multiple splits.

## 5. Dataset

The project uses the **PhysioNet 2019 Challenge** dataset.

The patient files are `.psv` time-series files.

Important fields include:

```text
HR
O2Sat
Temp
SBP
MAP
DBP
Resp
SepsisLabel
```

Patient identity and temporal ordering must be preserved.

Before changing target construction, inspect the actual data and determine the available columns, row counts, patient counts, missingness, and class distribution.

## 6. Clinical/project requirements

The project document identifies these clinical concepts as important:

- NEWS2 as the primary rule-based benchmark
- MEWS
- qSOFA
- SOFA

The project specifically requires the ML system to be compared with NEWS2.

The project documentation lists vital thresholds for clinical reference, but these should not automatically be treated as ML labels.

The documented deterioration scenarios include:
- sepsis onset
- respiratory failure
- cardiac arrest precursor
- hypovolemic shock
- fever progression

## 7. Planned feature engineering

The intended model should move beyond the current seven instantaneous vitals.

Core vitals:

```text
heart_rate
spo2
respiratory_rate
temperature
systolic_bp
diastolic_bp
```

Derived features should include, where valid:

```text
MAP
pulse_pressure
shock_index
SpO2/RR ratio
```

Temporal features should include historical changes/trends such as:

```text
{vital}_change_1h
{vital}_change_4h
rolling means
rolling standard deviations
rolling min/max
trend/slope
```

The project document describes approximately 34 features consisting of core vitals, derived vitals, trend features and context features.

The important modeling idea is that deterioration trends matter. A patient whose SpO2 is falling over time should not necessarily be treated the same as a patient with the same current SpO2 that has remained stable.

## 8. Preprocessing

The project documentation proposes:

- physiological artifact/range filtering
- spike detection
- rolling median smoothing
- missing-value handling
- temporal resampling to 5-minute intervals
- aggregation of multiple readings within an interval

However, do not delete genuinely abnormal physiological values merely because they are clinically abnormal. Distinguish obvious sensor artifacts from real deterioration.

Potential artifact ranges documented by the project include:

```text
HR: 20–250 bpm
SpO2: 50–100%
RR: 4–60/min
Temperature: 32–42°C
SBP: 50–260 mmHg
```

The project also mentions:
- sudden spikes >3 standard deviations as possible artifacts
- short missing gaps
- rolling median smoothing

These rules must be implemented carefully and must not introduce future-information leakage.

## 9. Target/label

The project roadmap proposes:

**Label = 1 if patient deteriorates within the next 6 hours.**

The project documentation describes deterioration in terms of events such as ICU transfer, cardiac arrest, or death for the general pipeline, while the actual PhysioNet data provides `SepsisLabel`.

Do NOT silently assume a target transformation.

First inspect the actual PhysioNet labels and explicitly determine how the prediction target should be generated.

For any prediction at time T, only information available at or before T may be used.

Never use future vitals, future rolling statistics, future imputation information, or future labels as input features.

## 10. Baseline and model progression

The intended progression is:

### Baseline
NEWS2 rule-based score.

### Classical ML
- Logistic Regression
- Random Forest

### Primary tabular model
- XGBoost

### Temporal deep-learning model
- LSTM

Do not assume XGBoost or LSTM will win. Select the final model based on actual validation/test evidence.

## 11. Class imbalance

The project expects deterioration/sepsis events to be relatively rare.

Potential approaches:
- class weights
- XGBoost `scale_pos_weight`
- validation-based threshold optimization

Do not blindly apply SMOTE to temporal medical data.

## 12. Evaluation

Report at least:

```text
AUROC
AUPRC
Sensitivity / Recall
Specificity
Precision / PPV
NPV
F1
False Positive Rate / False Alarm Rate
Confusion Matrix
Inference latency
```

Accuracy alone is not sufficient.

The project document gives target goals:

```text
AUROC > 0.85
Sensitivity > 88%
Specificity > 80%
False Alarm Rate < 20%
Lead Time > 4 hours
```

These are targets, NOT achieved results. Never fabricate or imply they were achieved without actual evaluation.

The project also wants lead-time evaluation: how early the model detects deterioration relative to the event.

## 13. XGBoost

XGBoost is the primary candidate for the tabular model.

Potential tuning parameters:

```text
n_estimators
max_depth
learning_rate
subsample
colsample_bytree
scale_pos_weight
```

Optuna may be used if useful.

Optimize the prediction threshold using validation data, not the final test set.

## 14. LSTM

After the tabular pipeline is stable, implement the temporal model.

The project document proposes:

```text
Input: last 12 readings × feature vector

LSTM 128 units
Dropout 0.3
LSTM 64 units
Dropout 0.3
Dense 32 ReLU
Output 1 Sigmoid
```

Sequences must never cross patient boundaries.

No future information may enter a sequence.

## 15. SHAP

SHAP is mandatory for the XGBoost prediction path.

Use:

```python
shap.TreeExplainer
```

Return the top contributing features for each prediction.

A target explanation format is:

```json
{
  "feature": "respiratory_rate_trend",
  "current_value": 24,
  "contribution": 0.32,
  "direction": "WORSENING"
}
```

Translate technical feature names into human-readable explanations.

SHAP explains model behavior; it does not establish clinical causation.

## 16. Real-time integration

The existing system must continue to support:

```python
PatientAnomalyDetector.predict(vitals)
```

The prediction response should remain compatible with the existing frontend.

It may be extended with:

```text
predicted_event
time_horizon
top_reasons
model_version
```

while retaining:

```text
risk_score
risk_level
sepsis_probability
detected_flags
is_anomaly
```

Keep these concepts separate:

```text
ML probability
risk score
NEWS2 score
alert priority
```

If the UI needs a 0–100 risk score:

```text
risk_score = probability * 100
```

Do not arbitrarily combine ML probability and rule-based scores without explicit justification.

## 17. Simulator

The existing project contains `ml_pipeline/signal_generator.py`.

Do not remove it.

The final ML system should work with the synthetic real-time patient simulator.

If an LSTM is used for inference, maintain a rolling historical buffer for each patient.

## 18. Performance

The project targets:

```text
ML inference <200 ms
end-to-end latency <500 ms
```

These are targets. Measure actual performance.

Models should be loaded once rather than retrained/reloaded for every prediction.

Training and inference preprocessing must use the same feature schema.

## 19. Development strategy

Do not implement the entire ML system in one uncontrolled change.

Proceed in stages:

### Stage 1 — Data audit
Determine:
- patient count
- row count
- available columns
- missingness
- class balance
- patient durations
- sepsis-positive patients/events

Do not train a final model yet.

### Stage 2 — Preprocessing
Implement and test:
- patient-safe split
- artifact handling
- missing-value handling
- resampling

### Stage 3 — Feature engineering
Implement and test:
- derived vitals
- temporal features
- trend features

Show the final feature list.

### Stage 4 — Target generation
Implement the future-deterioration target only after verifying the actual PhysioNet labels and avoiding leakage.

### Stage 5 — Baselines
Train/evaluate:
- NEWS2
- Logistic Regression
- Random Forest

### Stage 6 — XGBoost
Train, tune, optimize threshold and evaluate.

### Stage 7 — SHAP
Add explainability.

### Stage 8 — LSTM
Build temporal sequence model and compare.

### Stage 9 — Model selection
Compare all models and document the selection.

### Stage 10 — Backend integration
Update the ML layer while preserving existing application contracts.

## 20. First Codex task

The first task should be ONLY:

**Audit the existing dataset and ML pipeline.**

Do not immediately rewrite the project.

Inspect the repository and report:

1. current ML files
2. current model
3. current training flow
4. dataset location
5. number of patient files
6. number of rows
7. available columns
8. missing-value percentages
9. positive/negative label distribution
10. patient-level leakage risk
11. current inference contract
12. recommended next step

Then stop and wait for approval before making major ML changes.

## 21. General rules

- Inspect before editing.
- Preserve working functionality.
- Keep changes scoped.
- Run tests after meaningful changes.
- Never fabricate metrics.
- Never introduce patient or temporal leakage.
- Never claim clinical diagnosis.
- Do not over-engineer.
- Do not replace learned ML with arbitrary rules.
- Record model versions and experiment configurations.
- Prefer reproducible experiments.
