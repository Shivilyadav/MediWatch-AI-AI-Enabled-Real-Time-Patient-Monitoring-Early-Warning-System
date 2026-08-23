# MediWatch AI — Phase 4 Model Comparison

All five candidate models on the full metric suite. **Thresholds are selected on the
validation split only** and then applied unchanged to the held-out test split, which was
evaluated **once**. The test split has **60 positives** — small differences between models
are within the noise floor and are **not** overinterpreted.

- Tabular models (LogReg, RF, XGBoost ×2) use the adopted **stage4-v2** 52-feature
  representation (`docs/FEATURE_DIAGNOSIS.md`).
- **LSTM** uses raw causal hourly sequences (`docs/` Phase 3; `ml_pipeline/lstm_experiment.py`).
- Source of record: `ml_pipeline/results/model_comparison.json`.
- Threshold policy (all models): maximize F1 among thresholds reaching ≥0.80 **validation**
  sensitivity.

## Validation metrics (primary selection basis)

| Model | AUROC | AUPRC | Sens | Spec | Prec | NPV | F1 | FPR | TN/FP/FN/TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Logistic Regression | 0.5871 | 0.0134 | 0.864 | 0.402 | 0.0167 | 0.9960 | 0.0328 | 0.598 | 2254/3355/9/57 |
| Random Forest | **0.6026** | **0.0167** | 0.848 | 0.280 | 0.0137 | 0.9937 | 0.0269 | 0.720 | 1572/4037/10/56 |
| XGBoost baseline | 0.5699 | 0.0139 | 0.803 | 0.388 | 0.0152 | 0.9941 | 0.0298 | 0.612 | 2175/3434/13/53 |
| XGBoost tuned | 0.5595 | 0.0134 | 0.803 | 0.334 | 0.0140 | 0.9931 | 0.0275 | 0.666 | 1874/3735/13/53 |
| LSTM | **0.7563** | **0.0477** | 0.909 | 0.388 | 0.0172 | 0.9973 | 0.0337 | 0.612 | 2177/3432/6/60 |

## Test metrics (held-out, evaluated once, validation thresholds)

| Model | AUROC | AUPRC | Sens | Spec | Prec | NPV | F1 | FPR | TN/FP/FN/TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Logistic Regression | **0.6475** | 0.0161 | 0.833 | **0.412** | 0.0151 | 0.9957 | 0.0296 | **0.588** | 2289/3269/10/50 |
| Random Forest | 0.6324 | **0.0171** | 0.833 | 0.263 | 0.0121 | 0.9932 | 0.0238 | 0.737 | 1464/4094/10/50 |
| XGBoost baseline | 0.6398 | 0.0159 | 0.817 | 0.328 | 0.0129 | 0.9940 | 0.0255 | 0.672 | 1822/3736/11/49 |
| XGBoost tuned | 0.6468 | 0.0161 | 0.867 | 0.279 | 0.0128 | 0.9949 | 0.0252 | 0.721 | 1550/4008/8/52 |
| LSTM | 0.5340 | 0.0121 | 0.700 | 0.404 | 0.0125 | 0.9921 | 0.0246 | 0.596 | 2247/3311/18/42 |

## Sensitivity / specificity trade-off

Every model was pushed to ≈0.80–0.91 sensitivity by the threshold policy. At that operating
point the false-positive rate is enormous for all of them (test FPR 0.59–0.74): to catch ~50
of 60 test positives, the best model still raises **>3,200** false alarms among 5,558
negatives (precision ≈1.5%). **No model separates the classes well enough to be clinically
useful.** The differences that do exist are on the false-alarm axis: at matched sensitivity,
**Logistic Regression gives the highest specificity / lowest FPR** (test 0.412 / 0.588),
**Random Forest the lowest specificity / highest FPR** (test 0.263 / 0.737).

## Robustness: validation → test stability

| Model | ΔAUROC (test−val) | ΔAUPRC (test−val) | Verdict |
|---|---:|---:|---|
| Logistic Regression | +0.060 | +0.003 | very stable (test ≥ val) |
| Random Forest | +0.030 | +0.000 | very stable, esp. AUPRC (0.0167→0.0171) |
| XGBoost baseline | +0.070 | +0.002 | stable |
| XGBoost tuned | +0.087 | +0.003 | stable |
| **LSTM** | **−0.222** | **−0.036** | **overfit — did not generalize** |

## Key finding: the LSTM overfit; the held-out test exposed it

The LSTM had by far the **best validation** metrics (AUROC 0.756, AUPRC 0.0477) — and by far
the **worst generalization**: on test its AUROC collapsed to **0.534** (near chance) and its
AUPRC to **0.0121** (below every tabular model). Selecting a model on validation alone would
have chosen the LSTM; the held-out test correctly rejected it.

Most likely causes (consistent with the design):

1. **Epoch selection on a noisy 66-positive validation AUPRC** — the per-epoch validation
   AUPRC swung between 0.017 and 0.048; picking the maximum is optimistically biased.
2. **Explicit missingness-mask channels** — the 20-channel input hands the LSTM the full
   measurement-cadence pattern. With only **300 training positives**, a hidden-32 LSTM has
   ample capacity to memorize validation-specific missingness structure that does not recur
   in the test patients. (This is a *generalization* failure from informative missingness,
   **not** future/onset leakage — sequences end strictly before the excluded onset window,
   forward-fill and standardization are causal and train-only.)

This is the textbook reason the test set is kept untouched and small validation differences
are not overinterpreted.

## Ranking

- **On validation (primary basis):** RF ≳ LogReg ≳ XGBoost variants; LSTM highest but
  **disqualified** by its test collapse. RF's validation AUROC/AUPRC edge over LogReg
  (+0.015 / +0.003) is within the 60–66-positive noise floor.
- **On robustness + the false-alarm axis + explainability + simplicity + threshold
  stability:** Logistic Regression is clearly best (highest specificity/lowest FPR at matched
  sensitivity, most stable, sane threshold 0.36 vs RF's fragile 0.0033, fully transparent,
  fastest at ~0.0008 ms/row).

Selection and rationale: `docs/FINAL_MODEL.md` (Phase 5/6).
