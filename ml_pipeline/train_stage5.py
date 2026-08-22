"""Stage 5 baseline and XGBoost experiment runner; not a deployment path."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent
LOCAL_PACKAGES = PIPELINE_ROOT / ".stage5_packages"
if LOCAL_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_PACKAGES))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


SEED = 42
FORBIDDEN_COLUMNS = {"patient_id", "timestamp", "target", "SepsisLabel"}


def read_csv_dataset(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        header = reader.fieldnames
    if not header:
        raise ValueError(f"Missing header in {path}")
    predictors = [column for column in header if column not in {"patient_id", "timestamp", "target"}]
    matrix = np.array(
        [[float(row[column]) if row[column] != "" else np.nan for column in predictors] for row in rows],
        dtype=float,
    )
    target = np.array([int(row["target"]) for row in rows], dtype=int)
    return {"header": header, "features": predictors, "X": matrix, "y": target, "patients": [row["patient_id"] for row in rows]}


def read_ids(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def validate_inputs(processed_root: Path, splits_root: Path):
    datasets = {name: read_csv_dataset(processed_root / f"{name}_features.csv") for name in ("train", "validation", "test")}
    schema = json.loads((processed_root / "feature_schema.json").read_text(encoding="utf-8"))
    expected_features = [item["name"] for item in schema["features"]]
    if len(expected_features) != 52 or schema["feature_count"] != 52:
        raise ValueError("Feature schema must contain exactly 52 predictors")
    expected_counts = {"train": (27349, 300), "validation": (5675, 66), "test": (5618, 60)}
    split_ids = {name: read_ids(splits_root / f"{name}_patients.txt") for name in datasets}
    if split_ids["train"] & split_ids["validation"] or split_ids["train"] & split_ids["test"] or split_ids["validation"] & split_ids["test"]:
        raise ValueError("Patient overlap in Stage 2 split artifacts")
    for name, dataset in datasets.items():
        if dataset["features"] != expected_features:
            raise ValueError(f"Feature schema mismatch for {name}")
        if len(dataset["features"]) != 52 or set(dataset["features"]) & FORBIDDEN_COLUMNS:
            raise ValueError(f"Predictor leakage or wrong feature count for {name}")
        if len(dataset["X"]) != expected_counts[name][0] or int(dataset["y"].sum()) != expected_counts[name][1]:
            raise ValueError(f"Unexpected Stage 4 target distribution for {name}")
        if set(dataset["patients"]) != split_ids[name]:
            raise ValueError(f"Processed patient IDs do not match the fixed {name} split")
    return datasets, expected_features


def news2_score(X: np.ndarray, feature_index: dict[str, int]) -> np.ndarray:
    """Adapted NEWS2: no oxygen/mental-status fields are available in this data."""
    def component(values, rules):
        result = np.zeros(len(values), dtype=float)
        valid = ~np.isnan(values)
        for predicate, points in rules:
            result[valid & predicate(values)] = points
        return result
    hr = X[:, feature_index["heart_rate"]]
    spo2 = X[:, feature_index["spo2"]]
    rr = X[:, feature_index["respiratory_rate"]]
    temp = X[:, feature_index["temperature"]]
    sbp = X[:, feature_index["systolic_bp"]]
    rr_score = component(rr, [(lambda x: x <= 8, 3), (lambda x: (x >= 9) & (x <= 11), 1), (lambda x: (x >= 12) & (x <= 20), 0), (lambda x: (x >= 21) & (x <= 24), 2), (lambda x: x >= 25, 3)])
    spo2_score = component(spo2, [(lambda x: x <= 91, 3), (lambda x: (x >= 92) & (x <= 93), 2), (lambda x: (x >= 94) & (x <= 95), 1), (lambda x: x >= 96, 0)])
    temp_score = component(temp, [(lambda x: x <= 35, 3), (lambda x: (x > 35) & (x <= 36), 1), (lambda x: (x > 36) & (x <= 38), 0), (lambda x: (x > 38) & (x <= 39), 1), (lambda x: x > 39, 2)])
    sbp_score = component(sbp, [(lambda x: x <= 90, 3), (lambda x: (x >= 91) & (x <= 100), 2), (lambda x: (x >= 101) & (x <= 110), 1), (lambda x: (x >= 111) & (x <= 219), 0), (lambda x: x >= 220, 3)])
    hr_score = component(hr, [(lambda x: x <= 40, 3), (lambda x: (x >= 41) & (x <= 50), 1), (lambda x: (x >= 51) & (x <= 90), 0), (lambda x: (x >= 91) & (x <= 110), 1), (lambda x: (x >= 111) & (x <= 130), 2), (lambda x: x >= 131, 3)])
    return rr_score + spo2_score + temp_score + sbp_score + hr_score


def wilson_interval(successes: int, total: int, z: float = 1.96):
    if total == 0:
        return [None, None]
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [round(center - half, 6), round(center + half, 6)]


def metrics(y: np.ndarray, probabilities: np.ndarray, threshold: float):
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    sensitivity = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    npv = tn / (tn + fn) if tn + fn else 0.0
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if precision + sensitivity else 0.0
    return {
        "auroc": round(float(roc_auc_score(y, probabilities)), 6), "auprc": round(float(average_precision_score(y, probabilities)), 6),
        "sensitivity": round(sensitivity, 6), "specificity": round(specificity, 6), "precision": round(precision, 6), "npv": round(npv, 6), "f1": round(f1, 6), "false_positive_rate": round(1 - specificity, 6),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "sensitivity_95ci_wilson": wilson_interval(int(tp), int(tp + fn)),
        "specificity_95ci_wilson": wilson_interval(int(tn), int(tn + fp)),
        "positive_samples": int(y.sum()), "negative_samples": int(len(y) - y.sum()),
    }


def choose_threshold(y: np.ndarray, probabilities: np.ndarray):
    """Maximize F1 among thresholds reaching 0.80 validation sensitivity, if possible."""
    candidates = np.unique(np.r_[0.0, probabilities, 1.0])
    scored = [(threshold, metrics(y, probabilities, float(threshold))) for threshold in candidates]
    eligible = [(threshold, score) for threshold, score in scored if score["sensitivity"] >= 0.80]
    pool = eligible if eligible else scored
    threshold, selected = max(pool, key=lambda item: (item[1]["f1"], item[1]["sensitivity"], item[1]["specificity"]))
    return float(threshold), selected, bool(eligible)


def latency_ms(model, X: np.ndarray, repeats: int = 5):
    model.predict_proba(X[:1])  # warm-up
    elapsed = []
    for _ in range(repeats):
        start = time.perf_counter()
        model.predict_proba(X)
        elapsed.append(time.perf_counter() - start)
    return round(1000 * min(elapsed) / len(X), 6)


def train_and_evaluate(project_root: Path):
    processed = project_root / "ml_pipeline" / "data" / "processed"
    splits = project_root / "ml_pipeline" / "data" / "splits"
    results_dir = project_root / "ml_pipeline" / "results"
    models_dir = project_root / "ml_pipeline" / "saved_models"
    results_dir.mkdir(exist_ok=True); models_dir.mkdir(exist_ok=True)
    data, features = validate_inputs(processed, splits)
    train, validation, test = data["train"], data["validation"], data["test"]
    class_ratio = float((len(train["y"]) - train["y"].sum()) / train["y"].sum())
    feature_index = {name: index for index, name in enumerate(features)}
    report = {"feature_version": "stage4-v1", "feature_count": len(features), "training_seed": SEED, "train_class_ratio_negative_to_positive": round(class_ratio, 6), "models": {}}

    # NEWS2 is a rule benchmark; missing components contribute zero, and room-air/no-confusion is assumed.
    news_val = news2_score(validation["X"], feature_index); news_test = news2_score(test["X"], feature_index)
    news_threshold, news_validation, news_met_sens = choose_threshold(validation["y"], news_val)
    class NewsModel:
        def __init__(self, index): self.index = index
        def predict_proba(self, X):
            scores = news2_score(X, self.index); return np.column_stack([np.zeros(len(scores)), scores])
    news_model = NewsModel(feature_index)
    report["models"]["news2_adapted"] = {"configuration": {"available_components": ["respiratory_rate", "spo2_scale_1", "temperature", "systolic_bp", "heart_rate"], "unavailable_components": ["supplemental_oxygen", "consciousness_or_new_confusion"], "missing_component_policy": "0 points"}, "threshold": news_threshold, "threshold_sensitivity_constraint_met": news_met_sens, "validation_metrics": news_validation, "test_metrics": metrics(test["y"], news_test, news_threshold), "inference_latency_ms_per_row": latency_ms(news_model, test["X"])}

    models = {
        "logistic_regression": (Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED))]), {"class_weight": "balanced", "imputer": "median fit on train", "scaler": "standard scaler fit on train"}),
        "random_forest": (Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", RandomForestClassifier(n_estimators=300, max_depth=None, min_samples_leaf=1, class_weight="balanced_subsample", random_state=SEED, n_jobs=-1))]), {"n_estimators": 300, "class_weight": "balanced_subsample", "imputer": "median fit on train"}),
    }
    trained = {}
    for name, (model, config) in models.items():
        start = time.perf_counter(); model.fit(train["X"], train["y"]); training_seconds = time.perf_counter() - start
        val_prob = model.predict_proba(validation["X"])[:, 1]; threshold, val_metrics, meets = choose_threshold(validation["y"], val_prob)
        test_prob = model.predict_proba(test["X"])[:, 1]
        joblib.dump({"model": model, "features": features, "threshold": threshold, "feature_version": "stage4-v1"}, models_dir / f"{name}_stage5.joblib")
        report["models"][name] = {"configuration": config, "training_seconds": round(training_seconds, 6), "threshold": threshold, "threshold_sensitivity_constraint_met": meets, "validation_metrics": val_metrics, "test_metrics": metrics(test["y"], test_prob, threshold), "inference_latency_ms_per_row": latency_ms(model, test["X"])}
        trained[name] = model

    baseline_config = {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.8, "colsample_bytree": 0.8, "scale_pos_weight": class_ratio}
    candidates = [baseline_config, {"n_estimators": 300, "max_depth": 3, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.8, "scale_pos_weight": class_ratio}, {"n_estimators": 300, "max_depth": 5, "learning_rate": 0.03, "subsample": 0.8, "colsample_bytree": 1.0, "scale_pos_weight": class_ratio}, {"n_estimators": 400, "max_depth": 4, "learning_rate": 0.03, "subsample": 0.9, "colsample_bytree": 0.9, "scale_pos_weight": class_ratio}]
    xgb_runs = []
    for config in candidates:
        model = XGBClassifier(**config, objective="binary:logistic", eval_metric="aucpr", random_state=SEED, n_jobs=4, tree_method="hist")
        start = time.perf_counter(); model.fit(train["X"], train["y"]); seconds = time.perf_counter() - start
        probabilities = model.predict_proba(validation["X"])[:, 1]
        threshold, val_metrics, meets = choose_threshold(validation["y"], probabilities)
        xgb_runs.append((model, config, seconds, threshold, val_metrics, meets))
    baseline = xgb_runs[0]
    tuned = max(xgb_runs[1:], key=lambda run: (run[4]["auprc"], run[4]["auroc"], run[4]["f1"]))
    for name, run in (("xgboost_baseline", baseline), ("xgboost_tuned", tuned)):
        model, config, seconds, threshold, val_metrics, meets = run
        test_prob = model.predict_proba(test["X"])[:, 1]
        joblib.dump({"model": model, "features": features, "threshold": threshold, "feature_version": "stage4-v1"}, models_dir / f"{name}_stage5.joblib")
        report["models"][name] = {"configuration": {**config, "search_candidates": len(candidates) - 1 if name == "xgboost_tuned" else 0}, "training_seconds": round(seconds, 6), "threshold": threshold, "threshold_sensitivity_constraint_met": meets, "validation_metrics": val_metrics, "test_metrics": metrics(test["y"], test_prob, threshold), "inference_latency_ms_per_row": latency_ms(model, test["X"])}

    (results_dir / "model_metrics.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = train_and_evaluate(PIPELINE_ROOT.parent)
    print(json.dumps(result, indent=2))
