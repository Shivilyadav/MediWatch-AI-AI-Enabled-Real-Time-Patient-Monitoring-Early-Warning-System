"""Causal Stage 4 feature engineering for PhysioNet hourly PSV records.

This module is intentionally model-free. It uses the approved Stage 3 target
definition and the immutable Stage 2 patient assignments. Every temporal value
for row t uses only rows at or before t from the same patient.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable, Mapping


CORE_SOURCES = {
    "heart_rate": "HR",
    "spo2": "O2Sat",
    "respiratory_rate": "Resp",
    "temperature": "Temp",
    "systolic_bp": "SBP",
    "diastolic_bp": "DBP",
}
TEMPORAL_VITALS = tuple(CORE_SOURCES)
CORE_FEATURES = (*TEMPORAL_VITALS, "map")
DERIVED_FEATURES = ("pulse_pressure", "shock_index", "spo2_rr_ratio")
TEMPORAL_SUFFIXES = (
    "change_1h",
    "change_4h",
    "mean_4h",
    "std_4h",
    "min_4h",
    "max_4h",
    "trend_4h",
)
FEATURE_NAMES = [
    *CORE_FEATURES,
    *DERIVED_FEATURES,
    *(f"{vital}_{suffix}" for vital in TEMPORAL_VITALS for suffix in TEMPORAL_SUFFIXES),
]
OUTPUT_COLUMNS = ["patient_id", "timestamp", *FEATURE_NAMES, "target"]


def as_number(value: object) -> float | None:
    """Convert PSV values to finite floats, treating blank and NaN as missing."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def population_std(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def slope_per_hour(values: list[float]) -> float:
    """Least-squares slope over equally spaced, trailing hourly observations."""
    x_values = list(range(len(values)))
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(values) / len(values)
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values)) / denominator


def first_positive_index(rows: Iterable[Mapping[str, object]]) -> int | None:
    for index, row in enumerate(rows):
        if int(float(row["SepsisLabel"])) == 1:
            return index
    return None


def approved_target(first_positive: int | None, index: int) -> int | None:
    """Return approved 1–6 hour target, or None for excluded onset/post-onset rows."""
    if first_positive is None:
        return 0
    onset_proxy_index = first_positive + 6
    if index >= onset_proxy_index:
        return None
    return int(index >= first_positive)


def current_core_values(row: Mapping[str, object]) -> dict[str, float | None]:
    values = {name: as_number(row[source]) for name, source in CORE_SOURCES.items()}
    direct_map = as_number(row.get("MAP"))
    # Direct MAP is retained when recorded. The formula is a current-row fallback
    # only; no carry-forward or competing MAP feature is created.
    values["map"] = direct_map if direct_map is not None else (
        (values["systolic_bp"] + 2 * values["diastolic_bp"]) / 3
        if values["systolic_bp"] is not None and values["diastolic_bp"] is not None
        else None
    )
    return values


def engineer_patient_rows(patient_id: str, raw_rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
    """Engineer valid rows for one patient without crossing patient boundaries."""
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
            output[f"{vital}_change_1h"] = (
                value - prior_1h if value is not None and prior_1h is not None else None
            )
            output[f"{vital}_change_4h"] = (
                value - prior_4h if value is not None and prior_4h is not None else None
            )
            trailing = [core_history[position][vital] for position in range(max(0, index - 3), index + 1)]
            if len(trailing) == 4 and all(item is not None for item in trailing):
                values = [float(item) for item in trailing]
                output[f"{vital}_mean_4h"] = sum(values) / 4
                output[f"{vital}_std_4h"] = population_std(values)
                output[f"{vital}_min_4h"] = min(values)
                output[f"{vital}_max_4h"] = max(values)
                output[f"{vital}_trend_4h"] = slope_per_hour(values)
            else:
                for suffix in ("mean_4h", "std_4h", "min_4h", "max_4h", "trend_4h"):
                    output[f"{vital}_{suffix}"] = None
        engineered.append(output)
    return engineered


def read_psv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="|"))


def split_patient_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def feature_schema() -> dict[str, object]:
    features = []
    units = {
        "heart_rate": "beats/min", "spo2": "%", "respiratory_rate": "breaths/min",
        "temperature": "degrees C", "systolic_bp": "mmHg", "diastolic_bp": "mmHg", "map": "mmHg",
    }
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
            calculation = {
                "change_1h": "value[t] - value[t-1]", "change_4h": "value[t] - value[t-4]",
                "mean_4h": "mean(value[t-3:t])", "std_4h": "population standard deviation of value[t-3:t]",
                "min_4h": "minimum of value[t-3:t]", "max_4h": "maximum of value[t-3:t]",
                "trend_4h": "least-squares slope over value[t-3:t]",
            }[suffix]
            features.append({"name": f"{vital}_{suffix}", "type": "temporal", "source": vital, "calculation": calculation, "units": f"{units[vital]}" + ("/hour" if suffix.startswith("change") or suffix == "trend_4h" else ""), "historical_window_hours": 1 if suffix == "change_1h" else 4, "can_be_missing": True})
    return {"version": "stage4-v1", "feature_count": len(FEATURE_NAMES), "features": features, "excluded_columns": ["SepsisLabel", "target"], "target_column": "target"}


def generate_processed_datasets(project_root: Path) -> dict[str, object]:
    """Create CSV feature datasets from existing seed-42 split artifacts."""
    pipeline_root = project_root / "ml_pipeline"
    data_root = pipeline_root / "data" / "raw" / "physionet"
    splits_root = pipeline_root / "data" / "splits"
    output_root = pipeline_root / "data" / "processed"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "feature_schema.json").write_text(json.dumps(feature_schema(), indent=2) + "\n", encoding="utf-8")

    all_statistics: dict[str, object] = {"feature_count": len(FEATURE_NAMES), "splits": {}}
    for split_name in ("train", "validation", "test"):
        patient_ids = split_patient_ids(splits_root / f"{split_name}_patients.txt")
        output_path = output_root / f"{split_name}_features.csv"
        missing = {feature: 0 for feature in FEATURE_NAMES}
        raw_rows = feature_rows = positives = excluded = 0
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for patient_id in patient_ids:
                source_path = data_root / f"{patient_id}.psv"
                patient_rows = read_psv(source_path)
                raw_rows += len(patient_rows)
                rows = engineer_patient_rows(patient_id, patient_rows)
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
            "rows_removed": raw_rows - feature_rows, "patients_removed": 0,
            "positive_samples": positives, "negative_samples": feature_rows - positives,
            "positive_samples_removed": 0,
            "missingness": {feature: {"count": missing[feature], "percentage": round(100 * missing[feature] / feature_rows, 6)} for feature in FEATURE_NAMES},
            "excluded_inferred_onset_or_post_onset_rows": excluded,
        }
    (output_root / "feature_statistics.json").write_text(json.dumps(all_statistics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return all_statistics


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    print(json.dumps(generate_processed_datasets(root), indent=2))
