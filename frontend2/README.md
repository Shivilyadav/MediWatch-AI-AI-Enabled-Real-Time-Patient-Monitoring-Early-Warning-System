# MediWatch AI — Real-Time Patient Monitoring & Early Warning System

**Member 5 — UI/UX Designer + Patient Simulation Engineer**

MediWatch AI is a clinical-grade hospital command center frontend and real-time patient physiological simulator built with **React, Vite, Tailwind CSS, Recharts, Lucide React, and React Context**.

---

## Key Features

1. **Hospital Command Center Dashboard (`/`)**:
   - Dynamic KPI summary cards (Total Patients, Normal, Medium Risk, High/Critical Risk, Active Alerts).
   - Real-time patient grid featuring 5 simulated beds (`P001` - `P005`).
   - Active Alerts Queue with clinical rationale and 1-click **ACKNOWLEDGE** action.

2. **Patient Detail Clinical View (`/patient/:patientId`)**:
   - Animated **AI Deterioration Risk Score Gauge** (0–100%) with level transitions (LOW, MEDIUM, HIGH, CRITICAL).
   - Predicted event & time horizon estimation.
   - Smooth **Recharts 24-hour vitals trends** (Heart Rate, SpO2, Respiratory Rate, Temperature, Blood Pressure).
   - **SHAP Feature Attribution Breakdown** ("Why is this patient at risk?") with dynamic horizontal contribution bars.
   - **NEWS2 Progression Timeline** with threshold zones (Low, Medium, High).
   - Complete **Alert Audit History** with acknowledgment status.

3. **Interactive Patient Simulator (`/simulator`)**:
   - 5 Physiological Scenarios: `NORMAL`, `DETERIORATING` (Primary Demo), `SEPSIS_ONSET`, `RESPIRATORY_FAILURE`, `RECOVERING`.
   - Speed Controls: `1x`, `2x`, `5x`, `10x`.
   - Smooth vital interpolation, bounded physiological noise, and alert suppression engine.

4. **Mobile Alert Response View (`/mobile-alert/:alertId`)**:
   - Native-feeling mobile UI for emergency alerts with instant vital snapshots.

5. **Dual Mode Architecture**:
   - **Demo Mode**: 100% browser-based execution with zero backend dependency.
   - **Live Mode**: Integrates with FastAPI REST endpoints & WebSocket (`ws://localhost:8000/ws/vitals-stream`) with automatic timeout and fallback.

---

## Installation & Setup

### Prerequisites
- Node.js (v18+)
- npm or yarn

### 1. Install Dependencies
```bash
cd mediwatch-ai
npm install
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```env
VITE_DEMO_MODE=true
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/vitals-stream
```

### 3. Run Local Development Server
```bash
npm run dev
```

The application will be accessible at: `http://localhost:5173`

---

## Hackathon Demo Step-by-Step Flow

1. **Step 1 — Open Command Center**: Navigate to `/`. Observe 5 patient cards. Patients P001, P002, P004 are Normal; P003 is in Medium Risk state (45%).
2. **Step 2 — Launch Simulator**: Click **Patient Simulator** in header. Select Patient **P003**, Scenario **Gradual Deterioration**, and Speed **5x**. Click **START SIMULATION**.
3. **Step 3 — Watch Real-Time Risk Progression**: Return to Command Center or stay on Simulator. Watch P003 risk progress smoothly:
   - `45% (MEDIUM)` → `62% (MEDIUM)` → `78% (HIGH)` → `88% (CRITICAL)`
4. **Step 4 — Automatic Alert Trigger**: Observe a new CRITICAL Alert appearing at the top of the Active Alert Queue.
5. **Step 5 — Inspect Patient Detail**: Click **P003**. Observe the animated Risk Gauge (88%), Recharts trends, NEWS2 progression, and SHAP factor breakdown ("Respiratory Rate 28/min (+0.34), SpO2 88% (+0.32)").
6. **Step 6 — Acknowledge Alert**: Click **ACKNOWLEDGE ALERT**. Observe immediate UI update to ACKNOWLEDGED.
7. **Step 7 — Simulate Clinical Recovery**: Go to Simulator, switch P003 scenario to **RECOVERING**. Watch vitals and risk score gradually stabilize back to normal bounds.

---

## Medical Safety Disclaimer
> **Prototype — Simulated data only. Not for clinical diagnosis or real patient care.**
