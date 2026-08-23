# MediWatch AI — Phase 1 SHAP Analysis (XGBoost, validation)

## Method

- **Explainer:** XGBoost built-in **TreeSHAP** via `booster.predict(dmatrix, pred_contribs=True)`.
  This is the exact TreeSHAP algorithm (Lundberg et al., 2020) that `shap.TreeExplainer`
  wraps for gradient-boosted trees; it returns identical values.
- **Why not the `shap` package:** installing `shap` pulls `numba`/`llvmlite`, which would
  likely force a downgrade of the working `numpy 2.3.5 / scikit-learn 1.9.0 / xgboost 3.4.1`
  stack that produced the Stage 5 results. The native path avoids that risk entirely.
- **Space:** contributions are in **margin (log-odds)** units. Positive SHAP → pushes the
  prediction toward the positive (deterioration-within-1–6h) class.
- **Data:** **validation split only** (5,675 rows, 66 positives). The test set is never
  loaded for this analysis (Phase 1 constraint).
- **Models analyzed:** `xgboost_tuned` (primary) and `xgboost_baseline` (robustness check).
- **Reproducibility:** `ml_pipeline/shap_analysis.py` → `ml_pipeline/results/shap_summary.json`.

`value_shap_corr` is the Pearson correlation between a feature's value and its SHAP
contribution across rows where the feature is present. It is a **crude linear summary** of
a nonlinear model — useful for the dominant direction, not a claim of linearity.

> **Interpretation caveat.** The Stage 5 XGBoost models are weak (validation AUROC ≈ 0.54–0.57,
> AUPRC ≈ 0.013–0.014). SHAP explains *what this weak model keys on*; it does **not**
> establish validated clinical drivers or causation.

## Global feature importance (XGBoost tuned, validation)

Importance = mean(|SHAP|) over validation rows, expressed as a share of total.

**By feature type:**

| Type | Importance share |
|---|---:|
| Temporal (42 features) | **71.5%** |
| Core current vitals (7) | 21.7% |
| Derived (3) | 6.7% |

**By base vital:**

| Vital | Share | | Vital | Share |
|---|---:|---|---|---:|
| heart_rate | 26.3% | | respiratory_rate | 10.6% |
| systolic_bp | 16.4% | | map | 4.2% |
| spo2 | 14.0% | | shock_index | 2.2% |
| diastolic_bp | 13.6% | | pulse_pressure | 2.1% |
| temperature | 10.7% | | | |

The temporal engineering layer carries ~71% of the model's signal — the Stage 4 features
are being used, not ignored. Importance is spread across all vitals rather than dominated
by any single one.

## Top 15 features (XGBoost tuned)

| Rank | Feature | Type | Share | value↔SHAP corr | Direction | Val miss % | % importance from missing rows |
|---:|---|---|---:|---:|---|---:|---:|
| 1 | heart_rate | core | 10.1% | +0.87 | ↑ value → ↑ risk | 9.8 | 2% |
| 2 | heart_rate_mean_4h | temporal | 5.9% | +0.65 | ↑ → ↑ risk | 26.7 | 10% |
| 3 | systolic_bp_max_4h | temporal | 5.0% | +0.71 | ↑ → ↑ risk ⚠ | 30.7 | 6% |
| 4 | map | core | 4.2% | −0.79 | ↑ → ↓ risk | 11.1 | 5% |
| 5 | temperature_change_4h | temporal | 4.1% | +0.66 | ↑ → ↑ risk | 77.4 | 34% |
| 6 | diastolic_bp_min_4h | temporal | 3.5% | +0.33 | ↑ → ↑ risk | 37.8 | 31% |
| 7 | heart_rate_max_4h | temporal | 3.4% | +0.51 | ↑ → ↑ risk | 26.7 | 1% |
| 8 | respiratory_rate_max_4h | temporal | 3.1% | +0.63 | ↑ → ↑ risk | 36.6 | 10% |
| 9 | heart_rate_min_4h | temporal | 3.0% | +0.36 | ↑ → ↑ risk | 26.7 | 7% |
| 10 | systolic_bp_min_4h | temporal | 2.9% | +0.28 | ↑ → ↑ risk | 30.7 | 4% |
| 11 | spo2_std_4h | temporal | 2.9% | +0.32 | ↑ → ↑ risk | 32.2 | 32% |
| 12 | diastolic_bp_max_4h | temporal | 2.7% | −0.55 | ↑ → ↓ risk | 37.8 | 31% |
| 13 | systolic_bp_change_4h | temporal | 2.7% | −0.66 | falling SBP → ↑ risk | 26.8 | 26% |
| 14 | spo2_max_4h | temporal | 2.7% | +0.63 | ↑ → ↑ risk ⚠ | 32.2 | 32% |
| 15 | respiratory_rate_std_4h | temporal | 2.5% | −0.22 | mixed | 36.6 | 6% |

