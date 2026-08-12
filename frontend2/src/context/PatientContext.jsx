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

  // Computed summary metrics
  const activeAlerts = patients.flatMap(p => p.alerts || []).filter(a => a.status === 'ACTIVE');
  const criticalCount = patients.filter(p => p.risk.level === 'CRITICAL' || p.risk.level === 'HIGH').length;
  const mediumCount = patients.filter(p => p.risk.level === 'MEDIUM').length;
  const normalCount = patients.filter(p => p.risk.level === 'NORMAL' || p.risk.level === 'LOW').length;

  const selectedPatient = patients.find(p => p.patient_id === selectedPatientId) || patients[2];

  // Initialize WebSocket client
  useEffect(() => {
    wsClientRef.current = new VitalWebSocketClient(
      (data) => {
        // When real WebSocket vitals stream arrives
        if (data && data.patient_id) {
          setPatients(prev => prev.map(p => p.patient_id === data.patient_id ? { ...p, ...data } : p));
        }
      },
      (status) => {
        setConnectionStatus(status);
        if (status === 'CONNECTED') {
          setIsDemoMode(false);
        }
      }
    );

    if (!isDemoMode) {
      wsClientRef.current.connect();
    }

    return () => {
      if (wsClientRef.current) wsClientRef.current.disconnect();
    };
  }, [isDemoMode]);

  // Simulation Clock Loop
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
