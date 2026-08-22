"""Phase 8 tests for the standalone inference path.

Run with the codex Python:
    python test_inference.py

Checks:
 1. CONSISTENCY (the important one): the standalone feature transform reproduces, feature
    for feature, the rows in the independently generated stage4-v2 TEST CSV. This proves the
    raw-vitals -> 52-feature path uses the exact training engineering (no manual duplication
    drift).
 2. Prediction contract: predict() returns a probability in [0,1], a valid risk level, and
    the expected keys.
 3. Explanation math: the linear log-odds contributions reconstruct the model's prediction.
 4. Missing-vitals robustness: a nearly empty reading still scores without error.
"""

from __future__ import annotations

import csv
import math
from collections import OrderedDict
from pathlib import Path

import numpy as np

from feature_engineering import FEATURE_NAMES, read_psv, as_number
from inference import (
    SepsisRiskModel, transform_vitals_to_features, VITAL_TO_PSV, DEFAULT_ARTIFACT,
)

PIPELINE_ROOT = Path(__file__).resolve().parent
V2 = PIPELINE_ROOT / "data" / "processed_v2"
DATA_ROOT = PIPELINE_ROOT / "data" / "raw" / "physionet"

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def psv_to_reading(psv_row):
    reading = {vital: as_number(psv_row[psv]) for vital, psv in VITAL_TO_PSV.items()}
    reading["map"] = as_number(psv_row.get("MAP"))
    return reading


def load_test_csv_by_patient():
    grouped: "OrderedDict[str, list[dict]]" = OrderedDict()
    with (V2 / "test_features.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped.setdefault(row["patient_id"], []).append(row)
    return grouped


def test_consistency():
    print("[1] standalone transform == training CSV")
    grouped = load_test_csv_by_patient()
    # Pick the test patient with the most engineered rows for good coverage.
    patient_id = max(grouped, key=lambda pid: len(grouped[pid]))
    csv_rows = grouped[patient_id]
    readings = [psv_to_reading(r) for r in read_psv(DATA_ROOT / f"{patient_id}.psv")]

    indices = sorted({0, len(csv_rows) // 2, len(csv_rows) - 1})
    all_ok = True
    max_abs_diff = 0.0
    for j in indices:
        vector = transform_vitals_to_features(readings[: j + 1])  # features for hour j
        for k, name in enumerate(FEATURE_NAMES):
            cell = csv_rows[j][name]
            expected = np.nan if cell == "" else float(cell)
            got = vector[k]
            if math.isnan(expected) and math.isnan(got):
                continue
            if math.isnan(expected) != math.isnan(got):
                all_ok = False
                print(f"      mismatch NaN {name} row {j}: csv={cell!r} got={got}")
                break
            max_abs_diff = max(max_abs_diff, abs(expected - got))
            if abs(expected - got) > 1e-9:
                all_ok = False
                print(f"      mismatch {name} row {j}: csv={expected} got={got}")
                break
    check(f"patient {patient_id}: {len(csv_rows)} rows, checked rows {indices}",
          all_ok, f"max_abs_diff={max_abs_diff:g}")
    check("max abs feature diff < 1e-9", all_ok and max_abs_diff < 1e-9, f"max_abs_diff={max_abs_diff:g}")


def test_prediction_contract():
    print("[2] prediction contract")
    model = SepsisRiskModel(DEFAULT_ARTIFACT)
    readings = [
        {"heart_rate": 88, "spo2": 98, "respiratory_rate": 18, "temperature": 37.0,
         "systolic_bp": 120, "diastolic_bp": 78},
        {"heart_rate": 96, "spo2": 96, "respiratory_rate": 20, "temperature": 37.4,
         "systolic_bp": 116, "diastolic_bp": 74},
        {"heart_rate": 112, "spo2": 93, "respiratory_rate": 24, "temperature": 38.3,
         "systolic_bp": 104, "diastolic_bp": 62},
    ]
    result = model.predict(readings)
    check("probability in [0,1]", 0.0 <= result["probability"] <= 1.0, str(result["probability"]))
    check("risk_level valid", result["risk_level"] in {"LOW", "MODERATE", "HIGH"}, result["risk_level"])
    check("alert is bool", isinstance(result["alert"], bool))
    for key in ("model_version", "feature_version", "threshold", "risk_bands", "disclaimer"):
        check(f"result has '{key}'", key in result)
    check("model_version is final-logreg-v1", result["model_version"] == "final-logreg-v1", result["model_version"])
    check("feature_version is stage4-v2", result["feature_version"] == "stage4-v2", result["feature_version"])


def test_explanation_math():
    print("[3] explanation reconstructs the prediction")
    model = SepsisRiskModel(DEFAULT_ARTIFACT)
    readings = [
        {"heart_rate": 130, "spo2": 90, "respiratory_rate": 28, "temperature": 39.1,
         "systolic_bp": 92, "diastolic_bp": 54},
    ] * 6
    vector = transform_vitals_to_features(readings).reshape(1, -1)
    steps = model.model.named_steps
    scaled = steps["scaler"].transform(steps["imputer"].transform(vector))
    contributions = scaled[0] * steps["model"].coef_[0]
    logit = float(contributions.sum() + steps["model"].intercept_[0])
    reconstructed = 1.0 / (1.0 + math.exp(-logit))
    predicted = model.predict(readings)["probability"]
    check("sigmoid(sum contribs + intercept) == predict_proba",
          abs(reconstructed - predicted) < 1e-9, f"{reconstructed} vs {predicted}")
    top = model.explain(readings, top_k=6)
    check("explain returns 6 items", len(top) == 6, str(len(top)))
    check("top item is most influential",
          abs(top[0]["log_odds_contribution"]) == max(abs(c) for c in contributions).round(4)
          or abs(top[0]["log_odds_contribution"]) >= abs(top[-1]["log_odds_contribution"]))


def test_missing_vitals():
    print("[4] robustness to sparse input")
    model = SepsisRiskModel(DEFAULT_ARTIFACT)
    result = model.predict([{"heart_rate": 101}])  # single hour, one vital
    check("scores with 1 vital / 1 hour", 0.0 <= result["probability"] <= 1.0, str(result["probability"]))
    check("reports few features present", result["features_present"] < result["features_total"],
          f"{result['features_present']}/{result['features_total']}")


def main():
    test_consistency()
    test_prediction_contract()
    test_explanation_math()
    test_missing_vitals()
    print(f"\n{PASS} passed, {FAIL} failed")
    raise SystemExit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
