/**
 * Initial dataset for 5 simulated patients (P001 - P005)
 * P003 is the primary demo patient initialized in a deteriorating state.
 */

import { calculateNEWS2, calculateDerivedVitals } from '../utils/news2';

// Helper to generate 24 hours of synthetic historical data points (every 30 mins)
function generateHistoricalVitals(baseVitals, trend = 'STABLE') {
  const points = [];
  const now = new Date();

  for (let i = 48; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 30 * 60 * 1000);
    const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Calculate historical trend drift factor (0 to 1)
    const factor = (48 - i) / 48;
    
    let hr = baseVitals.heart_rate;
    let spo2 = baseVitals.spo2;
    let rr = baseVitals.respiratory_rate;
    let temp = baseVitals.temperature;
    let sbp = baseVitals.systolic_bp;
    let dbp = baseVitals.diastolic_bp;

    if (trend === 'DETERIORATING') {
      // P003 progression over past 24 hours
      hr = Math.round(75 + factor * (baseVitals.heart_rate - 75) + (Math.random() * 4 - 2));
      spo2 = Math.round(98 - factor * (98 - baseVitals.spo2) + (Math.random() * 2 - 1));
      rr = Math.round(14 + factor * (baseVitals.respiratory_rate - 14) + (Math.random() * 2 - 1));
      temp = parseFloat((36.6 + factor * (baseVitals.temperature - 36.6) + (Math.random() * 0.2 - 0.1)).toFixed(1));
      sbp = Math.round(120 - factor * (120 - baseVitals.systolic_bp) + (Math.random() * 4 - 2));
    } else {
      // Stable variation around base vitals
      hr = Math.round(hr + (Math.random() * 4 - 2));
      spo2 = Math.min(100, Math.max(90, Math.round(spo2 + (Math.random() * 2 - 1))));
      rr = Math.round(rr + (Math.random() * 2 - 1));
      temp = parseFloat((temp + (Math.random() * 0.2 - 0.1)).toFixed(1));
      sbp = Math.round(sbp + (Math.random() * 4 - 2));
    }

    const currentVitals = { heart_rate: hr, spo2, respiratory_rate: rr, temperature: temp, systolic_bp: sbp, diastolic_bp: dbp };
    const news2 = calculateNEWS2(currentVitals);

    points.push({
      timestamp: timeStr,
      isoTime: time.toISOString(),
      heart_rate: hr,
      spo2: spo2,
      respiratory_rate: rr,
      temperature: temp,
      systolic_bp: sbp,
      diastolic_bp: dbp,
      news2_score: news2.totalScore
    });
  }

  return points;
}

const initialP001Vitals = { heart_rate: 72, spo2: 98, respiratory_rate: 14, temperature: 36.8, systolic_bp: 120, diastolic_bp: 78 };
const initialP002Vitals = { heart_rate: 68, spo2: 97, respiratory_rate: 15, temperature: 36.6, systolic_bp: 118, diastolic_bp: 76 };
const initialP003Vitals = { heart_rate: 95, spo2: 95, respiratory_rate: 20, temperature: 37.2, systolic_bp: 110, diastolic_bp: 72 };
const initialP004Vitals = { heart_rate: 76, spo2: 99, respiratory_rate: 13, temperature: 36.7, systolic_bp: 124, diastolic_bp: 80 };
const initialP005Vitals = { heart_rate: 88, spo2: 93, respiratory_rate: 19, temperature: 37.4, systolic_bp: 132, diastolic_bp: 84 };

export const INITIAL_PATIENTS = [
  {
    patient_id: 'P001',
    name: 'Eleanor Vance',
    age: 45,
    ward: 'ICU-A (Bed 02)',
    diagnosis: 'Post-Operative Monitoring',
    admission_duration: '24 hours',
    vitals: initialP001Vitals,
    derived: calculateDerivedVitals(initialP001Vitals),
    risk: {
      score: 0.12,
      level: 'LOW',
      predicted_event: 'Hemodynamically Stable',
      time_horizon: 'Next 24 Hours'
    },
    vital_history: generateHistoricalVitals(initialP001Vitals, 'STABLE'),
    alerts: [],
    last_updated: new Date().toISOString()
  },
  {
    patient_id: 'P002',
    name: 'Marcus Chen',
    age: 58,
    ward: 'Ward 2B (Bed 14)',
    diagnosis: 'Cardiac Observation',
    admission_duration: '18 hours',
    vitals: initialP002Vitals,
    derived: calculateDerivedVitals(initialP002Vitals),
    risk: {
      score: 0.18,
      level: 'LOW',
      predicted_event: 'Stable Rhythm',
      time_horizon: 'Next 24 Hours'
    },
    vital_history: generateHistoricalVitals(initialP002Vitals, 'STABLE'),
    alerts: [],
    last_updated: new Date().toISOString()
  },
  {
    patient_id: 'P003',
    name: 'Arthur Pendelton',
    age: 67,
    ward: 'General Ward (Bed 08)',
    diagnosis: 'Community-Acquired Pneumonia',
    admission_duration: '12 hours',
    vitals: initialP003Vitals,
    derived: calculateDerivedVitals(initialP003Vitals),
    risk: {
      score: 0.45,
      level: 'MEDIUM',
      predicted_event: 'Early Respiratory Deterioration',
      time_horizon: 'Within 12 Hours'
    },
    vital_history: generateHistoricalVitals(initialP003Vitals, 'DETERIORATING'),
    alerts: [
      {
        alert_id: 'ALT-P003-01',
        patient_id: 'P003',
        patient_name: 'Arthur Pendelton',
        severity: 'MEDIUM',
        reason: 'Respiratory rate elevated (20/min) with mild SpO2 drop (95%)',
        risk_score: 0.45,
        timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        status: 'ACTIVE'
      }
    ],
    last_updated: new Date().toISOString()
  },
  {
    patient_id: 'P004',
    name: 'Sophia Martinez',
    age: 34,
    ward: 'Emergency Ward (Bed 04)',
    diagnosis: 'Femur Fracture Post-Fixation',
    admission_duration: '6 hours',
    vitals: initialP004Vitals,
    derived: calculateDerivedVitals(initialP004Vitals),
    risk: {
      score: 0.08,
      level: 'LOW',
      predicted_event: 'Unremarkable Recovery',
      time_horizon: 'Next 24 Hours'
    },
    vital_history: generateHistoricalVitals(initialP004Vitals, 'STABLE'),
    alerts: [],
    last_updated: new Date().toISOString()
  },
  {
    patient_id: 'P005',
    name: 'Robert Sterling',
    age: 72,
    ward: 'ICU-B (Bed 06)',
    diagnosis: 'COPD Exacerbation',
    admission_duration: '36 hours',
    vitals: initialP005Vitals,
    derived: calculateDerivedVitals(initialP005Vitals),
    risk: {
      score: 0.38,
      level: 'MEDIUM',
      predicted_event: 'Chronic Airway Limitation Baseline',
      time_horizon: 'Within 12 Hours'
    },
    vital_history: generateHistoricalVitals(initialP005Vitals, 'STABLE'),
    alerts: [],
    last_updated: new Date().toISOString()
  }
];
