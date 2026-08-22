"""Stage 4-v2 causal feature engineering (experimental).

Motivation (Phase 2, see docs/SHAP_ANALYSIS.md): temporal features carry ~71% of the
XGBoost model's SHAP importance, yet they are the most-missing features because the
stage4-v1 rolling statistics require ALL FOUR of [t-3..t] to be present. This discards
usable trailing signal, especially for sparse vitals (temperature, diastolic BP).

stage4-v2 changes exactly ONE thing versus stage4-v1:

    Rolling statistics (mean/std/min/max/trend over the trailing 4-hour window) are
    computed from the PRESENT values in [t-3..t] as long as at least TWO are present
    (min_periods=2). The trend slope uses the actual hour offsets of the present
    points, so units remain "per hour".

Everything else is identical to stage4-v1 and is reused directly from
feature_engineering.py:
  - the 52-feature schema and column order,
  - core current values and MAP fallback,
  - derived features (pulse_pressure, shock_index, spo2_rr_ratio),
  - change_1h / change_4h (EXACT-lag semantics, deliberately unchanged),
  - the approved 1-6h prospective target and onset/post-onset exclusion,
  - the immutable seed-42 patient splits (never regenerated here).

Strictly causal: every value for row t uses only rows at or before t of the same
patient; histories reset at patient boundaries. No future value, label, or
cross-patient information is used.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Mapping

# Reuse every shared definition from stage4-v1 so nothing silently diverges.
from feature_engineering import (
    CORE_SOURCES,
    TEMPORAL_VITALS,
    CORE_FEATURES,
    DERIVED_FEATURES,
    TEMPORAL_SUFFIXES,
    FEATURE_NAMES,
    OUTPUT_COLUMNS,
    as_number,
    safe_divide,
    population_std,
    first_positive_index,
    approved_target,
    current_core_values,
    read_psv,
    split_patient_ids,
)

ROLLING_MIN_PERIODS = 2


def slope_per_hour_xy(xs: list[float], ys: list[float]) -> float | None:
    """Least-squares slope of ys against hour offsets xs. Needs >=2 distinct xs."""
    n = len(xs)
    if n < 2:
        return None
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0:
        return None
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom


def engineer_patient_rows_v2(patient_id: str, raw_rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
    """stage4-v2 per-patient engineering; identical to v1 except rolling min_periods=2."""
    first_positive = first_positive_index(raw_rows)
    core_history = [current_core_values(row) for row in raw_rows]
    engineered: list[dict[str, object]] = []

    for index, raw_row in enumerate(raw_rows):
        target = approved_target(first_positive, index)
        if target is None:
            continue

        current = core_history[index]
        output: dict[str, object] = {
            "patient_id": patient_id,
            "timestamp": int(float(raw_row["ICULOS"])),
            **current,
            "pulse_pressure": (
                current["systolic_bp"] - current["diastolic_bp"]
                if current["systolic_bp"] is not None and current["diastolic_bp"] is not None
                else None
            ),
            "shock_index": safe_divide(current["heart_rate"], current["systolic_bp"]),
            "spo2_rr_ratio": safe_divide(current["spo2"], current["respiratory_rate"]),
            "target": target,
        }

        for vital in TEMPORAL_VITALS:
            value = current[vital]
            prior_1h = core_history[index - 1][vital] if index >= 1 else None
            prior_4h = core_history[index - 4][vital] if index >= 4 else None
            # EXACT-lag changes, unchanged from stage4-v1.
            output[f"{vital}_change_1h"] = (
                value - prior_1h if value is not None and prior_1h is not None else None
            )
            output[f"{vital}_change_4h"] = (
                value - prior_4h if value is not None and prior_4h is not None else None
            )
            # Rolling stats over PRESENT trailing values, min_periods=2 (the v2 change).
            window_positions = range(max(0, index - 3), index + 1)
            present_xy = [
                (float(position), float(core_history[position][vital]))
                for position in window_positions
                if core_history[position][vital] is not None
            ]
            if len(present_xy) >= ROLLING_MIN_PERIODS:
                xs = [xy[0] for xy in present_xy]
                ys = [xy[1] for xy in present_xy]
                output[f"{vital}_mean_4h"] = sum(ys) / len(ys)
                output[f"{vital}_std_4h"] = population_std(ys)
                output[f"{vital}_min_4h"] = min(ys)
                output[f"{vital}_max_4h"] = max(ys)
                output[f"{vital}_trend_4h"] = slope_per_hour_xy(xs, ys)
            else:
                for suffix in ("mean_4h", "std_4h", "min_4h", "max_4h", "trend_4h"):
                    output[f"{vital}_{suffix}"] = None
        engineered.append(output)
    return engineered


def feature_schema_v2() -> dict[str, object]:
    units = {
        "heart_rate": "beats/min", "spo2": "%", "respiratory_rate": "breaths/min",
        "temperature": "degrees C", "systolic_bp": "mmHg", "diastolic_bp": "mmHg", "map": "mmHg",
    }
    features = []
    for name in CORE_FEATURES:
        source = "MAP raw value; fallback from current SBP and DBP" if name == "map" else f"PhysioNet {CORE_SOURCES[name]}"
        features.append({"name": name, "type": "core", "source": source, "calculation": "current-row value", "units": units[name], "historical_window_hours": 0, "can_be_missing": True})
    features.extend([
        {"name": "pulse_pressure", "type": "derived", "source": "systolic_bp, diastolic_bp", "calculation": "systolic_bp - diastolic_bp", "units": "mmHg", "historical_window_hours": 0, "can_be_missing": True},
        {"name": "shock_index", "type": "derived", "source": "heart_rate, systolic_bp", "calculation": "heart_rate / systolic_bp when SBP > 0", "units": "1", "historical_window_hours": 0, "can_be_missing": True},
        {"name": "spo2_rr_ratio", "type": "derived", "source": "spo2, respiratory_rate", "calculation": "spo2 / respiratory_rate when RR > 0", "units": "% per breaths/min", "historical_window_hours": 0, "can_be_missing": True},
    ])
    for vital in TEMPORAL_VITALS:
        for suffix in TEMPORAL_SUFFIXES:
            calc = {
                "change_1h": "value[t] - value[t-1] (exact lag)",
                "change_4h": "value[t] - value[t-4] (exact lag)",
                "mean_4h": "mean of present value[t-3:t], min_periods=2",
                "std_4h": "population std of present value[t-3:t], min_periods=2",
                "min_4h": "min of present value[t-3:t], min_periods=2",
                "max_4h": "max of present value[t-3:t], min_periods=2",
                "trend_4h": "least-squares slope over present value[t-3:t] hour offsets, min_periods=2",
            }[suffix]
            features.append({"name": f"{vital}_{suffix}", "type": "temporal", "source": vital, "calculation": calc, "units": f"{units[vital]}" + ("/hour" if suffix.startswith("change") or suffix == "trend_4h" else ""), "historical_window_hours": 1 if suffix == "change_1h" else 4, "can_be_missing": True})
    return {"version": "stage4-v2", "parent_version": "stage4-v1", "rolling_min_periods": ROLLING_MIN_PERIODS,
            "change_semantics": "exact-lag (unchanged from stage4-v1)",
            "feature_count": len(FEATURE_NAMES), "features": features,
            "excluded_columns": ["SepsisLabel", "target"], "target_column": "target"}


def generate_v2(project_root: Path, splits=("train", "validation", "test")) -> dict[str, object]:
    pipeline_root = project_root / "ml_pipeline"
    data_root = pipeline_root / "data" / "raw" / "physionet"
    splits_root = pipeline_root / "data" / "splits"
    output_root = pipeline_root / "data" / "processed_v2"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "feature_schema.json").write_text(json.dumps(feature_schema_v2(), indent=2) + "\n", encoding="utf-8")

    all_statistics: dict[str, object] = {"version": "stage4-v2", "feature_count": len(FEATURE_NAMES), "splits": {}}
    for split_name in splits:
        patient_ids = split_patient_ids(splits_root / f"{split_name}_patients.txt")
        output_path = output_root / f"{split_name}_features.csv"
        missing = {feature: 0 for feature in FEATURE_NAMES}
        raw_rows = feature_rows = positives = excluded = 0
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for patient_id in patient_ids:
                patient_rows = read_psv(data_root / f"{patient_id}.psv")
                raw_rows += len(patient_rows)
                rows = engineer_patient_rows_v2(patient_id, patient_rows)
                feature_rows += len(rows)
                excluded += len(patient_rows) - len(rows)
                for row in rows:
                    positives += int(row["target"])
                    for feature in FEATURE_NAMES:
                        if row[feature] is None:
                            missing[feature] += 1
                    writer.writerow({key: "" if value is None else value for key, value in row.items()})
        all_statistics["splits"][split_name] = {
            "patients": len(patient_ids), "raw_rows": raw_rows, "feature_rows": feature_rows,
            "rows_removed": raw_rows - feature_rows, "positive_samples": positives,
            "negative_samples": feature_rows - positives,
            "missingness": {f: {"count": missing[f], "percentage": round(100 * missing[f] / feature_rows, 6)} for f in FEATURE_NAMES},
            "excluded_inferred_onset_or_post_onset_rows": excluded,
        }
    (output_root / "feature_statistics.json").write_text(json.dumps(all_statistics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return all_statistics


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parent.parent
    # Default: train + validation only, to keep the test set untouched during Phase 2.
    requested = sys.argv[1:] or ["train", "validation"]
    print(json.dumps(generate_v2(root, splits=tuple(requested)), indent=2))
