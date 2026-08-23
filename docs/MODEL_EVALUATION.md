# MediWatch AI — Stage 5 Model Evaluation

## Scope and non-goals

This document reports the measured results of `ml_pipeline/train_stage5.py`, run once
against the fixed Stage 2/Stage 4 artifacts. The run trains and evaluates five models
(NEWS2 adapted rule benchmark, Logistic Regression, Random Forest, XGBoost baseline,
XGBoost tuned) and writes the machine-readable metrics to
`ml_pipeline/results/model_metrics.json`. That JSON is the source of truth; every number
below is copied from it without rounding beyond the six decimals the script already
recorded.

**Stage naming.** `AGENTS.md` §19 lists baselines (NEWS2 / Logistic Regression /
Random Forest) as *Stage 5* and XGBoost as *Stage 6*. The single script
`train_stage5.py` covers both; this evaluation therefore spans what the roadmap splits
into Stage 5 and Stage 6.

**This evaluation does NOT:**

- modify `ml_pipeline/model.pkl`, the backend, or the frontend (untouched);
- implement SHAP or LSTM (roadmap Stage 7/8, not started);
- select a final production model (roadmap Stage 9);
- constitute clinical validation. The 1–6 hour horizon is a **PhysioNet 2019 Challenge
  early-warning benchmark target**, evaluated on held-out PhysioNet patients — it is not
  independent prospective clinical validation, and none of these results should be
  presented as clinical performance.

## Reproducibility

| Item | Value |
|---|---|
| Runner | `ml_pipeline/train_stage5.py` (run unmodified) |
| Dataset / feature version | `stage4-v1` (PhysioNet 2019 Challenge, sets A+B, 1,000 patients) |
| Feature inputs | `ml_pipeline/data/processed/{train,validation,test}_features.csv` |
| Split artifacts | `ml_pipeline/data/splits/{train,validation,test}_patients.txt`, seed 42 |
| Predictor count | 52 (`stage4-v1`), forbidden columns excluded (`patient_id`, `timestamp`, `target`, `SepsisLabel`) |
| Training seed | 42 |
| Outputs | `ml_pipeline/results/model_metrics.json`, `ml_pipeline/saved_models/*_stage5.joblib` |

**Environment used for this run.** Python 3.12.13 with `numpy 2.3.5`, `scipy 1.18.1`,
`joblib 1.5.3`, `threadpoolctl 3.6.0`, `scikit-learn 1.9.0`, `xgboost 3.4.1`.

> Note: a pre-existing `ml_pipeline/.stage5_packages` vendored-package directory was
> found corrupted (empty namespace shadows for `scipy`/`joblib`, missing
> `scikit-learn`/`xgboost`) and could not be repaired in place due to OneDrive file
> locks. It was renamed to `ml_pipeline/_stage5_packages_disabled` so the script's
> `LOCAL_PACKAGES.exists()` prepend is bypassed, and a self-consistent stack was
> installed into the interpreter's own site-packages. No pipeline source was changed.

## Data provenance and split

Patient-level 70/15/15 split, stratified by ever-positive `SepsisLabel`, seed 42, with
zero patient overlap across splits (re-verified at run start by
`validate_inputs()`). Row and positive-target counts were asserted before training:

| Split | Rows | Positive target rows | Negative target rows | Positive rate |
|---|---:|---:|---:|---:|
| Train | 27,349 | 300 | 27,049 | 1.097% |
| Validation | 5,675 | 66 | 5,609 | 1.163% |
| Test | 5,618 | 60 | 5,558 | 1.068% |

Train negative:positive ratio = **90.163333** (used as XGBoost `scale_pos_weight`).

## Target definition

Prospective 1–6 hour future-event target (approved Stage 3/4 convention). For a positive
patient with first supplied positive row `f`: onset proxy `τ = f + 6`; `target = 1` for
rows `f … f+5`, `target = 0` before `f`, and rows `≥ f+6` are **excluded** (not treated
as negatives). All rows of never-positive patients are `target = 0`. Features are strictly
causal (current + trailing only), reset at patient boundaries; `SepsisLabel` is never a
predictor. See `docs/FEATURE_ENGINEERING.md`.

## Threshold-selection protocol

Thresholds were chosen on **validation probabilities only** (`choose_threshold()`):
among all candidate thresholds reaching **≥ 0.80 validation sensitivity**, the one
maximizing validation F1 (tie-broken by sensitivity, then specificity) is selected. The
test set is used exactly once, for final metrics, and never influences threshold choice.
This is confirmed empirically: validation sensitivities sit at ≈0.80–0.88 (the
constraint boundary) while test sensitivities differ (0.85–0.92).

## Model configurations

