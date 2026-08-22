import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  AlertOctagon,
  Check,
  Heart,
  Wind,
  Thermometer,
  Activity,
  Gauge,
  Clock,
  ShieldAlert
} from 'lucide-react';

import { usePatientContext } from '../context/PatientContext';
import { formatTimeAgo, getRiskColor } from '../utils/formatters';

export function MobileAlert() {
  const { alertId } = useParams();
  const navigate = useNavigate();

  const {
    patients,
    acknowledgeAlertAction
  } = usePatientContext();

  // Find requested alert
  const allAlerts = patients.flatMap(
    patient => patient.alerts || []
  );

  const alert =
    allAlerts.find(
      item => item.alert_id === alertId
    ) || allAlerts[0];

  // Alert not found
  if (!alert) {
    return (
      <div className="min-h-[85vh] flex items-center justify-center p-4 bg-sky-50">
        <div className="w-full max-w-md bg-white border border-sky-200 rounded-2xl p-8 text-center shadow-xl shadow-sky-100">

          <AlertOctagon className="w-10 h-10 text-slate-400 mx-auto mb-3" />

          <h1 className="text-lg font-black text-slate-800 mb-1">
            Alert Not Found
          </h1>

          <p className="text-sm text-slate-500 mb-5">
            The requested alert could not be found.
          </p>

          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-sm font-bold rounded-lg transition-colors"
          >
            Back to Command Center
          </button>
        </div>
      </div>
    );
  }

  const targetPatient = patients.find(
    patient => patient.patient_id === alert.patient_id
  );

  // Patient not found
  if (!targetPatient) {
    return (
      <div className="min-h-[85vh] flex items-center justify-center p-4 bg-sky-50">
        <div className="w-full max-w-md bg-white border border-sky-200 rounded-2xl p-8 text-center shadow-xl shadow-sky-100">

          <h1 className="text-lg font-black text-slate-800">
            Patient Record Not Found
          </h1>

          <button
            onClick={() => navigate('/')}
            className="mt-5 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-sm font-bold rounded-lg"
          >
            Back to Command Center
          </button>

        </div>
      </div>
    );
  }

  const vitals =
    alert.vitals_snapshot || targetPatient.vitals || {};

  const isAck = alert.status === 'ACKNOWLEDGED';
  const styles = getRiskColor(alert.severity);

  const handleAcknowledge = async () => {
    try {
      await acknowledgeAlertAction(alert.alert_id);
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center p-4 bg-sky-50">

      <div className="w-full max-w-md bg-white border border-sky-200 rounded-2xl shadow-xl shadow-sky-100 overflow-hidden">

        {/* Alert Header */}
        <div
          className={`p-4 text-center border-b ${styles.bg} ${styles.border} ${
            alert.severity === 'CRITICAL'
              ? 'animate-critical-glow'
              : ''
          }`}
        >

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 border border-red-200 text-red-600 text-xs font-black uppercase tracking-wider mb-2">
            <AlertOctagon className="w-4 h-4 text-red-500" />
            {alert.severity} ALERT NOTIFICATION
          </div>

          <h1 className="text-xl font-black text-slate-900">
            Patient {alert.patient_id}
          </h1>

          <p className="text-xs text-slate-500 font-medium">
            {alert.patient_name || targetPatient.name}
          </p>
        </div>

        {/* Risk Banner */}
        <div className="p-4 bg-slate-50 border-b border-sky-100 flex items-center justify-between">

          <div>
            <div className="text-[10px] font-bold text-slate-500 uppercase">
              AI Risk Score
            </div>

            <div className={`text-2xl font-black ${styles.text}`}>
              {Math.round((alert.risk_score || 0) * 100)}%
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] font-bold text-slate-500 uppercase">
              Alert Time
            </div>

            <div className="text-xs font-mono text-slate-600 font-semibold">
              {formatTimeAgo(alert.timestamp)}
            </div>
          </div>

        </div>

        {/* Clinical Reason */}
        <div className="p-4 bg-white border-b border-sky-100">

          <div className="text-[11px] font-bold text-slate-500 uppercase mb-1 flex items-center gap-1">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
            Primary Clinical Reason
          </div>

          <p className="text-sm font-semibold text-slate-800 leading-snug">
            {alert.reason || 'Clinical deterioration detected.'}
          </p>

        </div>

        {/* Current Vitals */}
        <div className="p-4">

          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
            Current Vitals Snapshot
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs font-semibold mb-4">

            {/* Heart Rate */}
            <div className="p-2.5 bg-white rounded-xl border border-red-200 flex items-center justify-between shadow-sm">

              <span className="flex items-center gap-1 text-slate-500">
                <Heart className="w-3.5 h-3.5 text-red-500" />
                HR:
              </span>

              <span className="text-slate-800 font-bold">
                {vitals.heart_rate ?? '--'} bpm
              </span>

            </div>

            {/* SpO2 */}
            <div className="p-2.5 bg-white rounded-xl border border-cyan-200 flex items-center justify-between shadow-sm">

              <span className="flex items-center gap-1 text-slate-500">
                <Activity className="w-3.5 h-3.5 text-cyan-500" />
                SpO2:
              </span>

              <span className="text-cyan-600 font-bold">
                {vitals.spo2 ?? '--'}%
              </span>

            </div>

            {/* Respiratory Rate */}
            <div className="p-2.5 bg-white rounded-xl border border-blue-200 flex items-center justify-between shadow-sm">

              <span className="flex items-center gap-1 text-slate-500">
                <Wind className="w-3.5 h-3.5 text-blue-500" />
                RR:
              </span>

              <span className="text-slate-800 font-bold">
                {vitals.respiratory_rate ?? '--'} /min
              </span>

            </div>

            {/* Temperature */}
            <div className="p-2.5 bg-white rounded-xl border border-amber-200 flex items-center justify-between shadow-sm">

              <span className="flex items-center gap-1 text-slate-500">
                <Thermometer className="w-3.5 h-3.5 text-amber-500" />
                Temp:
              </span>

              <span className="text-slate-800 font-bold">
                {vitals.temperature ?? '--'}°C
              </span>

            </div>

            {/* Blood Pressure */}
            <div className="col-span-2 p-2.5 bg-white rounded-xl border border-emerald-200 flex items-center justify-between shadow-sm">

              <span className="flex items-center gap-1 text-slate-500">
                <Gauge className="w-3.5 h-3.5 text-emerald-500" />
                Blood Pressure:
              </span>

              <span className="text-slate-800 font-bold">
                {vitals.systolic_bp ?? '--'}/
                {vitals.diastolic_bp ?? '--'} mmHg
              </span>

            </div>

          </div>

          {/* Time Since Normal */}
          <div className="flex items-center justify-between text-xs text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-sky-100 mb-4">

            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-sky-500" />
              Time Since Normal Reading:
            </span>

            <strong className="text-slate-700">
              12 minutes
            </strong>

          </div>

          {/* Acknowledge */}
          {isAck ? (
            <div className="w-full py-3 bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-sm rounded-xl text-center flex items-center justify-center gap-2">
              <Check className="w-4 h-4 text-emerald-500" />
              ALERT ACKNOWLEDGED
            </div>
          ) : (
            <button
              onClick={handleAcknowledge}
              className="w-full py-3.5 bg-red-600 hover:bg-red-500 active:scale-[0.98] text-white font-extrabold text-sm rounded-xl shadow-lg shadow-red-600/20 transition-all flex items-center justify-center gap-2"
            >
              <Check className="w-5 h-5 text-white" />
              ACKNOWLEDGE ALERT
            </button>
          )}

          {/* Patient Detail */}
          <div className="mt-3 text-center">

            <button
              onClick={() =>
                navigate(`/patient/${alert.patient_id}`)
              }
              className="text-xs text-sky-600 hover:text-sky-700 hover:underline font-semibold"
            >
              Open Full Patient Monitor →
            </button>

          </div>

        </div>
      </div>
    </div>
  );
}