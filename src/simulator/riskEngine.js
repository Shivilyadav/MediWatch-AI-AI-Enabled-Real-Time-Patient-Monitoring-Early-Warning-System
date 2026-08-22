/**
 * Demo ML Risk Prediction Engine
 * Computes estimated deterioration risk score, level, predicted event, time horizon,
 * and SHAP feature contributions for explainable AI breakdown.
 */

import { calculateNEWS2 } from '../utils/news2';
import { getRiskLevelFromScore, getPredictedEventDescription, getTimeHorizon } from '../utils/riskUtils';

export function calculateDemoRisk(vitals, vitalHistory = []) {
  const { heart_rate, spo2, respiratory_rate, temperature, systolic_bp, diastolic_bp } = vitals || {};
  const news2 = calculateNEWS2(vitals);
  
  let riskScore = 0.05;

  // 1. SpO2 Contribution (Heavy Weight in Respiratory Deterioration)
  if (spo2 < 90) riskScore += 0.40;
  else if (spo2 <= 92) riskScore += 0.30;
  else if (spo2 <= 94) riskScore += 0.20;
  else if (spo2 <= 95) riskScore += 0.10;

  // 2. Respiratory Rate Contribution
  if (respiratory_rate >= 28) riskScore += 0.30;
  else if (respiratory_rate >= 24) riskScore += 0.22;
  else if (respiratory_rate >= 21) riskScore += 0.15;
  else if (respiratory_rate >= 19) riskScore += 0.08;

  // 3. Heart Rate Contribution
  if (heart_rate >= 130) riskScore += 0.20;
  else if (heart_rate >= 115) riskScore += 0.14;
  else if (heart_rate >= 100) riskScore += 0.08;
  else if (heart_rate <= 45) riskScore += 0.18;

  // 4. Systolic BP / Shock Index Contribution
  if (systolic_bp <= 90) riskScore += 0.15;
  else if (systolic_bp <= 100) riskScore += 0.10;

  // 5. Temperature Contribution
  if (temperature >= 39.0) riskScore += 0.10;
  else if (temperature >= 38.2) riskScore += 0.05;

  // 6. NEWS2 Bonus
  if (news2.totalScore >= 7) riskScore += 0.15;
  else if (news2.totalScore >= 5) riskScore += 0.10;

  // Clamp between 0.05 and 0.98
  riskScore = Math.min(0.98, Math.max(0.05, parseFloat(riskScore.toFixed(2))));
  const level = getRiskLevelFromScore(riskScore);
  const predictedEvent = getPredictedEventDescription(level, vitals);
  const timeHorizon = getTimeHorizon(level);

  // Generate dynamic SHAP Factor Contributions sorted by weight
  const explanations = generateSHAPExplanations(vitals, news2.totalScore, vitalHistory);

  return {
    score: riskScore,
    level,
    predicted_event: predictedEvent,
    time_horizon: timeHorizon,
    news2_score: news2.totalScore,
    explanations
  };
}

function generateSHAPExplanations(vitals, news2Score, history = []) {
  const factors = [];
  const { heart_rate, spo2, respiratory_rate, temperature, systolic_bp } = vitals || {};

  // Previous reading comparison for trend calculation
  const prevReading = history.length > 2 ? history[history.length - 3] : null;

  // Respiratory Rate SHAP
  if (respiratory_rate >= 20) {
    const rrDiff = prevReading ? respiratory_rate - prevReading.respiratory_rate : 0;
    const statusText = rrDiff > 0 ? `WORSENING (+${rrDiff}/min)` : 'ELEVATED';
    const weight = respiratory_rate >= 25 ? 0.34 : 0.22;
    factors.push({
      feature: 'Respiratory Rate',
      value: `${respiratory_rate} breaths/min`,
      contribution: weight,
      status: statusText,
      direction: 'positive'
    });
  }

  // SpO2 SHAP
  if (spo2 <= 95) {
    const spo2Diff = prevReading ? prevReading.spo2 - spo2 : 0;
    const statusText = spo2Diff > 0 ? `WORSENING (-${spo2Diff}%)` : 'HYPOXIC DROP';
    const weight = spo2 <= 90 ? 0.32 : 0.24;
    factors.push({
      feature: 'SpO2 Saturation',
      value: `${spo2}%`,
      contribution: weight,
      status: statusText,
      direction: 'positive'
    });
  }

  // Heart Rate SHAP
  if (heart_rate >= 95) {
    const hrDiff = prevReading ? heart_rate - prevReading.heart_rate : 0;
    const statusText = hrDiff > 0 ? `RISING (+${hrDiff} bpm)` : 'TACHYCARDIC';
    const weight = heart_rate >= 120 ? 0.24 : 0.16;
    factors.push({
      feature: 'Heart Rate Trend',
      value: `${heart_rate} bpm`,
      contribution: weight,
      status: statusText,
      direction: 'positive'
    });
  }

  // NEWS2 Score SHAP
  if (news2Score >= 3) {
    const weight = news2Score >= 7 ? 0.20 : 0.14;
    factors.push({
      feature: 'NEWS2 Score',
      value: `${news2Score}`,
      contribution: weight,
      status: news2Score >= 7 ? 'CRITICAL HIGH' : 'ELEVATED',
      direction: 'positive'
    });
  }

  // Temperature SHAP
  if (temperature >= 37.8) {
    const weight = temperature >= 39.0 ? 0.16 : 0.09;
    factors.push({
      feature: 'Body Temperature',
      value: `${temperature}°C`,
      contribution: weight,
      status: 'FEBRILE',
      direction: 'positive'
    });
  }

  // Systolic BP SHAP
  if (systolic_bp <= 105) {
    factors.push({
      feature: 'Systolic Blood Pressure',
      value: `${systolic_bp} mmHg`,
      contribution: 0.12,
      status: 'HYPOTENSIVE DROP',
      direction: 'positive'
    });
  }

  // If stable/low risk, add protective factors
  if (factors.length === 0) {
    factors.push(
      { feature: 'SpO2 Oxygenation', value: `${spo2}%`, contribution: -0.25, status: 'OPTIMAL', direction: 'negative' },
      { feature: 'Respiratory Rate', value: `${respiratory_rate} /min`, contribution: -0.20, status: 'NORMAL', direction: 'negative' },
      { feature: 'Heart Rate', value: `${heart_rate} bpm`, contribution: -0.15, status: 'STABLE', direction: 'negative' }
    );
  }

  // Sort descending by contribution magnitude
  return factors.sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
}
