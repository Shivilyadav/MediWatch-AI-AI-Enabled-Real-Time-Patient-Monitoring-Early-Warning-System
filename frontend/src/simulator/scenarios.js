/**
 * Physiological simulation scenarios with stage-by-stage progression targets.
 */

export const SCENARIOS = {
  NORMAL: {
    id: 'NORMAL',
    name: 'Normal & Stable',
    description: 'Patient vitals remain within healthy physiological bounds with natural baseline variation.',
    targetStages: [
      {
        durationTicks: 10,
        vitals: { heart_rate: 74, spo2: 98, respiratory_rate: 14, temperature: 36.8, systolic_bp: 120, diastolic_bp: 78 },
        riskScore: 0.12,
        stageName: 'Stable Baseline'
      }
    ]
  },

  DETERIORATING: {
    id: 'DETERIORATING',
    name: 'Gradual Deterioration (Primary Hackathon Demo)',
    description: 'Pneumonia patient undergoing progressive respiratory distress across 4 clinical stages.',
    targetStages: [
      {
        durationTicks: 8,
        vitals: { heart_rate: 95, spo2: 95, respiratory_rate: 20, temperature: 37.2, systolic_bp: 110, diastolic_bp: 72 },
        riskScore: 0.45,
        stageName: 'Stage 1: Early Respiratory Strain (Medium Risk)'
      },
      {
        durationTicks: 8,
        vitals: { heart_rate: 105, spo2: 93, respiratory_rate: 22, temperature: 37.8, systolic_bp: 104, diastolic_bp: 68 },
        riskScore: 0.62,
        stageName: 'Stage 2: Mild Hypoxia & Tachycardia (Medium Risk)'
      },
      {
        durationTicks: 8,
        vitals: { heart_rate: 118, spo2: 91, respiratory_rate: 24, temperature: 38.4, systolic_bp: 96, diastolic_bp: 62 },
        riskScore: 0.78,
        stageName: 'Stage 3: Moderate Respiratory Failure (High Risk)'
      },
      {
        durationTicks: 8,
        vitals: { heart_rate: 130, spo2: 88, respiratory_rate: 28, temperature: 39.1, systolic_bp: 88, diastolic_bp: 58 },
        riskScore: 0.88,
        stageName: 'Stage 4: Severe Respiratory Distress & Shock (Critical Risk)'
      }
    ]
  },

  SEPSIS_ONSET: {
    id: 'SEPSIS_ONSET',
    name: 'Sepsis Onset (Rapid Inflammatory Crisis)',
    description: 'Rapid systemic infection leading to severe tachycardia, high fever, and systemic hypotension.',
    targetStages: [
      {
        durationTicks: 6,
        vitals: { heart_rate: 102, spo2: 94, respiratory_rate: 21, temperature: 38.2, systolic_bp: 108, diastolic_bp: 70 },
        riskScore: 0.54,
        stageName: 'Stage 1: Systemic Response'
      },
      {
        durationTicks: 6,
        vitals: { heart_rate: 118, spo2: 92, respiratory_rate: 24, temperature: 38.9, systolic_bp: 98, diastolic_bp: 62 },
        riskScore: 0.76,
        stageName: 'Stage 2: Early Septic Shock'
      },
      {
        durationTicks: 8,
        vitals: { heart_rate: 136, spo2: 89, respiratory_rate: 29, temperature: 39.6, systolic_bp: 84, diastolic_bp: 52 },
        riskScore: 0.92,
        stageName: 'Stage 3: Fulminant Septic Shock'
      }
    ]
  },

  RESPIRATORY_FAILURE: {
    id: 'RESPIRATORY_FAILURE',
    name: 'Acute Respiratory Failure',
    description: 'Rapid decline in pulmonary function leading to acute arterial desaturation.',
    targetStages: [
      {
        durationTicks: 6,
        vitals: { heart_rate: 98, spo2: 92, respiratory_rate: 22, temperature: 37.1, systolic_bp: 114, diastolic_bp: 74 },
        riskScore: 0.58,
        stageName: 'Stage 1: Mild Hypoxemia'
      },
      {
        durationTicks: 6,
        vitals: { heart_rate: 112, spo2: 87, respiratory_rate: 27, temperature: 37.3, systolic_bp: 106, diastolic_bp: 68 },
        riskScore: 0.81,
        stageName: 'Stage 2: Severe Hypoxemia'
      },
      {
        durationTicks: 8,
        vitals: { heart_rate: 128, spo2: 83, respiratory_rate: 32, temperature: 37.5, systolic_bp: 94, diastolic_bp: 60 },
        riskScore: 0.94,
        stageName: 'Stage 3: Respiratory Collapse'
      }
    ]
  },

  RECOVERING: {
    id: 'RECOVERING',
    name: 'Clinical Recovery & Stabilization',
    description: 'Therapeutic intervention leads to gradual stabilization of oxygenation and hemodynamics.',
    targetStages: [
      {
        durationTicks: 6,
        vitals: { heart_rate: 115, spo2: 91, respiratory_rate: 24, temperature: 38.3, systolic_bp: 98, diastolic_bp: 64 },
        riskScore: 0.68,
        stageName: 'Stage 1: Post-Intervention Response'
      },
      {
        durationTicks: 6,
        vitals: { heart_rate: 98, spo2: 94, respiratory_rate: 20, temperature: 37.6, systolic_bp: 108, diastolic_bp: 72 },
        riskScore: 0.46,
        stageName: 'Stage 2: Stabilizing Vitals'
      },
      {
        durationTicks: 8,
        vitals: { heart_rate: 78, spo2: 97, respiratory_rate: 15, temperature: 36.9, systolic_bp: 118, diastolic_bp: 76 },
        riskScore: 0.16,
        stageName: 'Stage 3: Full Stabilization'
      }
    ]
  }
};
