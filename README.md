# 🩺 MediWatch AI: AI-Enabled Real-Time Patient Monitoring & Early Warning System

MediWatch AI is an intelligent clinical ICU telemetry and remote patient monitoring platform that streams multi-parameter vital signs (ECG, PPG/SpO2, Blood Pressure, Respiration Rate, Temperature) and utilizes Machine Learning algorithms on real-world clinical ICU datasets (PhysioNet Challenge 2019) for early anomaly detection, sepsis risk stratification, and real-time clinical alerts.

---

## 🚀 Key Features

- **Real-Time Telemetry Streaming**: High-frequency ECG (Lead II) and PPG wave synthesis using Gaussian wave modeling.
- **AI/ML Early Warning Engine**: Real-time vital anomaly detection and sepsis onset risk scoring.
- **PhysioNet Challenge 2019 Dataset Pipeline**: High-throughput multi-threaded downloader and preprocessing pipeline for 40,336 ICU patient records across Hospital A and Hospital B.
- **Multi-Bed Central Station**: Dynamic patient vital monitoring with acoustic alert feedback.

---

## 📁 Repository Structure

```
├── data/                       # Downloaded PhysioNet ICU patient records (git-ignored)
│   ├── training_setA/          # 20,336 patient records (.psv) from Hospital A
│   └── training_setB/          # 20,000 patient records (.psv) from Hospital B
├── ml_pipeline/                # Machine Learning & Signal Processing
│   ├── download_dataset.py     # Multi-threaded AWS S3 PhysioNet 2019 dataset downloader
│   ├── signal_generator.py     # Synthetic PQRST ECG & PPG wave synthesis
│   └── __init__.py
├── .gitignore                  # Git ignore rules for datasets, cache, and virtualenvs
├── requirements.txt            # Project Python dependencies
└── README.md                   # Project documentation
```

---

## 🛠️ Quick Start Guide

### 1. Prerequisites & Environment Setup
Clone the repository and create a Python virtual environment:

```bash
git clone https://github.com/Shivilyadav/MediWatch-AI-AI-Enabled-Real-Time-Patient-Monitoring-Early-Warning-System.git
cd MediWatch-AI-AI-Enabled-Real-Time-Patient-Monitoring-Early-Warning-System

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Download PhysioNet Dataset
To download the complete 40,336 patient records directly from open AWS S3 storage:

```bash
python ml_pipeline/download_dataset.py
```

---

## 📊 Dataset Attribution

This project uses clinical ICU telemetry from the **PhysioNet / Computing in Cardiology Challenge 2019**:
- *Reyna MA, Josef CS, Jeter R, Shashikumar SP, Moody B, Westover MB, Sharma A, Nemati S, Clifford GD. Early Prediction of Sepsis from Clinical Data: the PhysioNet/Computing in Cardiology Challenge 2019. Crit Care Med. 2020 Jan;48(1):e1-e9.*

---

## 📄 License
This project is licensed under the MIT License.
