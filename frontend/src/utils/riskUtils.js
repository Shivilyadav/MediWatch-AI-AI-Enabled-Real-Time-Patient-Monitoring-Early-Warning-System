/**
 * Supplementary risk utility functions and formatting helpers.
 *
 * IMPORTANT: In live mode the backend (final_model_v1.pkl) is the SOLE source of
 * risk_level. These utilities are used ONLY by the demo-mode simulation engine
 * (frontend/src/simulator/riskEngine.js). They must never override a backend score.
 *
 * Risk bands match the model artifact's own thresholds (read from final_model_v1.pkl):
 *   LOW      : probability < 0.3606
 *   MODERATE : 0.3606 <= probability < 0.7543
 *   HIGH     : probability >= 0.7543
 */

export function getRiskLevelFromScore(score) {
  if (score >= 0.7543) return 'HIGH';
  if (score >= 0.3606) return 'MODERATE';
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
    case 'HIGH':
      return 'Respiratory Deterioration & Hypoxia';
    case 'MODERATE':
      return 'Elevated Deterioration Risk';
    case 'LOW':
    default:
      return 'Stable — Low Risk of Deterioration';
  }
}

export function getTimeHorizon(level) {
  switch (level) {
    case 'HIGH':
      return 'Within 4 Hours';
    case 'MODERATE':
      return 'Within 12 Hours';
    case 'LOW':
    default:
      return 'Next 24 Hours';
  }
}
