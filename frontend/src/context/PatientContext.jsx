/**
 * PatientContext — Global Application State Management
 * Coordinates live patient vitals, simulation engine execution, active alerts,
 * WebSocket telemetry, and API acknowledgments.
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { INITIAL_PATIENTS } from '../simulator/demoData';
import { runSimulationTick } from '../simulator/patientSimulator';
import { SCENARIOS } from '../simulator/scenarios';
import { acknowledgeAlert as apiAcknowledgeAlert } from '../services/api';
import { VitalWebSocketClient } from '../services/websocket';

const PatientContext = createContext(null);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8021';

/**
 * Transform one backend patient object (from GET /api/patients or a WS vitals packet)
 * into the shape the frontend components expect.
 *
 * Backend patient shape:
 *   { id, name, age, gender, admission_type, doctor, vitals, analysis }
 *
 * Frontend patient shape:
 *   { patient_id, name, age, ward, diagnosis, vitals, derived, risk, vital_history, alerts, last_updated }
 *
 * The backend generator snapshot emits:
 *   heart_rate, spo2, sys_bp, dia_bp, resp_rate, temp, map, condition
 * We normalise these to the frontend component convention here.
 */
function backendPatientToFrontend(backendPatient, existingFrontendPatient = null) {
  const { id, name, age, gender, admission_type, doctor, vitals: rawVitals, analysis } = backendPatient;

  // Normalise backend vital key names to what the frontend components expect.
  const vitals = {
    heart_rate:       rawVitals?.heart_rate      ?? null,
    spo2:             rawVitals?.spo2             ?? null,
    respiratory_rate: rawVitals?.resp_rate        ?? rawVitals?.respiratory_rate ?? null,
    temperature:      rawVitals?.temp             ?? rawVitals?.temperature ?? null,
    systolic_bp:      rawVitals?.sys_bp           ?? rawVitals?.systolic_bp ?? null,
    diastolic_bp:     rawVitals?.dia_bp           ?? rawVitals?.diastolic_bp ?? null,
  };

  // Build a risk object from the backend analysis (the ML model is the source of truth).
  // analysis.risk_level is LOW / MODERATE / HIGH (from the artifact's risk_bands).
  // IMPORTANT: WS telemetry packets use explain=False and therefore carry no explanations.
  // Preserve any explanations already loaded from the REST detail endpoint (explain=True).
  const incomingExplanations = analysis?.explanations;
  const risk = {
    score:              analysis?.probability         ?? 0,
    level:              analysis?.risk_level          ?? 'LOW',
    // Keep existing explanations when the WS packet has none (explain=False on telemetry).
    explanations:       (incomingExplanations && incomingExplanations.length > 0)
                          ? incomingExplanations
                          : (existingFrontendPatient?.risk?.explanations ?? []),
    alert:              analysis?.alert               ?? false,
    alert_actionable:   analysis?.alert_actionable    ?? false,
    history_sufficient: analysis?.history_sufficient  ?? false,
    disclaimer:         analysis?.disclaimer          ?? '',
  };

  // Append this reading to the existing vital_history (if we already have this patient).
  const prevHistory = existingFrontendPatient?.vital_history ?? [];
  const now = new Date();
  const historyPoint = {
    timestamp: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    isoTime:   now.toISOString(),
    ...vitals,
  };
  const vital_history = [...prevHistory, historyPoint].slice(-60);

  return {
    // Use the backend bed_id as patient_id so routing and WS matching work consistently.
    patient_id:         id,
    name:               name,
    age:                age,
    // Store raw gender and admission_type separately so the WS tick handler can
    // pass them back without unpacking the already-formatted `ward` string.
    gender:             gender ?? existingFrontendPatient?.gender ?? '',
    admission_type:     admission_type ?? existingFrontendPatient?.admission_type ?? '',
    ward:               `${gender ?? ''} · ${admission_type ?? ''}`,
    diagnosis:          admission_type ?? '',
    admission_duration: doctor ?? '',
    vitals,
    derived:            existingFrontendPatient?.derived ?? {},
    risk,
    vital_history,
    alerts:             existingFrontendPatient?.alerts ?? [],
    last_updated:       now.toISOString(),
  };
}

