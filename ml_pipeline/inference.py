"""Phase 7: standalone inference for the final MediWatch sepsis-risk benchmark model.

Self-contained: depends only on numpy + scikit-learn + joblib and this repo's feature
code. No FastAPI, frontend, database, or hardware.

Pipeline:
    RAW HOURLY VITALS
      -> stage4-v2 feature transformation (the EXACT training code, reused)
      -> final model (median impute + standardize + LogisticRegression, from the artifact)
      -> risk PROBABILITY
      -> risk LEVEL (LOW / MODERATE / HIGH)

Feature transformation reuses `engineer_patient_rows_v2` from `feature_engineering_v2.py`
so no feature maths is duplicated here. Raw rows are synthesized in the PhysioNet PSV column
layout with a dummy `SepsisLabel=0`; that dummy label only affects the (ignored) target and
never any feature value, so every provided hour is engineered with its correct causal
features and we read the LAST row's 52-feature vector.

NOT a clinical diagnostic tool. Research/hackathon benchmark only (see docs/FINAL_MODEL.md).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping, Sequence

import joblib
import numpy as np

from feature_engineering import FEATURE_NAMES, CORE_SOURCES
from feature_engineering_v2 import engineer_patient_rows_v2

PIPELINE_ROOT = Path(__file__).resolve().parent
DEFAULT_ARTIFACT = PIPELINE_ROOT / "saved_models" / "final_model_v1.pkl"

# Friendly input name -> PhysioNet PSV column expected by current_core_values().
VITAL_TO_PSV = {
    "heart_rate": "HR",
    "spo2": "O2Sat",
    "respiratory_rate": "Resp",
    "temperature": "Temp",
    "systolic_bp": "SBP",
    "diastolic_bp": "DBP",
}
ACCEPTED_VITALS = tuple(VITAL_TO_PSV) + ("map",)


def _psv_row(reading: Mapping[str, object], hour_index: int) -> dict[str, object]:
    """Convert one friendly hourly reading into a PSV-style raw row.

    Missing/None vitals become "" (treated as missing by the shared code). ICULOS is the
    1-based hour; SepsisLabel is a dummy 0 (affects only the ignored target)."""
    row: dict[str, object] = {}
    for vital, psv in VITAL_TO_PSV.items():
        value = reading.get(vital)
        row[psv] = "" if value is None else value
    map_value = reading.get("map")
    row["MAP"] = "" if map_value is None else map_value
    row["ICULOS"] = hour_index
    row["SepsisLabel"] = 0
    return row


def transform_vitals_to_features(readings: Sequence[Mapping[str, object]]) -> np.ndarray:
    """Raw hourly vitals (chronological) -> the 52-feature vector for the LATEST hour.

    Uses the exact stage4-v2 engineering. Returns a (52,) float array with np.nan for
    features that cannot be computed from the supplied history."""
    if not readings:
        raise ValueError("readings must contain at least one hourly vitals record")
    for reading in readings:
        unknown = set(reading) - set(ACCEPTED_VITALS)
        if unknown:
            raise ValueError(f"unknown vital(s): {sorted(unknown)}; accepted: {list(ACCEPTED_VITALS)}")
    raw_rows = [_psv_row(reading, hour + 1) for hour, reading in enumerate(readings)]
    engineered = engineer_patient_rows_v2("inference", raw_rows)
    if not engineered:  # cannot happen with dummy label, but guard anyway
        raise RuntimeError("feature engineering produced no rows")
    last = engineered[-1]
    return np.array(
        [np.nan if last[name] is None else float(last[name]) for name in FEATURE_NAMES],
        dtype=float,
    )


class SepsisRiskModel:
    """Loads the final artifact and scores raw hourly vitals."""

    def __init__(self, artifact_path: Path | str = DEFAULT_ARTIFACT):
        self.artifact = joblib.load(Path(artifact_path))
        self.model = self.artifact["model"]
        self.features = self.artifact["features"]
        self.threshold = float(self.artifact["threshold"])
        bands = self.artifact["risk_bands"]
        self.moderate_cut = float(bands["moderate_cut"])
        self.high_cut = float(bands["high_cut"])
        self.model_version = self.artifact["model_version"]
        self.feature_version = self.artifact["feature_version"]
        if self.features != FEATURE_NAMES:
            raise ValueError("artifact feature contract does not match feature_engineering.FEATURE_NAMES")

    def risk_level(self, probability: float) -> str:
        if probability >= self.high_cut:
            return "HIGH"
        if probability >= self.moderate_cut:
            return "MODERATE"
        return "LOW"

    def predict(self, readings: Sequence[Mapping[str, object]]) -> dict[str, object]:
        vector = transform_vitals_to_features(readings)
        probability = float(self.model.predict_proba(vector.reshape(1, -1))[:, 1][0])
        present = int(np.count_nonzero(~np.isnan(vector)))
        return {
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "probability": probability,
            "risk_level": self.risk_level(probability),
            "alert": bool(probability >= self.threshold),
            "threshold": self.threshold,
            "risk_bands": {"moderate_cut": self.moderate_cut, "high_cut": self.high_cut},
            "hours_supplied": len(readings),
            "features_present": present,
            "features_total": len(self.features),
            "disclaimer": "Research/hackathon benchmark; NOT a clinical diagnostic tool.",
        }

    def explain(self, readings: Sequence[Mapping[str, object]], top_k: int = 8) -> list[dict[str, object]]:
        """Linear-model feature attributions for the latest hour (log-odds contributions).

        For LogisticRegression inside the Pipeline: contribution_i = coef_i * scaled_value_i,
        where scaled_value is the feature after the artifact's median-imputation + scaling.
        This is the linear analogue of a SHAP breakdown; contributions sum (with the
        intercept) to the predicted log-odds."""
        vector = transform_vitals_to_features(readings).reshape(1, -1)
        steps = self.model.named_steps
        imputed = steps["imputer"].transform(vector)
        scaled = steps["scaler"].transform(imputed)
        coef = steps["model"].coef_[0]
        contributions = scaled[0] * coef
        order = np.argsort(-np.abs(contributions))[:top_k]
        raw = vector[0]
        result = []
        for idx in order:
            result.append({
                "feature": self.features[idx],
                "raw_value": None if math.isnan(raw[idx]) else round(float(raw[idx]), 4),
                "was_imputed": bool(math.isnan(raw[idx])),
                "log_odds_contribution": round(float(contributions[idx]), 4),
                "direction": "increases risk" if contributions[idx] > 0 else "decreases risk",
            })
        return result


def load_default_model() -> SepsisRiskModel:
    return SepsisRiskModel(DEFAULT_ARTIFACT)
