import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Heart,
  Wind,
  Thermometer,
  Activity,
  TrendingUp,
  TrendingDown,
  ChevronRight
} from 'lucide-react';
import { StatusBadge } from '../common/StatusBadge';
import { formatTimeAgo, getRiskColor, getVitalStatus } from '../../utils/formatters';

export function PatientCard({ patient }) {
  const navigate = useNavigate();

  const {
    patient_id,
    name,
    age,
    ward,
    diagnosis,
    vitals = {},
    derived = {},
    risk = {},
    last_updated
  } = patient;

  const riskStyles = getRiskColor(risk.level);
  const isCritical = risk.level === 'CRITICAL';
  const isHigh = risk.level === 'HIGH';

  const hrStatus = getVitalStatus('heart_rate', vitals.heart_rate);
  const spo2Status = getVitalStatus('spo2', vitals.spo2);
  const rrStatus = getVitalStatus('respiratory_rate', vitals.respiratory_rate);
  const tempStatus = getVitalStatus('temperature', vitals.temperature);

  return (
    <div
      onClick={() => navigate(`/patient/${patient_id}`)}
      className={`group relative rounded-xl border bg-white p-4 transition-all duration-300 cursor-pointer hover:border-sky-400 hover:shadow-xl hover:shadow-sky-100 ${
        isCritical
          ? 'border-red-500/80 animate-critical-glow'
          : isHigh
            ? 'border-orange-400/70 animate-high-glow'
            : 'border-sky-100'
      }`}
    >
      {/* Header Info */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base font-extrabold text-slate-900 group-hover:text-sky-600 transition-colors">
              {patient_id}
            </span>

            <span className="text-xs font-semibold text-slate-600">
              {name}
            </span>

            <span className="text-xs text-slate-400">
              ({age}y)
            </span>
          </div>

          <p className="text-xs text-slate-500 truncate max-w-[220px]">
            {ward} • {diagnosis}
          </p>
        </div>

        <StatusBadge level={risk.level} />
      </div>

      {/* AI Risk Score Banner */}
      <div
        className={`flex items-center justify-between p-2.5 rounded-lg mb-3 border ${riskStyles.bg} ${riskStyles.border}`}
      >
        <div>
          <div className="text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
            AI Risk Score
          </div>

          <div
            className={`text-xl font-black ${riskStyles.text} tracking-tight flex items-center gap-1.5`}
          >
            {Math.round(risk.score * 100)}%

            {risk.score >= 0.65 ? (
              <TrendingUp className="w-4 h-4 text-red-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-emerald-500" />
            )}
          </div>
        </div>

        <div className="text-right">
          <div className="text-[10px] font-semibold tracking-wider text-slate-500 uppercase">
            NEWS2 Score
          </div>

          <div className="text-base font-black text-slate-800">
            {derived.news2_score ?? 'N/A'}
          </div>
        </div>
      </div>

      {/* Live Vitals Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3 text-xs">

        {/* Heart Rate */}
        <div
          className={`p-2 rounded-lg border bg-sky-50 ${
            hrStatus.severity === 'NORMAL'
              ? 'border-sky-100'
              : 'border-red-300 bg-red-50'
          }`}
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="flex items-center gap-1 text-[11px] font-medium">
              <Heart className="w-3 h-3 text-red-500" />
              HR
            </span>

            <span className="text-[10px] font-bold text-slate-400">
              bpm
            </span>
          </div>

          <div className="text-base font-bold text-slate-900 flex items-baseline justify-between">
            {vitals.heart_rate ?? '--'}

            <span
              className={`text-[10px] font-semibold ${
                hrStatus.severity === 'NORMAL'
                  ? 'text-slate-500'
                  : 'text-red-500'
              }`}
            >
              {hrStatus.label}
            </span>
          </div>
        </div>

        {/* SpO2 */}
        <div
          className={`p-2 rounded-lg border bg-sky-50 ${
            spo2Status.severity === 'NORMAL'
              ? 'border-sky-100'
              : 'border-red-300 bg-red-50'
          }`}
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="flex items-center gap-1 text-[11px] font-medium">
              <Activity className="w-3 h-3 text-cyan-500" />
              SpO2
            </span>

            <span className="text-[10px] font-bold text-slate-400">
              %
            </span>
          </div>

          <div className="text-base font-bold text-slate-900 flex items-baseline justify-between">
            {vitals.spo2 ?? '--'}%

            <span
              className={`text-[10px] font-semibold ${
                spo2Status.severity === 'NORMAL'
                  ? 'text-slate-500'
                  : 'text-red-500'
              }`}
            >
              {spo2Status.label}
            </span>
          </div>
        </div>

        {/* Respiratory Rate */}
        <div
          className={`p-2 rounded-lg border bg-sky-50 ${
            rrStatus.severity === 'NORMAL'
              ? 'border-sky-100'
              : 'border-orange-300 bg-orange-50'
          }`}
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="flex items-center gap-1 text-[11px] font-medium">
              <Wind className="w-3 h-3 text-sky-500" />
              RR
            </span>

            <span className="text-[10px] font-bold text-slate-400">
              /min
            </span>
          </div>

          <div className="text-base font-bold text-slate-900 flex items-baseline justify-between">
            {vitals.respiratory_rate ?? '--'}

            <span
              className={`text-[10px] font-semibold ${
                rrStatus.severity === 'NORMAL'
                  ? 'text-slate-500'
                  : 'text-orange-500'
              }`}
            >
              {rrStatus.label}
            </span>
          </div>
        </div>

        {/* Temperature */}
        <div
          className={`p-2 rounded-lg border bg-sky-50 ${
            tempStatus.severity === 'NORMAL'
              ? 'border-sky-100'
              : 'border-amber-300 bg-amber-50'
          }`}
        >
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="flex items-center gap-1 text-[11px] font-medium">
              <Thermometer className="w-3 h-3 text-amber-500" />
              Temp
            </span>

            <span className="text-[10px] font-bold text-slate-400">
              °C
            </span>
          </div>

          <div className="text-base font-bold text-slate-900 flex items-baseline justify-between">
            {vitals.temperature ?? '--'}°

            <span
              className={`text-[10px] font-semibold ${
                tempStatus.severity === 'NORMAL'
                  ? 'text-slate-500'
                  : 'text-amber-500'
              }`}
            >
              {tempStatus.label}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-sky-100 text-[11px] text-slate-500">
        <span>
          Updated {formatTimeAgo(last_updated)}
        </span>

        <span className="flex items-center gap-1 font-semibold text-sky-600 group-hover:translate-x-1 transition-transform">
          View Detail
          <ChevronRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </div>
  );
}