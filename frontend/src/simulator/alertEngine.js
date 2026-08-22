/**
 * Demo Alert Engine
 * Evaluates patient vitals & risk scores to produce non-repetitive clinical alerts
 * with suppression windows, multi-vital aggregation, and severity escalation.
 */

const SUPPRESSION_WINDOW_MS = 2 * 60 * 1000; // 2 minutes suppression window

export function checkAndGenerateAlerts(patient, riskResult) {
  const { patient_id, name, vitals, alerts = [] } = patient;
  const { score: riskScore, level: riskLevel, news2_score: news2Score } = riskResult;

  // Determine severity tier
  let alertSeverity = null;
  if (riskScore >= 0.85 || news2Score >= 7) {
    alertSeverity = 'CRITICAL';
  } else if ((riskScore >= 0.65 && riskScore <= 0.84) || (news2Score >= 5 && news2Score <= 6)) {
    alertSeverity = 'HIGH';
  } else if ((riskScore >= 0.45 && riskScore <= 0.64) || (news2Score >= 3 && news2Score <= 4)) {
    alertSeverity = 'MEDIUM';
  }

  // No alert needed for LOW risk
  if (!alertSeverity) {
    return alerts;
  }

  // Build aggregated medical rationale
  const reason = buildAggregatedReason(vitals, riskScore, news2Score);

  // Check existing active alerts for suppression & escalation
  const activeAlerts = alerts.filter(a => a.status === 'ACTIVE');
  const now = new Date();

  const existingSameSeverity = activeAlerts.find(a => a.severity === alertSeverity);
  if (existingSameSeverity) {
    const timeSinceLast = now - new Date(existingSameSeverity.timestamp);
    if (timeSinceLast < SUPPRESSION_WINDOW_MS) {
      // Suppress duplicate alert within window
      return alerts;
    }
  }

  // Check for severity escalation (e.g., existing alert was MEDIUM, now CRITICAL)
  const updatedAlerts = alerts.map(a => {
    if (a.status === 'ACTIVE' && isLowerSeverity(a.severity, alertSeverity)) {
      return { ...a, status: 'RESOLVED', resolved_at: now.toISOString(), resolution_note: 'Escalated to higher severity' };
    }
    return a;
  });

  const alertId = `ALT-${patient_id}-${Date.now().toString().slice(-6)}`;

  const newAlert = {
    alert_id: alertId,
    patient_id,
    patient_name: name,
    severity: alertSeverity,
    reason,
    risk_score: riskScore,
    news2_score: news2Score,
    timestamp: now.toISOString(),
    status: 'ACTIVE',
    vitals_snapshot: { ...vitals }
  };

  return [newAlert, ...updatedAlerts];
}

function isLowerSeverity(current, target) {
  const ranks = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };
  return (ranks[current] || 0) < (ranks[target] || 0);
}

function buildAggregatedReason(vitals, riskScore, news2Score) {
  const parts = [];
  const { heart_rate, spo2, respiratory_rate, temperature, systolic_bp } = vitals;

  if (spo2 < 90) parts.push(`SpO2 rapidly decreasing (${spo2}%)`);
  else if (spo2 <= 93) parts.push(`Hypoxia observed (${spo2}%)`);

  if (respiratory_rate >= 25) parts.push(`Tachypnea severe (${respiratory_rate}/min)`);
  else if (respiratory_rate >= 21) parts.push(`Respiratory rate increasing (${respiratory_rate}/min)`);

  if (heart_rate >= 120) parts.push(`Severe tachycardia (${heart_rate} bpm)`);
  else if (heart_rate >= 100) parts.push(`Heart rate elevated (${heart_rate} bpm)`);

  if (systolic_bp <= 90) parts.push(`Hypotension detected (BP ${systolic_bp} mmHg)`);

  if (temperature >= 38.8) parts.push(`High fever (${temperature}°C)`);

  if (parts.length === 0) {
    return `Risk score elevated to ${Math.round(riskScore * 100)}% (NEWS2: ${news2Score})`;
  }

  return parts.join(' • ');
}
