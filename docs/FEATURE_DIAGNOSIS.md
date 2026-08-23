# MediWatch AI — Phase 2 Feature Diagnosis (stage4-v1 → stage4-v2)

## Question

Does the 52-feature `stage4-v1` representation have a defensible ML weakness worth
fixing, and if so does a fix actually help on the **validation** split (test untouched)?

## Diagnosis (from SHAP + Stage 4 statistics)

1. **The dominant feature family is also the most-missing.** TreeSHAP attributes ~71% of
   the XGBoost model's importance to temporal features (see `docs/SHAP_ANALYSIS.md`), yet
   those features are heavily missing because `stage4-v1` requires **all four** of
   `[t-3..t]` to be present for any 4-hour rolling statistic (mean/std/min/max/trend).
   A single gap in the trailing window voids the whole statistic.
2. **Temperature temporal features are extremely sparse** (`temperature_mean_4h` ~89%
   missing in train) — yet `temperature_change_4h` is a top-5 feature. Signal exists but
   is being discarded by the completeness rule.
3. Changes (`change_1h`, `change_4h`) are exact-lag point differences; relaxing them would
   make their time-delta ambiguous, so they were **not** identified as the problem.
4. **No feature should be deleted for missingness** (per the task) — the fix is to
   *recover* signal, not remove features.

## Change: `stage4-v2` (one change only)

`ml_pipeline/feature_engineering_v2.py` reuses every `stage4-v1` definition and changes
**only** the rolling-window completeness rule:

> 4-hour rolling statistics are computed from the **present** values in `[t-3..t]` when at
> least **two** are present (`min_periods=2`). The trend slope uses the actual hour
> offsets of the present points, so units remain per-hour.

Unchanged: the 52-feature schema and order, core/derived values, MAP fallback, exact-lag
`change_1h`/`change_4h`, the approved 1–6h target and onset/post-onset exclusion, and the
immutable seed-42 splits. The change is **strictly causal** (trailing/current values only;
resets at patient boundaries; no future value/label). `stage4-v1` artifacts are preserved;
`stage4-v2` is written to `ml_pipeline/data/processed_v2/`.

### Coverage gain (train split, % missing)

| Feature | v1 | v2 |
|---|---:|---:|
| heart_rate_mean_4h | 26.49 | **8.57** |
| spo2_std_4h | 31.22 | **10.95** |
| spo2_max_4h | 31.22 | **10.95** |
| respiratory_rate_mean_4h | 35.81 | **13.53** |
| systolic_bp_max_4h | 32.16 | **12.25** |
| diastolic_bp_mean_4h | 44.35 | **29.86** |
| temperature_mean_4h | 89.03 | **77.03** |
| temperature_change_4h (exact-lag, unchanged) | 78.04 | 78.04 |

Row counts, positives, and the 39/173/36 onset exclusions are identical to v1 — only
feature *coverage* changed, not the target or the split.

## Validation evidence (threshold selected on validation only; test untouched)

| Model | v1 AUROC | v1 AUPRC | v1 Sens | v1 Spec | v2 AUROC | v2 AUPRC | v2 Sens | v2 Spec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.5669 | 0.0135 | 0.818 | 0.271 | **0.5871** | 0.0134 | 0.864 | **0.402** |
| Random Forest | 0.5902 | 0.0149 | 0.879 | 0.268 | **0.6026** | **0.0167** | 0.848 | 0.280 |
| XGBoost baseline | 0.5429 | 0.0130 | 0.803 | 0.281 | **0.5699** | **0.0139** | 0.803 | **0.388** |
| XGBoost tuned | 0.5676 | 0.0139 | 0.803 | 0.294 | 0.5595 | 0.0134 | 0.803 | 0.334 |

(Full numbers: `ml_pipeline/results/stage4v2_validation.json`.)

- Validation **AUROC** improves for 3 of 4 models (LogReg +0.020, RF +0.012, XGB baseline
  +0.027); XGBoost-tuned is ~flat (−0.008).
- Validation **specificity at matched high sensitivity** improves for most models — the
  false-alarm weakness the project cares about (LogReg 0.271→0.402; XGB baseline
  0.281→0.388; XGB tuned 0.294→0.334).
- Validation **AUPRC** improves for RF (best seen, 0.0167) and XGB baseline; flat elsewhere.

## Decision

**Adopt `stage4-v2` as the modeling representation for the remaining phases; preserve
`stage4-v1` unchanged for reproducibility.** The change is principled and causal, recovers
signal in the highest-importance (temporal) family, and modestly improves the
validation metrics that matter (specificity at matched sensitivity, AUROC, RF AUPRC)
without materially degrading any model.

**Honest caveat.** The gains are small and, with only 66 validation positives, within the
noise floor. `stage4-v2` is adopted on the combined weight of principle + coverage +
consistent (if modest) validation improvement — **not** because it reaches any target
metric. It does not, on its own, make any model deployment-ready.
