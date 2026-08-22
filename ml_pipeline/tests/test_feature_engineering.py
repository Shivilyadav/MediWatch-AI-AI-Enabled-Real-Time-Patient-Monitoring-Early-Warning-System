import importlib.util
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "ml_pipeline" / "feature_engineering.py"
spec = importlib.util.spec_from_file_location("mediwatch_feature_engineering", MODULE_PATH)
feature_engineering = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["mediwatch_feature_engineering"] = feature_engineering
spec.loader.exec_module(feature_engineering)


def row(hour, hr, spo2=98, rr=16, temp=37, sbp=120, dbp=80, map_value=93, label=0):
    return {
        "ICULOS": str(hour), "HR": str(hr), "O2Sat": str(spo2), "Resp": str(rr),
        "Temp": str(temp), "SBP": str(sbp), "DBP": str(dbp), "MAP": str(map_value),
        "SepsisLabel": str(label),
    }


class FeatureEngineeringTests(unittest.TestCase):
    def test_patient_boundary_resets_history(self):
        first = feature_engineering.engineer_patient_rows("A", [row(1, 50), row(2, 60)])
        second = feature_engineering.engineer_patient_rows("B", [row(1, 200)])
        self.assertEqual(first[1]["heart_rate_change_1h"], 10.0)
        self.assertIsNone(second[0]["heart_rate_change_1h"])

    def test_future_values_do_not_change_past_features(self):
        base = [row(1, 60), row(2, 70), row(3, 80), row(4, 90), row(5, 100)]
        altered = base[:-1] + [row(5, 999)]
        original_features = feature_engineering.engineer_patient_rows("A", base)[3]
        altered_features = feature_engineering.engineer_patient_rows("A", altered)[3]
        self.assertEqual(original_features, altered_features)

    def test_one_hour_change(self):
        rows = feature_engineering.engineer_patient_rows("A", [row(1, 60), row(2, 68)])
        self.assertEqual(rows[1]["heart_rate_change_1h"], 8.0)

    def test_four_hour_change_and_trailing_statistics(self):
        rows = feature_engineering.engineer_patient_rows("A", [row(i + 1, 10 * (i + 1)) for i in range(5)])
        self.assertEqual(rows[4]["heart_rate_change_4h"], 40.0)
        self.assertEqual(rows[3]["heart_rate_mean_4h"], 25.0)
        self.assertEqual(rows[3]["heart_rate_min_4h"], 10.0)
        self.assertEqual(rows[3]["heart_rate_max_4h"], 40.0)
        self.assertEqual(rows[3]["heart_rate_trend_4h"], 10.0)

    def test_derived_vitals_and_map_fallback(self):
        values = feature_engineering.engineer_patient_rows("A", [row(1, 90, spo2=96, rr=12, sbp=120, dbp=60, map_value="NaN")])[0]
        self.assertEqual(values["map"], 80.0)
        self.assertEqual(values["pulse_pressure"], 60.0)
        self.assertEqual(values["shock_index"], 0.75)
        self.assertEqual(values["spo2_rr_ratio"], 8.0)

    def test_approved_target_alignment(self):
        raw = [row(index + 1, 80, label=1 if index >= 3 else 0) for index in range(12)]
        engineered = feature_engineering.engineer_patient_rows("A", raw)
        self.assertEqual([item["target"] for item in engineered], [0, 0, 0, 1, 1, 1, 1, 1, 1])
        self.assertEqual(len(engineered), 9)  # Rows at first_positive + 6 and after are excluded.

    def test_schema_excludes_target_leakage(self):
        schema = feature_engineering.feature_schema()
        names = [item["name"] for item in schema["features"]]
        self.assertNotIn("SepsisLabel", names)
        self.assertNotIn("target", names)
        self.assertNotIn("SepsisLabel", feature_engineering.FEATURE_NAMES)


if __name__ == "__main__":
    unittest.main()
