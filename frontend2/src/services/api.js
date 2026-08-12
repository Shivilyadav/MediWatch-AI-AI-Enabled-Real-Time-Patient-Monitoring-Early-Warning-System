/**
 * API Service Client with Dual Mode Architecture.
 * Interacts with FastAPI backend when available, or seamlessly falls back
 * to local demo state.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
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

export async function getPatientVitals(patientId, fallbackHistory) {
  if (IS_DEMO_MODE) return fallbackHistory;

  try {
    const res = await fetch(`${API_BASE_URL}/api/patients/${patientId}/vitals`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`API getPatientVitals(${patientId}) failed. Falling back to local history:`, err.message);
    return fallbackHistory;
  }
}

export async function getPatientAlerts(patientId, fallbackAlerts) {
  if (IS_DEMO_MODE) return fallbackAlerts;

  try {
    const res = await fetch(`${API_BASE_URL}/api/patients/${patientId}/alerts`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    return fallbackAlerts;
  }
}

export async function getActiveAlerts(fallbackAlerts) {
  if (IS_DEMO_MODE) return fallbackAlerts;

  try {
    const res = await fetch(`${API_BASE_URL}/api/alerts/active`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    return fallbackAlerts;
  }
}

export async function ingestVitals(data) {
  if (IS_DEMO_MODE) return { status: 'ingested_demo', data };

  try {
    const res = await fetch(`${API_BASE_URL}/api/vitals/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn('Backend vitals ingestion failed, continuing in Demo Mode:', err.message);
    return { status: 'ingested_demo', data };
  }
}

export async function predictRisk(data) {
  if (IS_DEMO_MODE) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/predict/risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    return null;
  }
}

export async function acknowledgeAlert(alertId) {
  if (IS_DEMO_MODE) return { alert_id: alertId, status: 'ACKNOWLEDGED' };

  try {
    const res = await fetch(`${API_BASE_URL}/api/alerts/${alertId}/acknowledge`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(3000)
    });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend acknowledge alert ${alertId} failed. Optimistically acknowledged locally:`, err.message);
    return { alert_id: alertId, status: 'ACKNOWLEDGED' };
  }
}
