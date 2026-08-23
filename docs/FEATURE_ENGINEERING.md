# MediWatch AI — Stage 4 Feature Engineering

## Scope

Stage 4 converts the fixed Stage 2 patient splits into ML-ready, hourly CSV feature datasets. No model was trained and no backend, frontend, `model.py`, or `model.pkl` file was changed.

The processed datasets are CSV because this environment does not have a Parquet-capable data stack installed. The raw PSV files are never modified.

## Causal feature policy

Every output row at time `t` is constructed from the current row and earlier rows of the **same patient only**. Temporal histories reset for every PSV file. No forward fill, backfill, interpolation, future measurement, future label, or cross-patient history is used.

Missing history is represented as an empty CSV field. In particular:

- A 1-hour change requires both the current and exact preceding hourly value.
- A 4-hour change requires current and exact `t-4` values.
- Four-hour rolling statistics and slope require all current/trailing `t-3` through `t` values to be present.
- Missing observations are not invented or imputed during feature engineering; Stage 2's training-only imputer remains the downstream preprocessing mechanism.

## Feature set (52 predictor features)

### Core current values (7)

`heart_rate`, `spo2`, `respiratory_rate`, `temperature`, `systolic_bp`, `diastolic_bp`, `map`.

These preserve the raw clinical values using standardized names. `map` uses the recorded PhysioNet `MAP` when available; only when it is missing, it uses the current-row fallback `(SBP + 2*DBP) / 3`. There is no duplicate MAP predictor.

### Derived current values (3)

`pulse_pressure = systolic_bp - diastolic_bp`; `shock_index = heart_rate / systolic_bp` when SBP is positive; `spo2_rr_ratio = spo2 / respiratory_rate` when RR is positive. Invalid/missing denominators yield missing values rather than a fabricated value.

### Temporal values (42)

For each of `heart_rate`, `spo2`, `respiratory_rate`, `temperature`, `systolic_bp`, and `diastolic_bp`, the complete suffix set is:

`_change_1h`, `_change_4h`, `_mean_4h`, `_std_4h`, `_min_4h`, `_max_4h`, `_trend_4h`.

The rolling window is `[t-3, t]`, inclusive. Standard deviation is population standard deviation. Trend is a least-squares slope over those four equally spaced hourly values, in vital units per hour.

The complete machine-readable definition (source, calculation, units, history window, and missingness capability) is in `ml_pipeline/data/processed/feature_schema.json`.

## Target alignment

The output includes `patient_id`, `timestamp` (`ICULOS`), the 52 predictors, and `target`. `SepsisLabel` is not emitted as a predictor or output column.

For a positive record with first supplied positive row `f`, target construction follows the approved Stage 3 convention:

```text
onset_proxy = f + 6 hourly rows
target(t) = 1 when f <= t <= f + 5
target(t) = 0 before f
exclude t >= f + 6
```

All non-septic patient rows have target 0. The exclusion prevents current/onset/post-onset rows from being silently treated as negatives.

## Processed dataset statistics

| Split | Patients | Raw rows | Feature rows | Rows excluded | Positive | Negative | Patients lost | Positive targets lost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 700 | 27,522 | 27,349 | 173 | 300 | 27,049 | 0 | 0 |
| Validation | 150 | 5,714 | 5,675 | 39 | 66 | 5,609 | 0 | 0 |
| Test | 150 | 5,654 | 5,618 | 36 | 60 | 5,558 | 0 | 0 |

The 248 excluded rows are exactly inferred onset/post-onset rows required by the approved target definition (173 train, 39 validation, 36 test). No row was removed for missing vital data, no patient was lost, and no positive target sample was lost.

## Missingness

All per-feature counts and percentages for each split are recorded in `ml_pipeline/data/processed/feature_statistics.json`. Missingness increases for temporal features because history is intentionally unavailable at early rows and whenever a required observation is missing.

Selected training missingness illustrates the expected pattern:

| Feature | Missing % |
|---|---:|
| heart_rate | 10.03% |
| map | 11.85% |
| spo2 | 13.16% |
| respiratory_rate | 16.31% |
| temperature | 66.08% |
| heart_rate_change_1h | 16.92% |
| heart_rate_mean_4h | 26.49% |
| temperature_change_1h | 86.10% |
| temperature_mean_4h | 89.03% |
| diastolic_bp_mean_4h | 44.35% |

## Generated artifacts

- `ml_pipeline/data/processed/train_features.csv`
- `ml_pipeline/data/processed/validation_features.csv`
- `ml_pipeline/data/processed/test_features.csv`
- `ml_pipeline/data/processed/feature_schema.json`
- `ml_pipeline/data/processed/feature_statistics.json`
- `ml_pipeline/feature_engineering.py`

## Verification

`ml_pipeline/tests/test_feature_engineering.py` passed seven checks:

1. patient-boundary reset;
2. a future value cannot change an earlier row's engineered features;
3. manual 1-hour change;
4. manual 4-hour change and rolling statistics;
5. derived vitals and MAP fallback;
6. approved target alignment and post-onset exclusion;
7. absence of `SepsisLabel` and `target` from the predictor schema.

No temporal leakage was found in the implemented feature calculations.
