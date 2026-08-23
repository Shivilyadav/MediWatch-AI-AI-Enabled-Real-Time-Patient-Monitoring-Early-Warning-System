import asyncio
import os
import sys
import time
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root directory to path for importing ml_pipeline.
# NOTE: ml_inference (imported below) additionally puts the ml_pipeline directory itself on
# sys.path, which is what the final inference module's sibling imports require. Both paths
# are derived from __file__, so launching from the project root or from backend/ both work.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml_pipeline import VitalSignalGenerator

# FINAL ML integration (final-logreg-v1 / stage4-v2). This replaces the old
# PatientAnomalyDetector + model.pkl scoring path; model.pkl is no longer loaded.
# See docs/BACKEND_ML_INTEGRATION.md.
try:  # package-style import when the backend is imported as `backend.main`
    from .ml_inference import (
        HISTORY,
        MIN_HOURS_FOR_FULL_TEMPORAL,
        evaluate,
        get_model,
        model_info,
    )
except ImportError:  # script-style import when uvicorn loads `main:app` inside backend/
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    from ml_inference import (
        HISTORY,
        MIN_HOURS_FOR_FULL_TEMPORAL,
        evaluate,
        get_model,
        model_info,
    )

app = FastAPI(title="Aavishkar Patient Monitor API", version="1.0.0")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the FINAL model once at import so a bad/missing artifact fails fast and loudly
# rather than on the first request.
FINAL_MODEL = get_model()

# In-Memory ICU Patient Roster
PATIENTS_DB = [
    {
        "id": "BED-101",
        "name": "Sarah Connor",
        "age": 48,
        "gender": "Female",
        "admission_type": "ICU Cardiac Post-Op",
        "doctor": "Dr. Vance",
        "generator": VitalSignalGenerator(heart_rate=74, spo2=98, sys_bp=122, dia_bp=81, resp_rate=16, temp=36.9),
    },
    {
        "id": "BED-102",
        "name": "Robert Chen",
        "age": 62,
        "gender": "Male",
        "admission_type": "ARDS / Respiratory Care",
        "doctor": "Dr. Aris",
        "generator": VitalSignalGenerator(heart_rate=92, spo2=93, sys_bp=135, dia_bp=88, resp_rate=22, temp=37.8),
    },
    {
        "id": "BED-103",
        "name": "Elena Rostova",
        "age": 71,
        "gender": "Female",
        "admission_type": "Sepsis Management",
        "doctor": "Dr. Mehta",
        "generator": VitalSignalGenerator(heart_rate=105, spo2=96, sys_bp=108, dia_bp=68, resp_rate=24, temp=38.9),
    },
    {
        "id": "BED-104",
        "name": "David Miller",
        "age": 55,
        "gender": "Male",
        "admission_type": "Telemetry Observation",
        "doctor": "Dr. Vance",
        "generator": VitalSignalGenerator(heart_rate=68, spo2=99, sys_bp=118, dia_bp=78, resp_rate=14, temp=36.6),
    }
]

ALERTS_HISTORY: List[Dict] = []
ACTIVE_WEBSOCKETS: List[WebSocket] = []

# --- Virtual-hour cadence -------------------------------------------------------------
# stage4-v2 features are defined over HOURLY rows, while the generator emits
# instantaneous samples. Committing every 1 Hz sample as an "hour" would mislabel the
# time axis and distort every temporal feature, so the telemetry loop commits one
# representative reading per virtual hour and scores read-only in between.
VIRTUAL_HOUR_SECONDS = 5.0

# Warm-up: give each bed a short synthetic baseline history so the first live prediction
# has populated temporal features instead of an all-imputed cold start. These rows come
# from that bed's OWN generator (same synthetic source as every other reading), are
# strictly in the past, and never cross beds.
WARMUP_HOURS = MIN_HOURS_FOR_FULL_TEMPORAL - 1


def seed_patient_histories() -> None:
    """Populate each bed's history with WARMUP_HOURS synthetic hourly readings."""
    HISTORY.reset()
    for patient in PATIENTS_DB:
        for _ in range(WARMUP_HOURS):
            evaluate(patient["id"], patient["generator"].get_vital_snapshot(),
                     commit=True, explain=False)


seed_patient_histories()

class SimulationRequest(BaseModel):
    bed_id: str
    condition: str  # Normal, Bradycardia, Tachycardia, Arrhythmia, Hypoxia, Fever

class AlertAckRequest(BaseModel):
    alert_id: str

@app.get("/api/model/info")
def get_model_info():
    """Identity and contract of the loaded FINAL model artifact."""
    return model_info()

@app.get("/api/patients")
def get_patients():
    """Returns all monitored patients with their current vital snapshot and ML risk assessment."""
    results = []
    for patient in PATIENTS_DB:
        vitals = patient["generator"].get_vital_snapshot()
        # Read-only: scores against existing history + this snapshot without advancing
        # the virtual clock, so dashboard polling cannot inflate the time axis.
        ml_eval = evaluate(patient["id"], vitals, commit=False, explain=False)

        results.append({
            "id": patient["id"],
            "name": patient["name"],
            "age": patient["age"],
            "gender": patient["gender"],
            "admission_type": patient["admission_type"],
            "doctor": patient["doctor"],
            "vitals": vitals,
            "analysis": ml_eval
        })
    return results

