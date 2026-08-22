/**
 * NEWS2 (National Early Warning Score 2) clinical calculator
 * Standard scoring system used by the NHS and global healthcare systems.
 */

export function calculateNEWS2(vitals) {
  const { heart_rate, spo2, respiratory_rate, temperature, systolic_bp } = vitals || {};
  let score = 0;
  const breakdown = {};

  // 1. Respiratory Rate
  let rrScore = 0;
  if (respiratory_rate <= 8) rrScore = 3;
  else if (respiratory_rate >= 9 && respiratory_rate <= 11) rrScore = 1;
  else if (respiratory_rate >= 12 && respiratory_rate <= 20) rrScore = 0;
  else if (respiratory_rate >= 21 && respiratory_rate <= 24) rrScore = 2;
  else if (respiratory_rate >= 25) rrScore = 3;
  breakdown.respiratory_rate = rrScore;
  score += rrScore;

  // 2. SpO2 Scale 1
  let spo2Score = 0;
  if (spo2 <= 91) spo2Score = 3;
  else if (spo2 === 92 || spo2 === 93) spo2Score = 2;
  else if (spo2 === 94 || spo2 === 95) spo2Score = 1;
  else if (spo2 >= 96) spo2Score = 0;
  breakdown.spo2 = spo2Score;
  score += spo2Score;

  // 3. Systolic BP
  let sbpScore = 0;
  if (systolic_bp <= 90) sbpScore = 3;
  else if (systolic_bp >= 91 && systolic_bp <= 100) sbpScore = 2;
  else if (systolic_bp >= 101 && systolic_bp <= 110) sbpScore = 1;
  else if (systolic_bp >= 111 && systolic_bp <= 219) sbpScore = 0;
  else if (systolic_bp >= 220) sbpScore = 3;
  breakdown.systolic_bp = sbpScore;
  score += sbpScore;

  // 4. Heart Rate
  let hrScore = 0;
  if (heart_rate <= 40) hrScore = 3;
  else if (heart_rate >= 41 && heart_rate <= 50) hrScore = 1;
  else if (heart_rate >= 51 && heart_rate <= 90) hrScore = 0;
  else if (heart_rate >= 91 && heart_rate <= 110) hrScore = 1;
  else if (heart_rate >= 111 && heart_rate <= 130) hrScore = 2;
  else if (heart_rate >= 131) hrScore = 3;
  breakdown.heart_rate = hrScore;
  score += hrScore;

  // 5. Temperature
  let tempScore = 0;
  if (temperature <= 35.0) tempScore = 3;
  else if (temperature >= 35.1 && temperature <= 36.0) tempScore = 1;
  else if (temperature >= 36.1 && temperature <= 38.0) tempScore = 0;
  else if (temperature >= 38.1 && temperature <= 39.0) tempScore = 1;
  else if (temperature >= 39.1) tempScore = 2;
  breakdown.temperature = tempScore;
  score += tempScore;

  // Risk categorization based on total NEWS2 score
  let riskLevel = 'LOW';
  if (score >= 7) riskLevel = 'HIGH';
  else if (score >= 5) riskLevel = 'MEDIUM';
  else if (Object.values(breakdown).some(s => s === 3)) riskLevel = 'MEDIUM';

  return {
    totalScore: score,
    riskLevel,
    breakdown
  };
}

export function calculateDerivedVitals(vitals) {
  const { heart_rate, systolic_bp, diastolic_bp } = vitals || {};
  
  // Mean Arterial Pressure (MAP) = (2 * diastolic + systolic) / 3
  const map = diastolic_bp && systolic_bp ? Math.round(((2 * diastolic_bp) + systolic_bp) / 3) : null;
  
  // Shock Index = Heart Rate / Systolic BP
  const shockIndex = heart_rate && systolic_bp ? parseFloat((heart_rate / systolic_bp).toFixed(2)) : null;
  
  // Pulse Pressure = Systolic - Diastolic
  const pulsePressure = systolic_bp && diastolic_bp ? systolic_bp - diastolic_bp : null;
  
  const news2 = calculateNEWS2(vitals);

  return {
    news2_score: news2.totalScore,
    news2_risk: news2.riskLevel,
    mean_arterial_pressure: map,
    shock_index: shockIndex,
    pulse_pressure: pulsePressure
  };
}