## Feature impact direction — clinical plausibility

**Physiologically coherent signals (reassuring):**

- **Tachycardia:** high `heart_rate` and its 4-hour mean/max raise risk (corr +0.87 / +0.65 / +0.51).
- **Hypotension:** high `map` **lowers** risk (−0.79); falling systolic BP (`systolic_bp_change_4h` −0.66) raises risk. Low perfusion → higher risk is the expected sepsis/deterioration pattern.
- **Fever progression:** rising `temperature_change_4h` raises risk (+0.66).
- **Tachypnea:** high `respiratory_rate_max_4h` raises risk (+0.63).
- **Instability:** higher `spo2_std_4h` (SpO₂ variability) raises risk (+0.32).

These match how a clinician reads deterioration and are the main reason to treat the model
as learning *some* real signal despite weak overall discrimination.

## Suspicious / counterintuitive features

- ⚠ **`systolic_bp_max_4h` (+0.71) and `spo2_max_4h` (+0.63):** higher values raising risk is
  counterintuitive (one expects *low* SBP and *low* SpO₂ to signal deterioration). Plausible
  explanations, none verified: (a) linear corr misrepresents a nonlinear/interaction effect;
  (b) collinearity among the six BP/SpO₂ temporal features splits credit oddly; (c)
  **supplemental-oxygen confounding** — sicker patients on O₂ can show high SpO₂; the dataset
  has no supplemental-O₂ flag; (d) small-positive-count noise (66 validation positives). These
  should be probed with partial-dependence, **not** hand-edited.
- **Missingness-as-signal in sparse temporal features:** `temperature_change_4h` (34%),
  `spo2_std_4h`/`spo2_max_4h` (32%), `diastolic_bp_min_4h`/`diastolic_bp_max_4h` (31%),
  `systolic_bp_change_4h` (26%) each draw a substantial minority of their importance from rows
  where the value is **missing** (XGBoost routes NaN to a learned default branch). Individually
  small, but collectively it means the model partly keys on *"recent history unavailable"* for
  sparse vitals — informative in-dataset (measurement cadence tracks acuity), but a fragile
  signal to rely on operationally.

## Is missingness dominating the model?

**No, not overall.** With a strict test (≥50% of a feature's importance from missing rows
**and** ≥40% missing), only **one** feature qualifies — `temperature_change_1h` (85% missing) —
and its importance share is negligible (**0.2%**). The dominant contributors (HR, MAP, HR
mean/max, SBP trends, RR max) derive their importance from **present, measured values**. So
missingness is a secondary, localized effect concentrated in the sparsest temporal features,
not a global crutch.

## Robustness (tuned vs baseline)

The `xgboost_baseline` and `xgboost_tuned` explanations agree closely: **13/15** top features
overlap; type split (temporal ~71.5%, core ~21%, derived ~7%) and per-vital ranking are nearly
identical; shared top features have the same directions. The two differ only in the tail
(`shock_index`/`spo2_rr_ratio` vs `spo2_max_4h`/`diastolic_bp_min_4h`). Conclusion: the
importance structure is stable, not an artifact of one configuration.

## Feature-engineering weaknesses (input to Phase 2)

1. **The most important feature family is also the most missing.** Temporal features carry
   ~71% of importance yet are heavily missing because 4-hour rolling stats require **all four**
   of `[t-3..t]` present and changes require the **exact** lag present. Much usable trailing
   signal is discarded by this all-or-nothing completeness rule.
2. **Temperature temporal features are extremely sparse:** `temperature` 66% missing at the
   core; `temperature_change_1h` ~85%, `temperature_change_4h` ~77%, `temperature_mean_4h` ~89%
   missing (Stage 4 stats). Yet `temperature_change_4h` is a top-5 feature — signal exists but
   is thin and partly driven by the missing branch.
3. **Derived features contribute little** (6.7%); `shock_index` is modest, `pulse_pressure`
   and `spo2_rr_ratio` marginal. Not harmful; low yield.

## Recommendations

1. **(Phase 2 candidate — `stage4-v2`)** Relax rolling-window completeness from *4-of-4* to
   **≥2-of-4 present** (`min_periods=2`), still strictly causal/trailing. This should
   substantially raise coverage of the high-importance temporal features (especially
   temperature and diastolic BP) without introducing future information. **Validate on the
   validation split only**; keep `stage4-v1` intact for reproducibility.
2. Consider a **longer window (e.g., 8h)** for the sparsest vital (temperature) — but only
   adopt if it improves validation metrics.
3. **Probe the counterintuitive `*_max_4h` signs** with partial-dependence before trusting
   them; do not manually override the model.
4. Keep derived features (cheap) but do not expand them further given low yield.
5. Treat all SHAP directions as **model behavior on a weak model**, not clinical evidence.

Machine-readable detail (all 52 features, both models): `ml_pipeline/results/shap_summary.json`.
