"""Backend bridge to the FINAL MediWatch sepsis-risk model (final-logreg-v1 / stage4-v2).

This module is the ONLY place the backend talks to the ML pipeline. It does three
things and nothing more:

  1. Resolves the sibling-import problem so `ml_pipeline/inference.py` can be
     imported regardless of the launch directory (project root OR backend/).
  2. Keeps ONE loaded copy of the final artifact (singleton).
  3. Maintains per-bed, isolated, chronological hourly history and marshals it
     into the existing inference API.

Deliberate non-goals (see docs/BACKEND_ML_INTEGRATION_PLAN.md):
  * No feature maths lives here. The 52 stage4-v2 features are produced ONLY by
    `ml_pipeline.inference.transform_vitals_to_features` -> `engineer_patient_rows_v2`.
  * The old `PatientAnomalyDetector` / `model.pkl` path is NOT used for scoring.
  * The artifact's threshold and risk bands are read from the artifact and never
    overridden.

The score is a research/hackathon benchmark, NOT a clinical diagnostic.
"""

from __future__ import annotations

import os
import sys
import threading
from collections import deque
from typing import Deque, Dict, List, Mapping, Optional

# --------------------------------------------------------------------------------------
# Import path resolution (plan section 6)
# --------------------------------------------------------------------------------------
# ml_pipeline/inference.py and feature_engineering_v2.py use bare sibling imports
# (`from feature_engineering import ...`). Those resolve only when the ml_pipeline
# DIRECTORY ITSELF is on sys.path. backend/main.py historically added only the project
# root, which is enough for `from ml_pipeline import ...` but NOT for inference.py.
#
# Both paths are derived from __file__ (never the current working directory), so this
# works identically whether uvicorn is launched from the project root or from backend/.

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
ML_PIPELINE_DIR = os.path.join(PROJECT_ROOT, "ml_pipeline")


def _ensure_on_sys_path(path: str) -> None:
    """Idempotently put `path` at the front of sys.path."""
    if path not in sys.path:
        sys.path.insert(0, path)


# Order matters only in that both must be present before importing inference.
_ensure_on_sys_path(PROJECT_ROOT)
_ensure_on_sys_path(ML_PIPELINE_DIR)

# Imported for its side-effect-free API. This is the FINAL model path.
from inference import (  # noqa: E402  (import must follow the sys.path fix)
    ACCEPTED_VITALS,
    DEFAULT_ARTIFACT,
    SepsisRiskModel,
)

# --------------------------------------------------------------------------------------
# Vital-name adaptation (plan section 3)
# --------------------------------------------------------------------------------------
# VitalSignalGenerator emits sys_bp/dia_bp/resp_rate/temp; inference.py accepts
# systolic_bp/diastolic_bp/respiratory_rate/temperature. `condition` is UI metadata and
# is not a model input, so it is dropped.

GENERATOR_TO_INFERENCE: Dict[str, str] = {
    "heart_rate": "heart_rate",
    "spo2": "spo2",
    "sys_bp": "systolic_bp",
    "dia_bp": "diastolic_bp",
    "resp_rate": "respiratory_rate",
    "temp": "temperature",
    "map": "map",
}

# Fields present on a generator snapshot that are intentionally NOT model inputs.
NON_MODEL_KEYS = frozenset({"condition"})

# stage4-v2 looks back at most to t-4 (change_4h) over a 4-hour rolling window, so 5
# hourly rows fully populate the current hour's temporal features. We retain more for
# headroom, but the buffer is hard-capped so memory stays bounded.
MIN_HOURS_FOR_FULL_TEMPORAL = 5
DEFAULT_MAX_HISTORY_HOURS = 72


def adapt_snapshot(vitals: Mapping[str, object]) -> Dict[str, object]:
    """Generator snapshot -> one inference-ready hourly reading.

    Pure key renaming: no values are altered, derived, or invented. Unknown keys raise,
    so a future generator change surfaces loudly instead of silently dropping a vital.
    """
    reading: Dict[str, object] = {}
    for key, value in vitals.items():
        if key in NON_MODEL_KEYS:
            continue
        target = GENERATOR_TO_INFERENCE.get(key)
        if target is None:
            raise ValueError(
                f"unmapped vital '{key}' from generator snapshot; "
                f"known keys: {sorted(GENERATOR_TO_INFERENCE)} "
                f"(non-model: {sorted(NON_MODEL_KEYS)})"
            )
        reading[target] = value
    unknown = set(reading) - set(ACCEPTED_VITALS)
    if unknown:  # guards against drift in inference.ACCEPTED_VITALS
        raise ValueError(f"adapted reading has vitals inference rejects: {sorted(unknown)}")
    return reading


# --------------------------------------------------------------------------------------
# Per-patient history (plan section 3)
# --------------------------------------------------------------------------------------


