"""Phase 2 experiment: does stage4-v2 (relaxed rolling min_periods=2) improve the
tabular models on the VALIDATION split, versus stage4-v1?

Trains the exact Stage 5 model configurations on stage4-v2 train data and evaluates on
stage4-v2 validation data, selecting each threshold on validation only. Compares against
the stage4-v1 validation metrics recorded in results/model_metrics.json.

The TEST set is not touched here. Reuses metrics/choose_threshold/read_csv_dataset from
train_stage5.py so metric computation is identical to Stage 5.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from train_stage5 import metrics, choose_threshold, read_csv_dataset, SEED

PIPELINE_ROOT = Path(__file__).resolve().parent
V2 = PIPELINE_ROOT / "data" / "processed_v2"
RESULTS = PIPELINE_ROOT / "results"


def build_models(class_ratio: float):
    return {
        "logistic_regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
        ]),
        "random_forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(n_estimators=300, max_depth=None, min_samples_leaf=1,
                                             class_weight="balanced_subsample", random_state=SEED, n_jobs=-1)),
        ]),
        "xgboost_baseline": XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8,
                                          colsample_bytree=0.8, scale_pos_weight=class_ratio,
                                          objective="binary:logistic", eval_metric="aucpr",
                                          random_state=SEED, n_jobs=4, tree_method="hist"),
        "xgboost_tuned": XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
                                       colsample_bytree=0.8, scale_pos_weight=class_ratio,
                                       objective="binary:logistic", eval_metric="aucpr",
                                       random_state=SEED, n_jobs=4, tree_method="hist"),
    }


def main():
    train = read_csv_dataset(V2 / "train_features.csv")
    val = read_csv_dataset(V2 / "validation_features.csv")
    assert train["features"] == val["features"], "feature order mismatch"
    assert len(train["features"]) == 52
    class_ratio = float((len(train["y"]) - train["y"].sum()) / train["y"].sum())

    report = {"feature_version": "stage4-v2", "train_class_ratio_negative_to_positive": round(class_ratio, 6),
              "validation_positives": int(val["y"].sum()), "validation_rows": int(len(val["y"])), "models": {}}
    for name, model in build_models(class_ratio).items():
        start = time.perf_counter()
        model.fit(train["X"], train["y"])
        seconds = time.perf_counter() - start
        val_prob = model.predict_proba(val["X"])[:, 1]
        threshold, val_metrics, meets = choose_threshold(val["y"], val_prob)
        report["models"][name] = {"training_seconds": round(seconds, 6), "threshold": threshold,
                                  "threshold_sensitivity_constraint_met": meets, "validation_metrics": val_metrics}

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "stage4v2_validation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    v1 = json.loads((RESULTS / "model_metrics.json").read_text(encoding="utf-8"))
    print("VALIDATION comparison (threshold selected on validation only)")
    print(f"{'model':22s} | {'v1 AUROC':>8s} {'v1 AUPRC':>8s} {'v1 Sens':>7s} {'v1 Spec':>7s} | "
          f"{'v2 AUROC':>8s} {'v2 AUPRC':>8s} {'v2 Sens':>7s} {'v2 Spec':>7s}")
    for name in report["models"]:
        a = v1["models"][name]["validation_metrics"]
        b = report["models"][name]["validation_metrics"]
        print(f"{name:22s} | {a['auroc']:8.4f} {a['auprc']:8.4f} {a['sensitivity']:7.3f} {a['specificity']:7.3f} | "
              f"{b['auroc']:8.4f} {b['auprc']:8.4f} {b['sensitivity']:7.3f} {b['specificity']:7.3f}")
    print("\nWrote", RESULTS / "stage4v2_validation.json")


if __name__ == "__main__":
    main()
