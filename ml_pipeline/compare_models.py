"""Phase 4: unified comparison of all candidate models.

Models compared (all thresholds selected on VALIDATION only; test evaluated once):
  * Logistic Regression, Random Forest, XGBoost baseline, XGBoost tuned
    -- retrained on the adopted stage4-v2 tabular representation.
  * LSTM -- loaded from ml_pipeline/saved_models/lstm_sepsis.pt (Phase 3).

For reference, the Stage-5 stage4-v1 tabular TEST metrics are carried over from
results/model_metrics.json (already the "official" Stage-5 numbers).

Because the test set has only 60 positives, small metric differences are NOT
overinterpreted; validation is the primary basis for selection (Phase 5).

Writes results/model_comparison.json and prints a comparison table.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import torch

from train_stage5 import metrics, choose_threshold, read_csv_dataset, latency_ms, SEED
from experiment_stage4v2 import build_models
import lstm_experiment as L

PIPELINE_ROOT = Path(__file__).resolve().parent
V2 = PIPELINE_ROOT / "data" / "processed_v2"
RESULTS = PIPELINE_ROOT / "results"
MODELS = PIPELINE_ROOT / "saved_models"

METRIC_KEYS = ("auroc", "auprc", "sensitivity", "specificity", "precision", "npv", "f1", "false_positive_rate")


def lstm_latency_ms(model, features, lengths, repeats=3):
    with torch.no_grad():
        model(features[:1], lengths[:1])  # warm-up
        elapsed = []
        for _ in range(repeats):
            start = time.perf_counter()
            model(features, lengths)
            elapsed.append(time.perf_counter() - start)
    return round(1000 * min(elapsed) / len(features), 6)


def evaluate_tabular():
    train = read_csv_dataset(V2 / "train_features.csv")
    val = read_csv_dataset(V2 / "validation_features.csv")
    test = read_csv_dataset(V2 / "test_features.csv")
    assert train["features"] == val["features"] == test["features"], "feature order mismatch"
    assert len(train["features"]) == 52
    class_ratio = float((len(train["y"]) - train["y"].sum()) / train["y"].sum())

    v1 = json.loads((RESULTS / "model_metrics.json").read_text(encoding="utf-8"))
    out = {}
    for name, model in build_models(class_ratio).items():
        start = time.perf_counter()
        model.fit(train["X"], train["y"])
        train_seconds = time.perf_counter() - start
        val_prob = model.predict_proba(val["X"])[:, 1]
        threshold, val_metrics, meets = choose_threshold(val["y"], val_prob)
        test_prob = model.predict_proba(test["X"])[:, 1]
        test_metrics = metrics(test["y"], test_prob, threshold)
        joblib.dump({"model": model, "features": train["features"], "threshold": threshold,
                     "feature_version": "stage4-v2"}, MODELS / f"{name}_stage4v2.joblib")
        out[name] = {
            "family": "tabular", "feature_version": "stage4-v2",
            "training_seconds": round(train_seconds, 4),
            "threshold": threshold, "threshold_sensitivity_constraint_met": meets,
            "validation_metrics": val_metrics, "test_metrics": test_metrics,
            "inference_latency_ms_per_row": latency_ms(model, test["X"]),
            "test_metrics_stage4v1_reference": v1["models"][name]["test_metrics"],
            "validation_metrics_stage4v1_reference": v1["models"][name]["validation_metrics"],
        }
    return out


def evaluate_lstm():
    bundle = torch.load(MODELS / "lstm_sepsis.pt", weights_only=False)
    mean = np.array(bundle["standardization"]["mean"], dtype=np.float32)
    std = np.array(bundle["standardization"]["std"], dtype=np.float32)
    threshold = bundle["threshold"]

    model = L.SepsisLSTM()
    model.load_state_dict(bundle["state_dict"])
    model.eval()

    result = {}
    for split in ("validation", "test"):
        windows, masks, y, _, _ = L.build_examples(split)
        features, lengths, _ = L.to_tensors(windows, masks, y, mean, std)
        prob = L.predict_probs(model, features, lengths)
        result[split] = metrics(y, prob, threshold)
        if split == "test":
            latency = lstm_latency_ms(model, features, lengths)
    return {
        "lstm": {
            "family": "sequence", "feature_version": bundle["feature_version"],
            "architecture": bundle["architecture"], "best_epoch": bundle["best_epoch"],
            "threshold": threshold, "threshold_sensitivity_constraint_met": True,
            "validation_metrics": result["validation"], "test_metrics": result["test"],
            "inference_latency_ms_per_sequence": latency,
        }
    }


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.set_num_threads(4)

    models = evaluate_tabular()
    models.update(evaluate_lstm())

    report = {
        "note": "All thresholds selected on validation only; test evaluated once. "
                "Test has 60 positives -- small differences are not meaningful. "
                "Tabular models use stage4-v2; LSTM uses raw causal sequences.",
        "primary_selection_basis": "validation",
        "models": models,
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "model_comparison.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    order = ["logistic_regression", "random_forest", "xgboost_baseline", "xgboost_tuned", "lstm"]
    header = f"{'model':22s} | " + " ".join(f"{'v_'+k[:6]:>9s}" for k in ("auroc", "auprc", "sens", "spec")) + \
             " || " + " ".join(f"{'t_'+k[:6]:>9s}" for k in ("auroc", "auprc", "sens", "spec"))
    print("VALIDATION (v_) vs TEST (t_) -- thresholds fixed on validation")
    print(header)
    print("-" * len(header))
    for name in order:
        v = models[name]["validation_metrics"]
        t = models[name]["test_metrics"]
        print(f"{name:22s} | "
              f"{v['auroc']:9.4f} {v['auprc']:9.4f} {v['sensitivity']:9.3f} {v['specificity']:9.3f} || "
              f"{t['auroc']:9.4f} {t['auprc']:9.4f} {t['sensitivity']:9.3f} {t['specificity']:9.3f}")
    print("\nwrote", RESULTS / "model_comparison.json")


if __name__ == "__main__":
    main()
