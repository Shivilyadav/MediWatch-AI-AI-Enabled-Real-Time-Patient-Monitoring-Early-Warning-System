"""Phase 1 SHAP analysis of the trained Stage 5 XGBoost models (validation only).

This uses XGBoost's built-in TreeSHAP (`booster.predict(..., pred_contribs=True)`),
which is the exact TreeSHAP algorithm (Lundberg et al., 2020) that
`shap.TreeExplainer` wraps for gradient-boosted trees. We use the native path on
purpose: installing the `shap` package pulls `numba`/`llvmlite`, which would likely
force a downgrade of the working numpy 2.3.5 / scikit-learn 1.9.0 / xgboost 3.4.1
stack that produced the Stage 5 results. The native path gives identical values with
zero new dependencies.

Contributions are returned in margin (log-odds) space. The final column of the
`pred_contribs` matrix is the per-row base value; the remaining 52 columns are the
per-feature SHAP contributions.

Read-only with respect to datasets and saved models. Writes a machine-readable
summary to `ml_pipeline/results/shap_summary.json`. VALIDATION data only — the test
set is never loaded here (Phase 1 constraint).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
import xgboost as xgb

PIPELINE_ROOT = Path(__file__).resolve().parent
PROCESSED = PIPELINE_ROOT / "data" / "processed"
MODELS = PIPELINE_ROOT / "saved_models"
RESULTS = PIPELINE_ROOT / "results"
FORBIDDEN = {"patient_id", "timestamp", "target"}


def read_dataset(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        header = reader.fieldnames
    predictors = [c for c in header if c not in FORBIDDEN]
    X = np.array(
        [[float(r[c]) if r[c] != "" else np.nan for c in predictors] for r in rows],
        dtype=float,
    )
    y = np.array([int(r["target"]) for r in rows], dtype=int)
    return predictors, X, y


def load_schema_meta():
    schema = json.loads((PROCESSED / "feature_schema.json").read_text(encoding="utf-8"))
    ftype = {f["name"]: f["type"] for f in schema["features"]}
    fsource = {f["name"]: f.get("source", "") for f in schema["features"]}
    return ftype, fsource


def safe_corr(a: np.ndarray, b: np.ndarray):
    if len(a) < 10:
        return None
    sa, sb = np.std(a), np.std(b)
    if sa == 0 or sb == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def base_vital(name: str) -> str:
    for vital in ("heart_rate", "spo2", "respiratory_rate", "temperature", "systolic_bp", "diastolic_bp"):
        if name == vital or name.startswith(vital + "_"):
            return vital
    if name == "map":
        return "map"
    if name in ("pulse_pressure", "shock_index", "spo2_rr_ratio"):
        return name
    return "other"


def analyze_model(name: str, predictors, X, y, ftype, val_missing):
    bundle = joblib.load(MODELS / f"{name}_stage5.joblib")
    model = bundle["model"]
    feats = bundle["features"]
    assert feats == predictors, f"feature order mismatch for {name}"
    booster = model.get_booster()
    # No feature_names on the DMatrix: the model was trained on a bare numpy array,
    # so the booster expects f0..f51. Column order already matches `predictors`.
    dmatrix = xgb.DMatrix(X, missing=np.nan)
    contribs = booster.predict(dmatrix, pred_contribs=True)
    shap_vals = contribs[:, :-1]
    base_value = float(np.mean(contribs[:, -1]))

    mean_abs = np.abs(shap_vals).mean(axis=0)
    total_abs = float(mean_abs.sum())

    per_feature = []
    for j, fname in enumerate(predictors):
        col = X[:, j]
        present = ~np.isnan(col)
        n_present = int(present.sum())
        n_missing = int((~present).sum())
        sh = shap_vals[:, j]
        abs_sh = np.abs(sh)
        total_col_abs = float(abs_sh.sum())
        corr = safe_corr(col[present], sh[present]) if n_present else None
        mean_sh_present = float(sh[present].mean()) if n_present else None
        mean_sh_missing = float(sh[~present].mean()) if n_missing else None
        frac_from_missing = float(abs_sh[~present].sum() / total_col_abs) if total_col_abs > 0 else 0.0
        per_feature.append({
            "feature": fname,
            "type": ftype.get(fname, "?"),
            "base_vital": base_vital(fname),
            "mean_abs_shap": round(float(mean_abs[j]), 6),
            "importance_share": round(float(mean_abs[j] / total_abs), 6) if total_abs else 0.0,
            "value_shap_corr": round(corr, 4) if corr is not None else None,
            "direction": ("higher_value_raises_risk" if (corr or 0) > 0.05
                          else "higher_value_lowers_risk" if (corr or 0) < -0.05
                          else "weak_or_mixed"),
            "mean_shap_present": round(mean_sh_present, 6) if mean_sh_present is not None else None,
            "mean_shap_missing": round(mean_sh_missing, 6) if mean_sh_missing is not None else None,
            "val_missing_pct": round(val_missing.get(fname, 0.0), 3),
            "frac_importance_from_missing_rows": round(frac_from_missing, 4),
        })
    per_feature.sort(key=lambda d: d["mean_abs_shap"], reverse=True)

    # Aggregate by feature type and by base vital
    by_type = {}
    by_vital = {}
    for rec in per_feature:
        by_type[rec["type"]] = by_type.get(rec["type"], 0.0) + rec["mean_abs_shap"]
        by_vital[rec["base_vital"]] = by_vital.get(rec["base_vital"], 0.0) + rec["mean_abs_shap"]
    by_type = {k: round(v / total_abs, 4) for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])}
    by_vital = {k: round(v / total_abs, 4) for k, v in sorted(by_vital.items(), key=lambda kv: -kv[1])}

    # Temperature temporal features specifically
    temp_temporal = [r for r in per_feature if r["base_vital"] == "temperature" and r["type"] == "temporal"]
    temp_temporal_share = round(sum(r["importance_share"] for r in temp_temporal), 4)

    # Missingness-dominated features: importance mostly from the NaN branch AND sparse
    missingness_dominated = [
        r for r in per_feature
        if r["frac_importance_from_missing_rows"] >= 0.5 and r["val_missing_pct"] >= 40.0
    ]

    return {
        "base_value_logodds": round(base_value, 6),
        "total_mean_abs_shap": round(total_abs, 6),
        "importance_by_type": by_type,
        "importance_by_base_vital": by_vital,
        "temperature_temporal_importance_share": temp_temporal_share,
        "top_features": per_feature[:15],
        "missingness_dominated_features": [
            {"feature": r["feature"], "val_missing_pct": r["val_missing_pct"],
             "frac_importance_from_missing_rows": r["frac_importance_from_missing_rows"],
             "importance_share": r["importance_share"]}
            for r in missingness_dominated
        ],
        "all_features_ranked": per_feature,
    }


def main():
    predictors, Xval, yval = read_dataset(PROCESSED / "validation_features.csv")
    ftype, fsource = load_schema_meta()
    stats = json.loads((PROCESSED / "feature_statistics.json").read_text(encoding="utf-8"))
    val_missing = {f: stats["splits"]["validation"]["missingness"][f]["percentage"] for f in predictors}

    report = {
        "method": "XGBoost native TreeSHAP (pred_contribs=True), margin/log-odds space",
        "data": "validation split only (5675 rows, 66 positives)",
        "feature_version": "stage4-v1",
        "feature_count": len(predictors),
        "models": {},
    }
    for name in ("xgboost_tuned", "xgboost_baseline"):
        report["models"][name] = analyze_model(name, predictors, Xval, yval, ftype, val_missing)

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "shap_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # Console digest for the tuned model
    tuned = report["models"]["xgboost_tuned"]
    print("=== XGBoost tuned — SHAP digest (validation) ===")
    print("base value (log-odds):", tuned["base_value_logodds"])
    print("importance by type:", tuned["importance_by_type"])
    print("importance by base vital:", tuned["importance_by_base_vital"])
    print("temperature temporal importance share:", tuned["temperature_temporal_importance_share"])
    print("\nTop 15 features (tuned):")
    print(f"{'feature':28s} {'type':9s} {'share':>7s} {'corr':>6s} {'dir':>26s} {'miss%':>6s} {'frMiss':>6s}")
    for r in tuned["top_features"]:
        print(f"{r['feature']:28s} {r['type']:9s} {r['importance_share']:7.3f} "
              f"{str(r['value_shap_corr']):>6s} {r['direction']:>26s} {r['val_missing_pct']:6.1f} "
              f"{r['frac_importance_from_missing_rows']:6.2f}")
    print("\nMissingness-dominated features (tuned):")
    for r in tuned["missingness_dominated_features"]:
        print(f"  {r['feature']:28s} miss%={r['val_missing_pct']:.1f} "
              f"frMiss={r['frac_importance_from_missing_rows']:.2f} share={r['importance_share']:.3f}")
    print("\nWrote", RESULTS / "shap_summary.json")


if __name__ == "__main__":
    main()
