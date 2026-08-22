"""Fit Stage 2 preprocessing parameters from train patients only."""

from pathlib import Path

from data_split import CORE_FEATURES, load_patient_metadata, read_patient_rows
from preprocessing import TrainingOnlyMedianImputer


def patient_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rows_for_patients(record_by_id, ids):
    for patient_id in ids:
        yield from read_patient_rows(record_by_id[patient_id].path)


def main() -> None:
    pipeline_root = Path(__file__).resolve().parent
    data_root = pipeline_root / "data" / "raw" / "physionet"
    splits_dir = pipeline_root / "data" / "splits"
    records = load_patient_metadata(data_root)
    record_by_id = {record.patient_id: record for record in records}

    imputer = TrainingOnlyMedianImputer(CORE_FEATURES)
    train_ids = patient_ids(splits_dir / "train_patients.txt")
    imputer.fit(rows_for_patients(record_by_id, train_ids))
    imputer.save(splits_dir / "preprocessing_params.json")

    # Exercise transform-only paths without creating modified copies of raw PSV data.
    for split_name in ("validation", "test"):
        ids = patient_ids(splits_dir / f"{split_name}_patients.txt")
        imputer.transform(rows_for_patients(record_by_id, ids))
    print(f"Saved training-only parameters for {len(CORE_FEATURES)} features.")


if __name__ == "__main__":
    main()
