"""Phase 6: build the versioned final-model artifact.

Selected model (see docs/FINAL_MODEL.md): Logistic Regression on the stage4-v2 52-feature
representation. This trains it deterministically (seed 42) on stage4-v2 train, selects the
threshold on validation, derives risk-band cut points from the VALIDATION probability
distribution, and saves a self-contained artifact:

    ml_pipeline/saved_models/final_model_v1.pkl

The artifact does NOT overwrite ml_pipeline/model.pkl (the backend model) and does NOT
overwrite any earlier experiment bundle. Test metrics are read from the already-recorded
one-time evaluation (results/model_comparison.json); the test set is not re-touched here.
"""

from __future__ import annotations

import json
import platform
from pathlib import Path

import joblib
import numpy as np
import sklearn

from train_stage5 import read_csv_dataset, choose_threshold, metrics, SEED
from experiment_stage4v2 import build_models

PIPELINE_ROOT = Path(__file__).resolve().parent
V2 = PIPELINE_ROOT / "data" / "processed_v2"
RESULTS = PIPELINE_ROOT / "results"
MODELS = PIPELINE_ROOT / "saved_models"

MODEL_VERSION = "final-logreg-v1"
FAMILY = "logistic_regression"


def main():
    train = read_csv_dataset(V2 / "train_features.csv")
    val = read_csv_dataset(V2 / "validation_features.csv")
    assert train["features"] == val["features"] and len(train["features"]) == 52
    class_ratio = float((len(train["y"]) - train["y"].sum()) / train["y"].sum())

    model = build_models(class_ratio)[FAMILY]
    model.fit(train["X"], train["y"])

    val_prob = model.predict_proba(val["X"])[:, 1]
    threshold, val_metrics, meets = choose_threshold(val["y"], val_prob)

    # Risk-band cut points from the VALIDATION probability distribution (documented, naive).
    moderate_cut = float(threshold)
    high_cut = float(np.quantile(val_prob, 0.95))

    schema = json.loads((V2 / "feature_schema.json").read_text(encoding="utf-8"))
    comparison = json.loads((RESULTS / "model_comparison.json").read_text(encoding="utf-8"))
    test_metrics = comparison["models"][FAMILY]["test_metrics"]

    artifact = {
        "model_version": MODEL_VERSION,
        "feature_version": "stage4-v2",
        "family": FAMILY,
        "model": model,  # sklearn Pipeline: median imputer -> standard scaler -> LogisticRegression
        "features": train["features"],  # 52-name input contract, exact order
        "feature_schema": schema,
        "preprocessing": {
            "imputation": "median, fit on stage4-v2 train",
            "scaling": "standardization (zero mean/unit var), fit on stage4-v2 train",
            "note": "Both steps are encapsulated inside the saved sklearn Pipeline; "
                    "callers pass the raw 52-feature vector (NaN allowed for missing).",
        },
        "threshold": threshold,
        "threshold_policy": "max F1 among thresholds reaching >= 0.80 validation sensitivity",
        "threshold_sensitivity_constraint_met": meets,
        "risk_bands": {
            "definition": {
                "low": "probability < moderate_cut",
                "moderate": "moderate_cut <= probability < high_cut",
                "high": "probability >= high_cut",
            },
            "moderate_cut": moderate_cut,
            "high_cut": high_cut,
            "derived_from": "validation predicted-probability distribution (high_cut = val P95)",
            "caveat": "LogisticRegression outputs are NOT calibrated to true event probability; "
                      "bands are ordinal research signals only.",
        },
        "training": {
            "seed": SEED,
            "class_weight": "balanced",
            "max_iter": 2000,
            "n_train_rows": int(len(train["y"])),
            "n_train_positive": int(train["y"].sum()),
            "class_ratio_negative_to_positive": round(class_ratio, 6),
        },
        "metrics": {"validation": val_metrics, "test": test_metrics},
        "intended_use": (
            "Research/hackathon early-warning BENCHMARK trained on a 1000-patient PhysioNet "
            "2019 subset. NOT a clinical diagnostic tool and NOT deployment-ready: at the "
            "required sensitivity the false-positive rate is ~0.59 and precision ~1.5%. "
            "See docs/FINAL_MODEL.md."
        ),
        "created_with": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }

    MODELS.mkdir(exist_ok=True)
    out = MODELS / "final_model_v1.pkl"
    assert out.name != "model.pkl"
    joblib.dump(artifact, out)

    print(f"model_version={MODEL_VERSION} feature_version=stage4-v2")
    print(f"threshold={threshold:.5f} meets_sens_constraint={meets}")
    print(f"risk bands: low<{moderate_cut:.4f} <=moderate< {high_cut:.4f} <=high")
    print("validation:", {k: val_metrics[k] for k in ("auroc", "auprc", "sensitivity", "specificity", "precision", "f1", "false_positive_rate")})
    print("test:", {k: test_metrics[k] for k in ("auroc", "auprc", "sensitivity", "specificity", "precision", "f1", "false_positive_rate")})
    print("saved", out)


if __name__ == "__main__":
    main()
