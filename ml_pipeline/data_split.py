"""Deterministic, patient-level split generation for PhysioNet PSV data.

This module intentionally uses only the Python standard library so that data
audit/splitting remains runnable before model-training dependencies are installed.
It does not fit models or alter labels.
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SEED = 42
SPLIT_NAMES = ("train", "validation", "test")
SPLIT_RATIOS = (0.70, 0.15, 0.15)
CORE_FEATURES = ("HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp")


@dataclass(frozen=True)
class PatientMetadata:
    """Metadata derived from a single PSV file without changing its rows."""

    patient_id: str
    path: Path
    row_count: int
    positive_rows: int

    @property
    def has_positive_label(self) -> bool:
        return self.positive_rows > 0


def patient_id_from_path(path: Path, data_root: Path) -> str:
    """Return a stable ID that remains unique if filenames repeat across sets."""
    return path.relative_to(data_root).with_suffix("").as_posix()


def discover_patient_files(data_root: Path) -> list[Path]:
    return sorted(data_root.rglob("*.psv"))


def read_patient_rows(path: Path) -> list[dict[str, str]]:
    """Read a PSV file in its original row order."""
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="|"))


def load_patient_metadata(data_root: Path) -> list[PatientMetadata]:
    records: list[PatientMetadata] = []
    for path in discover_patient_files(data_root):
        rows = read_patient_rows(path)
        positive_rows = sum(int(float(row["SepsisLabel"])) for row in rows)
        records.append(
            PatientMetadata(
                patient_id=patient_id_from_path(path, data_root),
                path=path,
                row_count=len(rows),
                positive_rows=positive_rows,
            )
        )
    if not records:
        raise FileNotFoundError(f"No PSV files found under {data_root}")
    return records


def _largest_remainder_counts(total: int) -> tuple[int, int, int]:
    """Allocate an integer total across the configured ratios deterministically."""
    raw = [total * ratio for ratio in SPLIT_RATIOS]
    counts = [int(value) for value in raw]
    remaining = total - sum(counts)
    order = sorted(range(3), key=lambda i: (raw[i] - counts[i], -i), reverse=True)
    for index in order[:remaining]:
        counts[index] += 1
    return tuple(counts)  # type: ignore[return-value]


def stratified_patient_split(
    records: Iterable[PatientMetadata], seed: int = DEFAULT_SEED
) -> dict[str, list[str]]:
    """Split patients, stratified only by whether they ever have a positive label.

    Total split sizes follow 70/15/15 exactly when possible. The positive-patient
    allocation is rounded by largest remainder, then negatives fill each target.
    Rows are never independently shuffled or stratified.
    """
    records = sorted(records, key=lambda record: record.patient_id)
    totals = _largest_remainder_counts(len(records))
    positive_ids = [record.patient_id for record in records if record.has_positive_label]
    negative_ids = [record.patient_id for record in records if not record.has_positive_label]

    rng = random.Random(seed)
    rng.shuffle(positive_ids)
    rng.shuffle(negative_ids)

    positive_counts = _largest_remainder_counts(len(positive_ids))
    if any(positive_counts[i] > totals[i] for i in range(3)):
        raise ValueError("Positive-patient allocation exceeds requested split size")
    negative_counts = tuple(totals[i] - positive_counts[i] for i in range(3))

    assignments: dict[str, list[str]] = {}
    positive_offset = negative_offset = 0
    for index, name in enumerate(SPLIT_NAMES):
        next_positive = positive_offset + positive_counts[index]
        next_negative = negative_offset + negative_counts[index]
        assignments[name] = sorted(
            positive_ids[positive_offset:next_positive]
            + negative_ids[negative_offset:next_negative]
        )
        positive_offset, negative_offset = next_positive, next_negative

    if positive_offset != len(positive_ids) or negative_offset != len(negative_ids):
        raise AssertionError("Split allocation did not assign every patient")
    verify_zero_patient_overlap(assignments)
    return assignments


def verify_zero_patient_overlap(assignments: dict[str, Iterable[str]]) -> None:
    """Raise if any patient ID appears in more than one split."""
    sets = {name: set(assignments[name]) for name in SPLIT_NAMES}
    missing = set(SPLIT_NAMES) - set(assignments)
    if missing:
        raise ValueError(f"Missing split assignments: {sorted(missing)}")
    overlaps = {
        "train_validation": sets["train"] & sets["validation"],
        "train_test": sets["train"] & sets["test"],
        "validation_test": sets["validation"] & sets["test"],
    }
    present = {name: sorted(values) for name, values in overlaps.items() if values}
    if present:
        raise ValueError(f"Patient overlap detected: {present}")


def split_statistics(
    records: Iterable[PatientMetadata], assignments: dict[str, Iterable[str]]
) -> dict[str, dict[str, float | int]]:
    record_by_id = {record.patient_id: record for record in records}
    statistics: dict[str, dict[str, float | int]] = {}
    for name in SPLIT_NAMES:
        selected = [record_by_id[patient_id] for patient_id in assignments[name]]
        patient_count = len(selected)
        positive_patients = sum(record.has_positive_label for record in selected)
        rows = sum(record.row_count for record in selected)
        positive_rows = sum(record.positive_rows for record in selected)
        statistics[name] = {
            "patients": patient_count,
            "rows": rows,
            "positive_patients": positive_patients,
            "negative_patients": patient_count - positive_patients,
            "positive_rows": positive_rows,
            "negative_rows": rows - positive_rows,
            "positive_row_percentage": round(100 * positive_rows / rows, 6) if rows else 0.0,
        }
    return statistics


def missingness_statistics(
    records: Iterable[PatientMetadata], assignments: dict[str, Iterable[str]]
) -> dict[str, dict[str, dict[str, float | int]]]:
    """Calculate missingness by split. PSV NaN values are treated as missing."""
    record_by_id = {record.patient_id: record for record in records}
    result: dict[str, dict[str, dict[str, float | int]]] = {}
    for name in SPLIT_NAMES:
        counts = Counter()
        missing = Counter()
        for patient_id in assignments[name]:
            for row in read_patient_rows(record_by_id[patient_id].path):
                for feature in CORE_FEATURES:
                    counts[feature] += 1
                    value = row.get(feature, "")
                    if not value or value.lower() == "nan":
                        missing[feature] += 1
        result[name] = {
            feature: {
                "missing_count": missing[feature],
                "total_count": counts[feature],
                "missing_percentage": round(100 * missing[feature] / counts[feature], 6),
            }
            for feature in CORE_FEATURES
        }
    return result


def positive_label_timeline_examples(
    records: Iterable[PatientMetadata], sample_size: int = 10
) -> list[dict[str, int | str]]:
    """Return deterministic examples; labels are observed, never rewritten."""
    examples = []
    for record in sorted(records, key=lambda item: item.patient_id):
        if not record.has_positive_label:
            continue
        rows = read_patient_rows(record.path)
        positive_positions = [index for index, row in enumerate(rows) if int(float(row["SepsisLabel"]))]
        first, last = positive_positions[0], positive_positions[-1]
        examples.append(
            {
                "patient_id": record.patient_id,
                "first_positive_row_index": first,
                "last_positive_row_index": last,
                "first_positive_iculos": int(float(rows[first]["ICULOS"])),
                "last_positive_iculos": int(float(rows[last]["ICULOS"])),
                "record_end_iculos": int(float(rows[-1]["ICULOS"])),
                "positive_readings": len(positive_positions),
                "hours_from_first_positive_to_record_end": int(float(rows[-1]["ICULOS"])) - int(float(rows[first]["ICULOS"])),
            }
        )
        if len(examples) == sample_size:
            break
    return examples


def write_split_artifacts(
    output_dir: Path,
    records: list[PatientMetadata],
    assignments: dict[str, list[str]],
    seed: int,
) -> dict[str, object]:
    """Persist deterministic assignments and derived, machine-readable reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    verify_zero_patient_overlap(assignments)
    for name in SPLIT_NAMES:
        (output_dir / f"{name}_patients.txt").write_text(
            "\n".join(assignments[name]) + "\n", encoding="utf-8"
        )

    summary: dict[str, object] = {
        "seed": seed,
        "strategy": "patient-level stratification by ever-positive SepsisLabel",
        "ratios": dict(zip(SPLIT_NAMES, SPLIT_RATIOS)),
        "dataset_patients": len(records),
        "dataset_rows": sum(record.row_count for record in records),
        "class_distribution": split_statistics(records, assignments),
        "core_feature_missingness": missingness_statistics(records, assignments),
        "temporal_policy": "PSV rows remain in original ICULOS order; no interpolation, rolling features, or temporal imputation is applied.",
        "label_policy": "Original SepsisLabel values are preserved unchanged.",
    }
    (output_dir / "split_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    timelines = positive_label_timeline_examples(records)
    (output_dir / "positive_label_timeline_examples.json").write_text(
        json.dumps(timelines, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def generate_split(
    data_root: Path, output_dir: Path, seed: int = DEFAULT_SEED
) -> dict[str, object]:
    records = load_patient_metadata(data_root)
    assignments = stratified_patient_split(records, seed=seed)
    return write_split_artifacts(output_dir, records, assignments, seed)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    summary = generate_split(
        project_root / "data" / "raw" / "physionet",
        project_root / "data" / "splits",
    )
    print(json.dumps(summary["class_distribution"], indent=2))