@app.get("/api/patients/{bed_id}")
def get_patient(bed_id: str):
    """Returns detailed profile for a specific bed."""
    for patient in PATIENTS_DB:
        if patient["id"].upper() == bed_id.upper():
            vitals = patient["generator"].get_vital_snapshot()
            # Detail view includes per-feature explanations; still read-only.
            ml_eval = evaluate(patient["id"], vitals, commit=False, explain=True)
            return {
                "id": patient["id"],
                "name": patient["name"],
                "age": patient["age"],
                "gender": patient["gender"],
                "admission_type": patient["admission_type"],
                "doctor": patient["doctor"],
                "vitals": vitals,
                "analysis": ml_eval
            }
    raise HTTPException(status_code=404, detail="Patient bed not found")

@app.post("/api/simulate")
def simulate_condition(req: SimulationRequest):
    """Triggers a physiological event or condition in a patient for clinical simulation."""
    target_patient = None
    for patient in PATIENTS_DB:
        if patient["id"].upper() == req.bed_id.upper():
            target_patient = patient
            break

    if not target_patient:
        raise HTTPException(status_code=404, detail="Patient bed not found")

    target_patient["generator"].set_condition(req.condition)

    # Generate immediate alert if condition is abnormal.
    # A simulated clinical event advances that patient's virtual clock by one hour.
    vitals = target_patient["generator"].get_vital_snapshot()
    ml_eval = evaluate(target_patient["id"], vitals, commit=True, explain=True)

    # `alert_actionable` (HIGH band) gates alert creation. The artifact's own metrics are
    # FPR ~0.59 / precision ~1.5%, so the raw `alert` flag at threshold 0.3606 fires
    # almost constantly. The threshold and risk bands are NOT modified; both flags are
    # reported verbatim in `analysis`.
    if ml_eval["alert_actionable"]:
        alert = {
            "alert_id": f"ALT-{int(time.time() * 1000)}",
            "bed_id": target_patient["id"],
            "patient_name": target_patient["name"],
            "timestamp": time.strftime("%H:%M:%S"),
            "risk_level": ml_eval["risk_level"],
            "flags": [e["feature"] for e in ml_eval.get("explanations", [])
                      if e["direction"] == "increases risk"],
            "vitals": vitals,
            "acknowledged": False,
            "probability": ml_eval["probability"],
            "model_version": ml_eval["model_version"],
            "feature_version": ml_eval["feature_version"],
            "disclaimer": ml_eval["disclaimer"]
        }
        ALERTS_HISTORY.insert(0, alert)

    return {
        "status": "success",
        "bed_id": req.bed_id,
        "new_condition": req.condition,
        "analysis": ml_eval
    }

@app.get("/api/alerts")
def get_alerts():
    """Returns clinical alert log."""
    return ALERTS_HISTORY[:50]

@app.post("/api/alerts/acknowledge")
def acknowledge_alert(req: AlertAckRequest):
    """Marks an alert as acknowledged by clinician."""
    for alert in ALERTS_HISTORY:
        if alert["alert_id"] == req.alert_id:
            alert["acknowledged"] = True
            return {"status": "acknowledged", "alert_id": req.alert_id}
    raise HTTPException(status_code=404, detail="Alert ID not found")

def build_vitals_payload(commit_hour: bool) -> Dict[str, Dict]:
    """Per-bed vitals + FINAL-model analysis for one telemetry vitals tick.

    `commit_hour` is True only on a virtual-hour boundary; otherwise the reading is
    scored without being appended, keeping the hourly time axis honest.
    """
    payload: Dict[str, Dict] = {}
    for patient in PATIENTS_DB:
        bed_id = patient["id"]
        vitals = patient["generator"].get_vital_snapshot()
        payload[bed_id] = {
            "vitals": vitals,
            "analysis": evaluate(bed_id, vitals, commit=commit_hour, explain=False)
        }
    return payload


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    """
    WebSocket streaming endpoint broadcasting real-time multi-patient ECG waves, PPG waves,
    and 1Hz vital telemetry updates to connected dashboards.
    """
    await websocket.accept()
    ACTIVE_WEBSOCKETS.append(websocket)
    start_time = time.time()
    last_vital_tick = 0.0
    last_hour_commit = 0.0

    try:
        while True:
            t = time.time() - start_time

            # Generate 60Hz high-resolution waveform packets for all beds
            waveform_payload = {}
            for patient in PATIENTS_DB:
                bed_id = patient["id"]
                gen = patient["generator"]
                ecg_val = gen.generate_ecg_sample(t)
                ppg_val = gen.generate_ppg_sample(t)

                waveform_payload[bed_id] = {
                    "ecg": round(ecg_val, 4),
                    "ppg": round(ppg_val, 4)
                }

            # Send 1Hz vital snapshots & FINAL-model risk predictions
            send_vitals = False
            vitals_payload = {}
            if (t - last_vital_tick) >= 1.0:
                last_vital_tick = t
                send_vitals = True
                commit_hour = (t - last_hour_commit) >= VIRTUAL_HOUR_SECONDS
                if commit_hour:
                    last_hour_commit = t
                vitals_payload = build_vitals_payload(commit_hour)

            packet = {
                "t": round(t, 3),
                "waveforms": waveform_payload,
                "vitals": vitals_payload if send_vitals else None
            }

            await websocket.send_json(packet)
            # Sleep 16ms to achieve ~60 FPS sampling rate
            await asyncio.sleep(0.016)

    except WebSocketDisconnect:
        ACTIVE_WEBSOCKETS.remove(websocket)
    except Exception:
        if websocket in ACTIVE_WEBSOCKETS:
            ACTIVE_WEBSOCKETS.remove(websocket)

# Mount frontend static directory if present
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
