/**
 * Patient Simulator Engine Core
 * Handles interpolation between scenario stages, noise injection,
 * state recalculation, and alert triggering.
 */

import { SCENARIOS } from './scenarios';
import { calculateDemoRisk } from './riskEngine';
import { calculateDerivedVitals } from '../utils/news2';
import { checkAndGenerateAlerts } from './alertEngine';

export function runSimulationTick(patient, scenarioId, currentStepIndex = 0) {
  const scenario = SCENARIOS[scenarioId] || SCENARIOS.NORMAL;
  const stages = scenario.targetStages;
  
  // Clamp step index within active scenario stages
  const activeStageIndex = Math.min(currentStepIndex, stages.length - 1);
  const targetStage = stages[activeStageIndex];
  const targetVitals = targetStage.vitals;

  const currentVitals = { ...patient.vitals };

  // Interpolate current vitals smoothly towards target vitals with noise
  const updatedVitals = {
    heart_rate: interpolateVital(currentVitals.heart_rate, targetVitals.heart_rate, 2.0, 1.5),
    spo2: Math.min(100, Math.max(75, interpolateVital(currentVitals.spo2, targetVitals.spo2, 0.8, 0.4))),
    respiratory_rate: Math.max(8, interpolateVital(currentVitals.respiratory_rate, targetVitals.respiratory_rate, 1.0, 0.5)),
    temperature: parseFloat(interpolateVital(currentVitals.temperature, targetVitals.temperature, 0.15, 0.05).toFixed(1)),
    systolic_bp: interpolateVital(currentVitals.systolic_bp, targetVitals.systolic_bp, 2.5, 1.2),
    diastolic_bp: interpolateVital(currentVitals.diastolic_bp, targetVitals.diastolic_bp, 1.8, 1.0)
  };

  // Recalculate derived clinical values
  const derived = calculateDerivedVitals(updatedVitals);

  // Append new history point
  const now = new Date();
  const timeLabel = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const historyPoint = {
    timestamp: timeLabel,
    isoTime: now.toISOString(),
    ...updatedVitals,
    news2_score: derived.news2_score
  };

  const updatedHistory = [...(patient.vital_history || []), historyPoint].slice(-60); // Keep last 60 points

  // Run Demo ML Risk Engine
  const riskResult = calculateDemoRisk(updatedVitals, updatedHistory);

  // Check and trigger new alerts if conditions met
  const tempPatient = { ...patient, vitals: updatedVitals };
  const updatedAlerts = checkAndGenerateAlerts(tempPatient, riskResult);

  return {
    ...patient,
    vitals: updatedVitals,
    derived,
    risk: {
      score: riskResult.score,
      level: riskResult.level,
      predicted_event: riskResult.predicted_event,
      time_horizon: riskResult.time_horizon,
      explanations: riskResult.explanations
    },
    vital_history: updatedHistory,
    alerts: updatedAlerts,
    last_updated: now.toISOString()
  };
}

function interpolateVital(current, target, stepSize, noiseRange) {
  const diff = target - current;
  let nextValue = current;

  if (Math.abs(diff) < 0.2) {
    nextValue = target;
  } else {
    nextValue = current + Math.sign(diff) * Math.min(Math.abs(diff), stepSize);
  }

  // Inject physiological noise
  const noise = (Math.random() * 2 - 1) * noiseRange;
  return Math.round((nextValue + noise) * 10) / 10;
}
