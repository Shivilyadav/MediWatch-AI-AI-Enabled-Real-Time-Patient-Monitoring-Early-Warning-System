import asyncio
import os
import sys
import time
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root directory to path for importing ml_pipeline
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml_pipeline import VitalSignalGenerator, PatientAnomalyDetector

app = FastAPI(title="Aavishkar Patient Monitor API", version="1.0.0")

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML Anomaly Detector
anomaly_detector = PatientAnomalyDetector()

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

class SimulationRequest(BaseModel):
    bed_id: str
    condition: str  # Normal, Bradycardia, Tachycardia, Arrhythmia, Hypoxia, Fever

class AlertAckRequest(BaseModel):
    alert_id: str

@app.get("/api/patients")
def get_patients():
    """Returns all monitored patients with their current vital snapshot and ML risk assessment."""
    results = []
    for patient in PATIENTS_DB:
        vitals = patient["generator"].get_vital_snapshot()
        ml_eval = anomaly_detector.predict(vitals)
        
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
            ml_eval = anomaly_detector.predict(vitals)
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
    
    # Generate immediate alert if condition is abnormal
    vitals = target_patient["generator"].get_vital_snapshot()
    ml_eval = anomaly_detector.predict(vitals)
    
    if ml_eval["is_anomaly"]:
        alert = {
            "alert_id": f"ALT-{int(time.time() * 1000)}",
            "bed_id": target_patient["id"],
            "patient_name": target_patient["name"],
            "timestamp": time.strftime("%H:%M:%S"),
            "risk_level": ml_eval["risk_level"],
            "flags": ml_eval["detected_flags"],
            "vitals": vitals,
            "acknowledged": False
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

            # Send 1Hz vital snapshots & ML anomaly predictions
            send_vitals = False
            vitals_payload = {}
            if (t - last_vital_tick) >= 1.0:
                last_vital_tick = t
                send_vitals = True
                for patient in PATIENTS_DB:
                    bed_id = patient["id"]
                    gen = patient["generator"]
                    vitals = gen.get_vital_snapshot()
                    ml_eval = anomaly_detector.predict(vitals)
                    
                    vitals_payload[bed_id] = {
                        "vitals": vitals,
                        "analysis": ml_eval
                    }

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
