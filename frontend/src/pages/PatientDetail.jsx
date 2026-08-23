import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  MapPin,
  Stethoscope
} from 'lucide-react';

import { usePatientContext } from '../context/PatientContext';
import { RiskGauge } from '../components/patient/RiskGauge';
import { VitalsSummary } from '../components/patient/VitalsSummary';
import { VitalsChart } from '../components/patient/VitalsChart';
import { SHAPExplainer } from '../components/patient/SHAPExplainer';
import { NEWS2Timeline } from '../components/patient/NEWS2Timeline';
import { AlertHistory } from '../components/patient/AlertHistory';
import { StatusBadge } from '../components/common/StatusBadge';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8021';

export function PatientDetail() {
  const { patientId } = useParams();
  const navigate = useNavigate();

  const {
    patients,
    setSelectedPatientId,
    isDemoMode,
    setIsDemoMode,
  } = usePatientContext();

  // If a BED-XXX URL is opened directly while in demo mode, auto-switch to live mode
  useEffect(() => {
    if (patientId?.startsWith('BED-') && isDemoMode) {
      setIsDemoMode(false);
    }
  }, [patientId, isDemoMode, setIsDemoMode]);

  const [directPatient, setDirectPatient] = useState(null);
  const patient = patients.find(p => p.patient_id === patientId) || directPatient;

  // In live mode, fetch the detail endpoint (explain=True) to get real model
  // feature contributions. The WebSocket telemetry uses explain=False so it
  // never carries explanations. We fetch once on page open and refresh every 30s.
  const [liveExplanations, setLiveExplanations] = useState(null);

  useEffect(() => {
    if (patient) {
      setSelectedPatientId(patient.patient_id);
    }
  }, [patient, setSelectedPatientId]);

  useEffect(() => {
    if (!patientId) return;

    let cancelled = false;

    async function fetchPatientDetail() {
      try {
        const res = await fetch(`${API_BASE_URL}/api/patients/${patientId}`, {
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (cancelled) return;

        if (data?.analysis?.explanations) {
          setLiveExplanations(data.analysis.explanations);
        }

        // If patient wasn't in global context yet, populate directPatient fallback
        if (!patients.some(p => p.patient_id === patientId)) {
          const rawVitals = data.vitals;
          const vitals = {
            heart_rate:       rawVitals?.heart_rate ?? null,
            spo2:             rawVitals?.spo2 ?? null,
            respiratory_rate: rawVitals?.resp_rate ?? rawVitals?.respiratory_rate ?? null,
            temperature:      rawVitals?.temp ?? rawVitals?.temperature ?? null,
            systolic_bp:      rawVitals?.sys_bp ?? rawVitals?.systolic_bp ?? null,
            diastolic_bp:     rawVitals?.dia_bp ?? rawVitals?.diastolic_bp ?? null,
          };
          const risk = {
            score:              data.analysis?.probability ?? 0,
            level:              data.analysis?.risk_level ?? 'LOW',
            explanations:       data.analysis?.explanations ?? [],
            alert:              data.analysis?.alert ?? false,
            alert_actionable:   data.analysis?.alert_actionable ?? false,
            history_sufficient: data.analysis?.history_sufficient ?? false,
            disclaimer:         data.analysis?.disclaimer ?? '',
          };
          setDirectPatient({
            patient_id:         data.id,
            name:               data.name,
            age:                data.age,
            gender:             data.gender,
            admission_type:     data.admission_type,
            ward:               `${data.gender} · ${data.admission_type}`,
            diagnosis:          data.admission_type,
            admission_duration: data.doctor,
            vitals,
            derived:            {},
            risk,
            vital_history:      [],
            alerts:             [],
            last_updated:       new Date().toISOString(),
          });
        }
      } catch (err) {
        // Non-fatal
      }
    }

    fetchPatientDetail();
    const interval = setInterval(fetchPatientDetail, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isDemoMode, patientId, patients]);

  // Patient not found
  if (!patient) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center">
        <div className="bg-white border border-sky-200 rounded-xl p-8 shadow-sm">
          <p className="text-base font-bold text-slate-700">
            Patient record not found.
          </p>

          <Link
            to="/"
            className="text-xs text-sky-600 underline mt-2 inline-block"
          >
            Back to Command Center
          </Link>
        </div>
      </div>
    );
  }

  const {
    patient_id,
    name,
    age,
    ward,
    diagnosis,
    admission_duration,
    vitals,
    derived,
    risk,
    vital_history,
    alerts,
    last_updated
  } = patient;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

      {/* Back Navigation */}
      <div className="mb-4">
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 hover:text-sky-700 bg-white border border-sky-200 px-3 py-1.5 rounded-lg transition-colors shadow-sm"
        >
          <ArrowLeft className="w-4 h-4 text-sky-600" />
          Back to Command Center
        </button>
      </div>

      {/* Patient Clinical Header */}
      <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-sm mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">

        <div className="flex items-start gap-4">

          {/* Patient ID */}
          <div className="w-12 h-12 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-700 font-extrabold text-lg shrink-0">
            {patient_id}
          </div>

          <div>

            <div className="flex items-center gap-3 flex-wrap">

              <h1 className="text-xl font-black text-slate-900 tracking-wide">
                {name}
              </h1>

              <span className="text-xs font-bold text-slate-500">
                Age: {age}y
              </span>

              <StatusBadge level={risk?.level} />

            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 mt-1">

              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-sky-600" />
                {ward}
              </span>

              <span className="flex items-center gap-1">
                <Stethoscope className="w-3.5 h-3.5 text-cyan-600" />
                {diagnosis}
              </span>

              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-500" />
                Admission: {admission_duration}
              </span>

            </div>
          </div>
        </div>

        {/* Quick Patient Switcher */}
        <div className="flex items-center gap-1 bg-sky-50 p-1 rounded-xl border border-sky-200 self-start md:self-auto">

          {patients.map(p => (
            <button
              key={p.patient_id}
              onClick={() =>
                navigate(`/patient/${p.patient_id}`)
              }
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                p.patient_id === patient_id
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-200'
                  : 'text-slate-600 hover:text-sky-700 hover:bg-white'
              }`}
            >
              {p.patient_id}
            </button>
          ))}

        </div>
      </div>

      {/* 1. Live Vitals */}
      <VitalsSummary vitals={vitals} />

      {/* 2. AI Risk Gauge */}
      <div className="mb-6">
        <RiskGauge
          risk={risk}
          derived={derived}
          lastUpdated={last_updated}
        />
      </div>

      {/* 3. Charts & Explanations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Left Column */}
        <div className="lg:col-span-7">

          <VitalsChart
            vitalHistory={vital_history || []}
          />

          <NEWS2Timeline
            vitalHistory={vital_history || []}
          />

        </div>

        {/* Right Column */}
        <div className="lg:col-span-5">

          <SHAPExplainer
            explanations={
              !isDemoMode && liveExplanations !== null
                ? liveExplanations
                : (risk?.explanations || [])
            }
          />

          <AlertHistory
            alerts={alerts || []}
          />

        </div>

      </div>
    </div>
  );
}