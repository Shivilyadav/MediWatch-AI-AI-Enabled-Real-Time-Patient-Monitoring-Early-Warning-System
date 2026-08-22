import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "ml_pipeline" / "data" / "raw" / "physionet"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


data_split = load_module("mediwatch_data_split", PROJECT_ROOT / "ml_pipeline" / "data_split.py")
preprocessing = load_module("mediwatch_preprocessing", PROJECT_ROOT / "ml_pipeline" / "preprocessing.py")


class LeakageSafeDataPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = data_split.load_patient_metadata(DATA_ROOT)

    def test_no_patient_overlap(self):
        assignments = data_split.stratified_patient_split(self.records, seed=42)
        data_split.verify_zero_patient_overlap(assignments)
        self.assertFalse(set(assignments["train"]) & set(assignments["validation"]))
        self.assertFalse(set(assignments["train"]) & set(assignments["test"]))
        self.assertFalse(set(assignments["validation"]) & set(assignments["test"]))

    def test_same_seed_reproduces_assignments(self):
        self.assertEqual(
            data_split.stratified_patient_split(self.records, seed=42),
            data_split.stratified_patient_split(self.records, seed=42),
        )

    def test_validation_transform_does_not_change_training_statistics(self):
        imputer = preprocessing.TrainingOnlyMedianImputer(("HR", "Temp"))
        imputer.fit([{"HR": 60, "Temp": 36}, {"HR": 80, "Temp": 38}])
        fitted_medians = dict(imputer.medians_)
        transformed = imputer.transform([{"HR": "NaN", "Temp": 50}])
        self.assertEqual(fitted_medians, imputer.medians_)
        self.assertEqual(transformed[0]["HR"], 70.0)
        self.assertEqual(transformed[0]["Temp"], 50.0)

    def test_unseen_rows_transform_without_refit(self):
        imputer = preprocessing.TrainingOnlyMedianImputer(("HR",))
        imputer.fit([{"HR": 55}, {"HR": 75}])
        self.assertEqual(
            imputer.transform([{"HR": None}, {"HR": 90}]),
            [{"HR": 65.0}, {"HR": 90.0}],
        )

    def test_patient_temporal_order_is_intact(self):
        assignments = data_split.stratified_patient_split(self.records, seed=42)
        record_by_id = {record.patient_id: record for record in self.records}
        for patient_id in assignments["validation"][:5] + assignments["test"][:5]:
            hours = [int(float(row["ICULOS"])) for row in data_split.read_patient_rows(record_by_id[patient_id].path)]
            self.assertEqual(hours, sorted(hours))
            self.assertTrue(all(next_hour - hour == 1 for hour, next_hour in zip(hours, hours[1:])))


if __name__ == "__main__":
    unittest.main()
