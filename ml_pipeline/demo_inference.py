"""Phase 8: standalone demo of the MediWatch sepsis-risk benchmark model.

Runs WITHOUT the FastAPI backend, the frontend, a database, or any hardware. It takes a
patient's available raw hourly vitals and prints the model version, risk probability, risk
level, and the threshold used, plus the top log-odds feature contributions.

Usage:
    python demo_inference.py                      # built-in illustrative patients
    python demo_inference.py --patient training_setA/p000018 --hours 12
    python demo_inference.py --patient <id>       # last 24 hours of a real PhysioNet record

*** RESEARCH / HACKATHON BENCHMARK ONLY -- NOT A CLINICAL DIAGNOSTIC TOOL. ***
The underlying model is not deployment-ready (see docs/FINAL_MODEL.md): at the required
sensitivity it raises many false alarms (precision ~1.5%). Do not use for patient care.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from feature_engineering import read_psv, as_number
from inference import SepsisRiskModel, VITAL_TO_PSV, DEFAULT_ARTIFACT

PIPELINE_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PIPELINE_ROOT / "data" / "raw" / "physionet"

DISCLAIMER = (
    "*** RESEARCH / HACKATHON BENCHMARK ONLY - NOT A CLINICAL DIAGNOSTIC TOOL. ***\n"
    "*** Not deployment-ready; high false-alarm rate. Do not use for patient care. ***"
)

# Illustrative synthetic patients (fabricated vitals, not real records).
SYNTHETIC = {
    "A: stable adult (6h)": [
        {"heart_rate": 78, "spo2": 98, "respiratory_rate": 16, "temperature": 36.8, "systolic_bp": 122, "diastolic_bp": 80},
        {"heart_rate": 80, "spo2": 98, "respiratory_rate": 16, "temperature": 36.9, "systolic_bp": 120, "diastolic_bp": 79},
        {"heart_rate": 76, "spo2": 99, "respiratory_rate": 15, "temperature": 36.7, "systolic_bp": 124, "diastolic_bp": 81},
        {"heart_rate": 79, "spo2": 98, "respiratory_rate": 16, "temperature": 36.8, "systolic_bp": 121, "diastolic_bp": 80},
        {"heart_rate": 77, "spo2": 98, "respiratory_rate": 15, "temperature": 36.9, "systolic_bp": 123, "diastolic_bp": 79},
        {"heart_rate": 80, "spo2": 98, "respiratory_rate": 16, "temperature": 36.8, "systolic_bp": 120, "diastolic_bp": 78},
    ],
    "B: deteriorating (6h)": [
        {"heart_rate": 88, "spo2": 97, "respiratory_rate": 18, "temperature": 37.2, "systolic_bp": 118, "diastolic_bp": 76},
        {"heart_rate": 96, "spo2": 96, "respiratory_rate": 20, "temperature": 37.6, "systolic_bp": 112, "diastolic_bp": 70},
        {"heart_rate": 105, "spo2": 95, "respiratory_rate": 22, "temperature": 38.1, "systolic_bp": 106, "diastolic_bp": 64},
        {"heart_rate": 114, "spo2": 93, "respiratory_rate": 25, "temperature": 38.6, "systolic_bp": 98, "diastolic_bp": 58},
        {"heart_rate": 122, "spo2": 91, "respiratory_rate": 28, "temperature": 39.0, "systolic_bp": 92, "diastolic_bp": 54},
        {"heart_rate": 130, "spo2": 90, "respiratory_rate": 30, "temperature": 39.2, "systolic_bp": 88, "diastolic_bp": 50},
    ],
    "C: sparse (2h, few vitals)": [
        {"heart_rate": 110},
        {"heart_rate": 118, "spo2": 92},
    ],
}


def load_real_patient(patient_id: str, hours: int) -> list[dict]:
    path = DATA_ROOT / f"{patient_id}.psv"
    if not path.exists():
        raise SystemExit(f"patient record not found: {path}")
    rows = read_psv(path)
    tail = rows[-hours:] if hours and hours < len(rows) else rows
    readings = []
    for row in tail:
        reading = {v: as_number(row[psv]) for v, psv in VITAL_TO_PSV.items()}
        reading["map"] = as_number(row.get("MAP"))
        readings.append({k: v for k, v in reading.items() if v is not None})
    return readings


def show(model: SepsisRiskModel, label: str, readings: list[dict]):
    result = model.predict(readings)
    print(f"\nPatient [{label}]")
    print(f"  model_version   : {result['model_version']}  (feature {result['feature_version']})")
    print(f"  hours supplied  : {result['hours_supplied']}   features present: "
          f"{result['features_present']}/{result['features_total']}")
    print(f"  risk probability: {result['probability']:.4f}")
    print(f"  risk level      : {result['risk_level']}   alert(>= {result['threshold']:.4f}): {result['alert']}")
    print(f"  risk bands      : LOW < {result['risk_bands']['moderate_cut']:.4f} "
          f"<= MODERATE < {result['risk_bands']['high_cut']:.4f} <= HIGH")
    print("  top feature contributions (log-odds):")
    for item in model.explain(readings, top_k=6):
        value = "missing(imputed)" if item["was_imputed"] else item["raw_value"]
        print(f"    {item['feature']:26s} {item['log_odds_contribution']:+.4f}  "
              f"({item['direction']}; value={value})")


def main():
    parser = argparse.ArgumentParser(description="Standalone MediWatch sepsis-risk demo")
    parser.add_argument("--patient", help="PhysioNet record id, e.g. training_setA/p000018")
    parser.add_argument("--hours", type=int, default=24, help="use the last N hours (default 24)")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    args = parser.parse_args()

    print(DISCLAIMER)
    model = SepsisRiskModel(args.artifact)

    if args.patient:
        readings = load_real_patient(args.patient, args.hours)
        show(model, f"real:{args.patient} (last {len(readings)}h)", readings)
    else:
        for label, readings in SYNTHETIC.items():
            show(model, label, readings)

    print(f"\n{DISCLAIMER}")


if __name__ == "__main__":
    main()