class PatientHistoryStore:
    """Isolated, chronological, bounded hourly history keyed by bed id.

    Guarantees:
      * ISOLATION  - each bed owns its own deque; readings are never shared or merged.
      * CHRONOLOGY - append-only at the tail; nothing is inserted into the past.
      * NO FUTURE  - `window()` returns only what has already been appended, so a
                     prediction can never see an observation later than the current one.
      * BOUNDED    - the deque's maxlen evicts the oldest hour, so memory is capped.
    """

    def __init__(self, max_hours: int = DEFAULT_MAX_HISTORY_HOURS):
        if max_hours < MIN_HOURS_FOR_FULL_TEMPORAL:
            raise ValueError(
                f"max_hours must be >= {MIN_HOURS_FOR_FULL_TEMPORAL} to populate "
                "stage4-v2 temporal features"
            )
        self.max_hours = int(max_hours)
        self._histories: Dict[str, Deque[Dict[str, object]]] = {}
        self._lock = threading.Lock()

    def _bucket(self, bed_id: str) -> Deque[Dict[str, object]]:
        history = self._histories.get(bed_id)
        if history is None:
            history = deque(maxlen=self.max_hours)
            self._histories[bed_id] = history
        return history

    def append(self, bed_id: str, reading: Mapping[str, object]) -> List[Dict[str, object]]:
        """Commit one hourly reading for `bed_id`; return that bed's window (copy)."""
        with self._lock:
            history = self._bucket(bed_id)
            history.append(dict(reading))  # copy: caller cannot mutate stored history
            return [dict(row) for row in history]

    def window(self, bed_id: str) -> List[Dict[str, object]]:
        """That bed's readings so far, oldest -> newest. Empty if never seen."""
        with self._lock:
            return [dict(row) for row in self._histories.get(bed_id, ())]

    def hours(self, bed_id: str) -> int:
        with self._lock:
            return len(self._histories.get(bed_id, ()))

    def beds(self) -> List[str]:
        with self._lock:
            return list(self._histories)

    def reset(self, bed_id: Optional[str] = None) -> None:
        """Clear one bed's history, or all beds when `bed_id` is None (tests/demo reset)."""
        with self._lock:
            if bed_id is None:
                self._histories.clear()
            else:
                self._histories.pop(bed_id, None)


# --------------------------------------------------------------------------------------
# Model singleton
# --------------------------------------------------------------------------------------

_model: Optional[SepsisRiskModel] = None
_model_lock = threading.Lock()

# One shared store for the process; isolation is per-bed inside it.
HISTORY = PatientHistoryStore()

ML_DISCLAIMER = (
    "Research/hackathon benchmark only. NOT a clinical diagnostic tool and not "
    "deployment-ready; do not use for patient care decisions."
)


def get_model() -> SepsisRiskModel:
    """Load `final_model_v1.pkl` once and reuse it (thread-safe, double-checked)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SepsisRiskModel(DEFAULT_ARTIFACT)
    return _model


def model_info() -> Dict[str, object]:
    """Artifact identity/contract, straight from the loaded artifact."""
    model = get_model()
    return {
        "model_version": model.model_version,
        "feature_version": model.feature_version,
        "threshold": model.threshold,
        "risk_bands": {"moderate_cut": model.moderate_cut, "high_cut": model.high_cut},
        "features_total": len(model.features),
        "artifact_path": str(DEFAULT_ARTIFACT),
        "disclaimer": ML_DISCLAIMER,
    }


# --------------------------------------------------------------------------------------
# Evaluation entry point
# --------------------------------------------------------------------------------------
# Alert policy note: the artifact's own metrics are FPR ~0.59 / precision ~1.5%, so
# `alert` (probability >= 0.3606) fires constantly. We surface the model's raw `alert`
# untouched AND a separate `alert_actionable` (HIGH band) used to decide whether to
# create a clinical alert entry. The threshold and bands themselves are NOT changed.


def evaluate(
    bed_id: str,
    vitals: Mapping[str, object],
    commit: bool = True,
    explain: bool = True,
    top_k: int = 8,
) -> Dict[str, object]:
    """Score one patient using the final model over that patient's own history.

    `commit=True` treats this snapshot as the patient's next virtual hour and appends it
    to their history. `commit=False` scores against the existing window plus this
    snapshot without persisting it (used by read-only REST reads that must not advance
    the clock).
    """
    reading = adapt_snapshot(vitals)

    if commit:
        window = HISTORY.append(bed_id, reading)
    else:
        window = HISTORY.window(bed_id)
        window.append(reading)

    model = get_model()
    result = dict(model.predict(window))  # copy so we can add backend fields

    if explain:
        result["explanations"] = model.explain(window, top_k=top_k)

    # Backend-added context. Model-owned keys above are left exactly as returned.
    result["bed_id"] = bed_id
    result["history_hours"] = len(window)
    result["history_sufficient"] = len(window) >= MIN_HOURS_FOR_FULL_TEMPORAL
    result["alert_actionable"] = bool(result["risk_level"] == "HIGH")
    result["disclaimer"] = ML_DISCLAIMER
    result["clinical_use"] = False
    return result


def reset_history(bed_id: Optional[str] = None) -> None:
    """Convenience passthrough for tests and demo restarts."""
    HISTORY.reset(bed_id)