| Model | Key configuration |
|---|---|
| NEWS2 (adapted) | Rule benchmark. Available components: RR, SpO₂ (scale 1), temperature, systolic BP, HR. **Unavailable: supplemental oxygen, consciousness/new confusion.** Missing components score 0 points. |
| Logistic Regression | `class_weight=balanced`, `max_iter=2000`; median imputer + standard scaler, both fit on train only. |
| Random Forest | `n_estimators=300`, `max_depth=None`, `min_samples_leaf=1`, `class_weight=balanced_subsample`; median imputer fit on train. |
| XGBoost baseline | `n_estimators=200`, `max_depth=4`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8`, `scale_pos_weight=90.163333`, `eval_metric=aucpr`, `tree_method=hist`. |
| XGBoost tuned | Best of 3 additional candidates by validation (AUPRC, then AUROC, then F1): `n_estimators=300`, `max_depth=3`, `learning_rate=0.05`, `subsample=0.9`, `colsample_bytree=0.8`, `scale_pos_weight=90.163333`. |

Selected thresholds: NEWS2 `0.0`; Logistic Regression `0.292847`; Random Forest
`0.003333`; XGBoost baseline `0.056777`; XGBoost tuned `0.075152`.

## Validation metrics (threshold-selection set)

| Model | AUROC | AUPRC | Sensitivity | Specificity | Precision | NPV | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NEWS2 (adapted) | 0.599602 | 0.016936 | 1.000000 | 0.000000 | 0.011630 | 0.000000 | 0.022993 | 1.000000 |
| Logistic Regression | 0.566878 | 0.013544 | 0.818182 | 0.271350 | 0.013040 | 0.992177 | 0.025671 | 0.728650 |
| Random Forest | 0.590170 | 0.014898 | 0.878788 | 0.267962 | 0.013929 | 0.994705 | 0.027423 | 0.732038 |
| XGBoost baseline | 0.542903 | 0.012975 | 0.803030 | 0.281334 | 0.012977 | 0.991829 | 0.025542 | 0.718666 |
| XGBoost tuned | 0.567577 | 0.013878 | 0.803030 | 0.294170 | 0.013210 | 0.992183 | 0.025993 | 0.705830 |

Validation AUPRC random baseline (prevalence) ≈ 0.01163.

## Test metrics (held out; evaluated once)

| Model | AUROC | AUPRC | Sensitivity | Specificity | Precision/PPV | NPV | F1 | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NEWS2 (adapted) | 0.523327 | 0.012792 | 1.000000 | 0.000000 | 0.010680 | 0.000000 | 0.021134 | 1.000000 |
| Logistic Regression | 0.626189 | 0.036939 | 0.850000 | 0.252969 | 0.012134 | 0.993640 | 0.023927 | 0.747031 |
| Random Forest | 0.607251 | 0.013780 | 0.866667 | 0.248291 | 0.012293 | 0.994236 | 0.024242 | 0.751709 |
| XGBoost baseline | 0.614785 | 0.015732 | 0.916667 | 0.211587 | 0.012396 | 0.995766 | 0.024461 | 0.788413 |
| XGBoost tuned | 0.637588 | 0.018500 | 0.916667 | 0.228140 | 0.012658 | 0.996072 | 0.024972 | 0.771860 |

Test AUPRC random baseline (prevalence) ≈ 0.01068. Wilson 95% CIs for sensitivity and
specificity are recorded per model in `model_metrics.json`.

## Test confusion matrices, training time, and latency

Test set: **60 positive** rows, **5,558 negative** rows.

| Model | TP | FN | TN | FP | Training (s) | Inference (ms/row) |
|---|---:|---:|---:|---:|---:|---:|
| NEWS2 (adapted) | 60 | 0 | 0 | 5,558 | n/a (rule) | 0.000078 |
| Logistic Regression | 51 | 9 | 1,406 | 4,152 | 0.350783 | 0.000804 |
| Random Forest | 52 | 8 | 1,380 | 4,178 | 2.144654 | 0.011107 |
| XGBoost baseline | 55 | 5 | 1,176 | 4,382 | 0.725778 | 0.001088 |
| XGBoost tuned | 55 | 5 | 1,268 | 4,290 | 0.573458 | 0.001605 |

All inference latencies are far below the 200 ms/prediction target (ML_PROJECT_CONTEXT.md
§18). Latency is per-row batch-amortized `predict_proba`, best of 5 repeats.

## Which model performed best

No model reaches clinically useful or target-level performance, and the ranking is
**not stable** between validation and test (expected with only 60–66 positive rows):

- **Test AUROC** is highest for **XGBoost tuned (0.637588)**, then Logistic Regression,
  XGBoost baseline, Random Forest, NEWS2.
- **Test AUPRC** is highest for **Logistic Regression (0.036939, ≈3.5× the 0.0107
  base rate)**, then XGBoost tuned (0.018500, ≈1.7×), baseline, Random Forest, NEWS2.
- On **validation** (the proper selection basis, since test must not drive selection),
  Random Forest is marginally best among learned models on both AUROC (0.590170) and
  AUPRC (0.014898), but the gaps are within sampling noise.

Because rankings disagree across metrics and splits, and all models are far below target,
**Stage 5 does not justify selecting a final model.** That decision belongs to roadmap
Stage 9, after XGBoost explainability (SHAP) and the LSTM comparison, and should weigh
AUPRC and a calibrated operating point — ideally with more positive cases.

## Did tuning improve XGBoost?

Marginally, and consistently on both splits:

| | Validation AUROC | Validation AUPRC | Test AUROC | Test AUPRC |
|---|---:|---:|---:|---:|
| XGBoost baseline | 0.542903 | 0.012975 | 0.614785 | 0.015732 |
| XGBoost tuned | 0.567577 | 0.013878 | 0.637588 | 0.018500 |

Tuned is better on the validation criteria used to select it and remained better on the
untouched test set, but both remain weak in absolute terms.

## Target assessment

Targets are from ML_PROJECT_CONTEXT.md §12 and are **goals, not commitments**; they were
**not** achieved except as noted.

| Target | Threshold | Best measured (test) | Met? |
|---|---|---|---|
| AUROC > 0.85 | 0.85 | 0.637588 (XGBoost tuned) | ❌ No |
| Sensitivity > 88% | 0.88 | 0.916667 (XGBoost baseline & tuned) | ⚠️ Met **only** at a high-sensitivity operating point that sacrifices specificity |
| Specificity > 80% | 0.80 | 0.252969 (Logistic Regression) | ❌ No |
| False-alarm rate < 20% | 0.20 | 0.747031 (Logistic Regression) | ❌ No |
| Lead time > 4 h | 4 h | not evaluated by this script | ➖ Not assessed |

The sensitivity target is met by the two XGBoost models only because thresholds were
deliberately tuned to the ≥0.80-sensitivity region; at that operating point specificity
collapses (FPR ≈ 0.77–0.79). This is a high-recall / very-low-precision regime, not a
model that meets the combined target profile.

## Limitations and honest caveats

1. **Weak absolute performance.** AUROC 0.52–0.64 and AUPRC 0.013–0.037 on test. These
   are near chance for AUROC and only ≈1.2–3.5× the base rate for AUPRC. This is an
   honest result on a genuinely hard, severely imbalanced rare-event task — **not** a
   sign of leakage (leakage would inflate, not depress, these numbers).
2. **Very few positives.** 71 ever-positive patients total; 60 positive rows in test,
   66 in validation. Metric estimates are noisy (see Wilson CIs) and model ranking is
   unstable across splits.
3. **NEWS2 is degenerate here.** Its selected threshold is 0.0 (flags every row →
   sensitivity 1.0, specificity 0.0, FPR 1.0). This is an artifact of the adaptation
   (no supplemental-oxygen or consciousness components; many missing vital components
   scored 0), not a leakage or coding error. As a pure ranker its test AUROC is only
   0.523. It is a weak, adapted benchmark and should be read as such.
4. **No labs, no oxygen/mental-status inputs.** Features are causal vitals and their
   derived/temporal transforms only; PhysioNet labs (largely missing) and NEWS2's
   oxygen/consciousness components are absent.
5. **Not clinical validation.** The 1–6 hour horizon is a PhysioNet benchmark target on
   held-out challenge patients. No prospective, site-level, or clinical validation has
   been performed. No clinical or diagnostic claim is made or supported.
6. **Threshold policy is a design choice.** Fixing ≥0.80 validation sensitivity forces a
   high-recall/low-precision operating point; a different clinical trade-off would move
   every operating-point metric.

## Artifacts produced by this run

- `ml_pipeline/results/model_metrics.json` — full per-model validation + test metrics,
  thresholds, configs, confusion matrices, Wilson CIs, latencies (source of truth).
- `ml_pipeline/saved_models/logistic_regression_stage5.joblib`
- `ml_pipeline/saved_models/random_forest_stage5.joblib`
- `ml_pipeline/saved_models/xgboost_baseline_stage5.joblib`
- `ml_pipeline/saved_models/xgboost_tuned_stage5.joblib`

Each `.joblib` bundle is `{"model", "features" (52), "threshold", "feature_version":
"stage4-v1"}`. NEWS2 is a rule benchmark and is not serialized.
