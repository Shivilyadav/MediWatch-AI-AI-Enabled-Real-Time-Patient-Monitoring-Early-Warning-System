/**
 * API Service Client — MediWatch Backend Integration
 * Interacts with the FastAPI backend that connects to the final ML model
 * (final-logreg-v1 / stage4-v2 / final_model_v1.pkl).
 *
 * All endpoints match the currently-implemented backend contract
 * defined in docs/BACKEND_ML_INTEGRATION.md.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8021';
const IS_DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';

export async function getPatients(fallbackLocalPatients) {
  if (IS_DEMO_MODE) return fallbackLocalPatients;

  try {
    const res = await fetch(`${API_BASE_URL}/api/patients`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('API getPatients failed. Falling back to local Demo Mode:', err.message);
    return fallbackLocalPatients;
  }
}

export async function getPatient(bedId, fallbackPatient) {
  if (IS_DEMO_MODE) return fallbackPatient;

  try {
    const res = await fetch(`${API_BASE_URL}/api/patients/${bedId}`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API getPatient(${bedId}) failed. Falling back to local data:`, err.message);
    return fallbackPatient;
  }
}

export async function simulateCondition(bedId, condition) {
  if (IS_DEMO_MODE) return { status: 'simulation_demo', bedId, condition };

  try {
    const res = await fetch(`${API_BASE_URL}/api/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bedId, condition }),
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API simulateCondition(${bedId}, ${condition}) failed. Falling back to Demo Mode:`, err.message);
    return { status: 'simulation_demo', bedId, condition };
  }
}

export async function getActiveAlerts(fallbackAlerts) {
  if (IS_DEMO_MODE) return fallbackAlerts;

  try {
    const res = await fetch(`${API_BASE_URL}/api/alerts`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('API getActiveAlerts failed. Falling back to local alerts:', err.message);
    return fallbackAlerts;
  }
}

export async function acknowledgeAlert(alertId) {
  if (IS_DEMO_MODE) return { alert_id: alertId, status: 'ACKNOWLEDGED' };

  try {
    const res = await fetch(`${API_BASE_URL}/api/alerts/acknowledge`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alertId }),
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API acknowledgeAlert(${alertId}) failed. Optimistically acknowledged locally:`, err.message);
    return { alert_id: alertId, status: 'ACKNOWLEDGED' };
  }
}

export async function getModelInfo(fallback) {
  if (IS_DEMO_MODE) return fallback;

  try {
    const res = await fetch(`${API_BASE_URL}/api/model/info`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('API getModelInfo failed. Falling back to Demo Mode:', err.message);
    return fallback;
  }
}

/**
 * Ingest a vitals snapshot through the backend.
 * The backend's /ws/telemetry endpoint handles the real-time vitals stream,
 * so this is a direct API call for single-snapshot evaluation.
 */
export async function evaluatePatient(bedId, vitals) {
  if (IS_DEMO_MODE) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/patients/${bedId}`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const data = await res.json();
    return data?.analysis || null;
  } catch (err) {
    console.warn(`API evaluatePatient(${bedId}) failed. Falling back to Demo Mode:`, err.message);
    return null;
  }
}