export function PatientProvider({ children }) {
  const [patients, setPatients] = useState(INITIAL_PATIENTS);
  const [selectedPatientId, setSelectedPatientId] = useState('P003');
  const [activeScenarioId, setActiveScenarioId] = useState('DETERIORATING');
  const [simulationSpeed, setSimulationSpeed] = useState(5); // 1x, 2x, 5x, 10x
  const [isSimulationRunning, setIsSimulationRunning] = useState(false);
  const [simulationStep, setSimulationStep] = useState(0);
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState('DISCONNECTED');
  const [virtualTime, setVirtualTime] = useState(new Date());

  const wsClientRef = useRef(null);
  // Tracks the current isDemoMode value inside async callbacks without causing
  // stale-closure re-runs of the WS useEffect.
  const isDemoModeRef = useRef(isDemoMode);
  useEffect(() => { isDemoModeRef.current = isDemoMode; }, [isDemoMode]);

  // Computed summary metrics
  const activeAlerts = patients.flatMap(p => p.alerts || []).filter(a => a.status === 'ACTIVE');
  const criticalCount = patients.filter(p => p.risk.level === 'CRITICAL' || p.risk.level === 'HIGH').length;
  const mediumCount = patients.filter(p => p.risk.level === 'MEDIUM' || p.risk.level === 'MODERATE').length;
  const normalCount = patients.filter(p => p.risk.level === 'NORMAL' || p.risk.level === 'LOW').length;

  const selectedPatient = patients.find(p => p.patient_id === selectedPatientId) || patients[0];

  /**
   * Load real patient roster from the backend and replace the frontend patient list.
   * Called when the user switches to live mode. Uses bed_id (e.g. "BED-101") as patient_id
   * so the WebSocket handler can match updates by the same key.
   */
  const loadLivePatients = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/patients`, {
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const backendPatients = await res.json();
      const livePatients = backendPatients.map(bp => backendPatientToFrontend(bp));
      setPatients(livePatients);
      // Select the first live patient by default.
      if (livePatients.length > 0) {
        setSelectedPatientId(livePatients[0].patient_id);
      }
    } catch (err) {
      console.warn('Could not load live patients from backend; staying in demo mode.', err.message);
      setIsDemoMode(true);
      setConnectionStatus('DISCONNECTED');
    }
  }, []);

  // Initialize WebSocket client
  useEffect(() => {
    wsClientRef.current = new VitalWebSocketClient(
      (data) => {
        // Backend packet structure:
        // {
        //   t: <float seconds>,
        //   waveforms: { "BED-101": { ecg, ppg }, ... },
        //   vitals: { "BED-101": { vitals: {...}, analysis: {...} }, ... } | null
        // }
        // vitals is null on non-1Hz ticks (waveform-only frames). Skip those.
        // Also skip entirely in demo mode to avoid overwriting demo patient state.
        if (isDemoModeRef.current) return;
        if (!data?.vitals) return;

        setPatients(prev => {
          let changed = false;
          const next = [...prev];

          for (const [bedId, payload] of Object.entries(data.vitals)) {
            // Match on patient_id which equals bedId in live mode (set by loadLivePatients).
            const idx = next.findIndex(p => p.patient_id === bedId);
            if (idx === -1) continue; // unknown bed; skip

            const { vitals: rawVitals, analysis } = payload;
            const existing = next[idx];

            // Reconstruct a backend-shaped object to pass through the normaliser.
            const updated = backendPatientToFrontend(
              {
                id:             bedId,
                name:           existing.name,
                age:            existing.age,
                // Use the stored raw gender/admission_type fields, not the
                // pre-formatted `ward` string, to avoid compounding the suffix
                // on every 1Hz tick.
                gender:         existing.gender         ?? '',
                admission_type: existing.admission_type ?? existing.diagnosis ?? '',
                doctor:         existing.admission_duration,
                vitals:         rawVitals,
                analysis,
              },
              existing  // pass existing patient so vital_history is appended and
                        // any REST-loaded explanations are preserved
            );
            next[idx] = updated;
            changed = true;
          }

          return changed ? next : prev;
        });
      },
      (status) => {
        setConnectionStatus(status);
        if (status === 'CONNECTED') {
          // Fetch the real patient roster immediately on connect so we have names, ages,
          // and initial ML risk scores before the first WS vital tick arrives.
          loadLivePatients();
        }
      }
    );

    if (!isDemoMode) {
      wsClientRef.current.connect();
    } else {
      // Cleanly disconnect silently when switching to demo mode
      wsClientRef.current.disconnect(true);
      setConnectionStatus('DISCONNECTED');
      setPatients(INITIAL_PATIENTS);
      setSelectedPatientId('P003');
    }

    return () => {
      if (wsClientRef.current) wsClientRef.current.disconnect(true);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDemoMode, loadLivePatients]);

  // Simulation Clock Loop (demo mode only)
  useEffect(() => {
    if (!isSimulationRunning) return;

    // Base interval tick is 2000ms divided by speed multiplier
    const intervalMs = Math.max(200, Math.round(2000 / simulationSpeed));

    const timer = setInterval(() => {
      setSimulationStep(prevStep => {
        const nextStep = prevStep + 1;

        setPatients(prevPatients => {
          return prevPatients.map(patient => {
            // Apply active scenario primarily to P003 (or selected target patient)
            if (patient.patient_id === selectedPatientId) {
              return runSimulationTick(patient, activeScenarioId, nextStep);
            } else {
              // Maintain baseline stable variation for other background patients
              return runSimulationTick(patient, 'NORMAL', 0);
            }
          });
        });

        // Advance virtual time by 5 minutes per tick
        setVirtualTime(prev => new Date(prev.getTime() + 5 * 60 * 1000));

        return nextStep;
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isSimulationRunning, simulationSpeed, selectedPatientId, activeScenarioId]);

  // Actions
  const startSimulation = useCallback(() => setIsSimulationRunning(true), []);
  const pauseSimulation = useCallback(() => setIsSimulationRunning(false), []);
  
  const resetSimulation = useCallback(() => {
    setIsSimulationRunning(false);
    setSimulationStep(0);
    setPatients(INITIAL_PATIENTS);
    setVirtualTime(new Date());
  }, []);

  const acknowledgeAlertAction = useCallback(async (alertId) => {
    // Optimistic local state update
    setPatients(prevPatients => {
      return prevPatients.map(patient => ({
        ...patient,
        alerts: (patient.alerts || []).map(a => 
          a.alert_id === alertId ? { ...a, status: 'ACKNOWLEDGED', acknowledged_at: new Date().toISOString() } : a
        )
      }));
    });

    // Call API service
    await apiAcknowledgeAlert(alertId);
  }, []);

  const changeScenario = useCallback((scenarioId) => {
    setActiveScenarioId(scenarioId);
    setSimulationStep(0);
  }, []);

  const value = {
    patients,
    selectedPatient,
    selectedPatientId,
    setSelectedPatientId,
    activeAlerts,
    activeScenarioId,
    changeScenario,
    simulationSpeed,
    setSimulationSpeed,
    isSimulationRunning,
    startSimulation,
    pauseSimulation,
    resetSimulation,
    simulationStep,
    virtualTime,
    isDemoMode,
    setIsDemoMode,
    connectionStatus,
    acknowledgeAlertAction,
    summaryMetrics: {
      total: patients.length,
      normalCount,
      mediumCount,
      criticalCount,
      activeAlertsCount: activeAlerts.length
    }
  };

  return (
    <PatientContext.Provider value={value}>
      {children}
    </PatientContext.Provider>
  );
}

export function usePatientContext() {
  const context = useContext(PatientContext);
  if (!context) {
    throw new Error('usePatientContext must be used within a PatientProvider');
  }
  return context;
}
