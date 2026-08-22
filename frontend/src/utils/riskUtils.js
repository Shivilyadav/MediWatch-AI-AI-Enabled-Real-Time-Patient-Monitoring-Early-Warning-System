/**
 * Supplementary risk utility functions and formatting helpers.
 */

export function getRiskLevelFromScore(score) {
  if (score >= 0.85) return 'CRITICAL';
  if (score >= 0.65) return 'HIGH';
  if (score >= 0.45) return 'MEDIUM';
  return 'LOW';
}

export function formatRiskPercent(score) {
  if (score === undefined || score === null) return '0%';
  return `${Math.round(score * 100)}%`;
}

export function getPredictedEventDescription(level, vitals = {}) {
  const { spo2, respiratory_rate, heart_rate, temperature } = vitals;

  if (spo2 && spo2 < 90) {
    return 'Acute Respiratory Deterioration';
  }
  if (temperature && temperature >= 38.5 && heart_rate && heart_rate > 110) {
    return 'Severe Sepsis Onset';
  }
  if (heart_rate && heart_rate > 125) {
    return 'Hemodynamic Failure & Tachycardia';
  }

  switch (level) {
    case 'CRITICAL':
      return 'Imminent Cardiopulmonary Failure';
    case 'HIGH':
      return 'Respiratory Deterioration & Hypoxia';
    case 'MEDIUM':
      return 'Moderate Clinical Instability';
    case 'LOW':
    default:
      return 'Stable — Low Risk of Deterioration';
  }
}

export function getTimeHorizon(level) {
  switch (level) {
    case 'CRITICAL':
      return 'Within 1 Hour';
    case 'HIGH':
      return 'Within 4 Hours';
    case 'MEDIUM':
      return 'Within 12 Hours';
    case 'LOW':
    default:
      return 'Next 24 Hours';
  }
}
