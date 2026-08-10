import os
import pickle
import numpy as np
import pandas as pd

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "model.pkl"))

class PatientAnomalyDetector:
    """
    ML Anomaly Detector & Risk Scoring engine for patient telemetry.
    Combines rule-based physiological indicators with a trained RandomForest model from PhysioNet 2019 data.
    """
    
    def __init__(self):
        self.ml_model = None
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    self.ml_model = pickle.load(f)
                print(f"[ML Engine] Loaded pre-trained PhysioNet model from {MODEL_PATH}")
            except Exception as e:
                print(f"[ML Engine] Could not load model file: {e}")

        # Baseline reference ranges (Normal Adult ICU standards)
        self.normal_ranges = {
            "heart_rate": (60, 100),
            "spo2": (95, 100),
            "sys_bp": (90, 120),
            "dia_bp": (60, 80),
            "map": (70, 100),
            "resp_rate": (12, 20),
            "temp": (36.5, 37.5)
        }

    def predict(self, vitals: dict) -> dict:
        """
        Calculates patient anomaly score (0-100), risk status, and flags specific clinical abnormalities.
        """
        hr = vitals.get("heart_rate", 70)
        spo2 = vitals.get("spo2", 98)
        sys_bp = vitals.get("sys_bp", 120)
        dia_bp = vitals.get("dia_bp", 80)
        map_val = vitals.get("map", 90)
        rr = vitals.get("resp_rate", 16)
        temp = vitals.get("temp", 37.0)
        
        detected_flags = []
        anomaly_score = 0.0

        # Heart rate evaluation
        if hr < 50:
            anomaly_score += 35
            detected_flags.append("SEVERE_BRADYCARDIA")
        elif hr < 60:
            anomaly_score += 15
            detected_flags.append("BRADYCARDIA")
        elif hr > 140:
            anomaly_score += 40
            detected_flags.append("SEVERE_TACHYCARDIA")
        elif hr > 100:
            anomaly_score += 20
            detected_flags.append("TACHYCARDIA")

        # SpO2 evaluation (Oxygen saturation)
        if spo2 < 85:
            anomaly_score += 50
            detected_flags.append("CRITICAL_HYPOXIA")
        elif spo2 < 92:
            anomaly_score += 30
            detected_flags.append("HYPOXIA")
        elif spo2 < 95:
            anomaly_score += 10
            detected_flags.append("MILD_DESATURATION")

        # Blood pressure evaluation
        if sys_bp < 90 or map_val < 65:
            anomaly_score += 30
            detected_flags.append("HYPOTENSION")
        elif sys_bp > 160 or dia_bp > 100:
            anomaly_score += 25
            detected_flags.append("HYPERTENSIVE_CRISIS")

        # Respiration evaluation
        if rr < 10:
            anomaly_score += 25
            detected_flags.append("BRADYPNEA")
        elif rr > 24:
            anomaly_score += 20
            detected_flags.append("TACHYPNEA")

        # Temperature evaluation
        if temp > 38.5:
            anomaly_score += 20
            detected_flags.append("HYPERTHERMIA_FEVER")
        elif temp < 35.5:
            anomaly_score += 25
            detected_flags.append("HYPOTHERMIA")

        # Condition specific flags
        condition = vitals.get("condition", "Normal")
        if "arrhythmia" in condition.lower():
            anomaly_score += 30
            detected_flags.append("IRREGULAR_ECG_ARRHYTHMIA")

        # ML Model Inference (if model is loaded)
        sepsis_prob = 0.0
        if self.ml_model is not None:
            try:
                # Features: ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp"]
                features = pd.DataFrame([{
                    "HR": hr,
                    "O2Sat": spo2,
                    "Temp": temp,
                    "SBP": sys_bp,
                    "MAP": map_val,
                    "DBP": dia_bp,
                    "Resp": rr
                }])
                prob = self.ml_model.predict_proba(features)[0][1]
                sepsis_prob = round(float(prob), 4)
                if sepsis_prob > 0.4:
                    anomaly_score += sepsis_prob * 30
                    detected_flags.append(f"PHYSIONET_SEPSIS_RISK_({int(sepsis_prob*100)}%)")
            except Exception:
                pass

        # Cap anomaly score at 100
        risk_score = min(100, int(round(anomaly_score)))

        # Assign risk tier
        if risk_score >= 60:
            risk_level = "CRITICAL"
        elif risk_score >= 35:
            risk_level = "HIGH"
        elif risk_score >= 15:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "sepsis_probability": sepsis_prob,
            "detected_flags": detected_flags,
            "is_anomaly": risk_score >= 35
        }
