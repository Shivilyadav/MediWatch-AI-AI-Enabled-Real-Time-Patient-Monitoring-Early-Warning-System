import React from 'react';
import { ShieldAlert, Clock, AlertTriangle, Activity } from 'lucide-react';
import { getRiskColor } from '../../utils/formatters';

export function RiskGauge({ risk = {}, derived = {}, lastUpdated }) {
  const {
    score = 0.45,
    level = 'MEDIUM',
    predicted_event = 'Monitoring Baseline',
    time_horizon = 'Within 12 Hours'
  } = risk;

  const scorePercent = Math.round(score * 100);
  const styles = getRiskColor(level);

  // SVG Gauge calculations (semi-circle arc)
  const radius = 70;
  const circumference = Math.PI * radius;
  const strokeDashoffset =
    circumference - (scorePercent / 100) * circumference;

  return (
    <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-sm">

      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-sky-100 mb-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-sky-600" />

          <h2 className="text-sm font-bold text-slate-900 tracking-wide">
            AI Deterioration Risk Gauge
          </h2>
        </div>

        <span
          className={`px-3 py-1 rounded-full text-xs font-bold border tracking-wider uppercase ${styles.badgeBg} ${styles.badgeText} ${styles.border}`}
        >
          {level} RISK
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">

        {/* Animated Semi-Circle Gauge */}
        <div className="md:col-span-5 flex flex-col items-center justify-center relative">

          <svg
            className="w-48 h-28 overflow-visible"
            viewBox="0 0 160 90"
          >
            {/* Background Arc */}
            <path
              d="M 10 85 A 70 70 0 0 1 150 85"
              fill="none"
              stroke="#DBEAFE"
              strokeWidth="14"
              strokeLinecap="round"
            />

            {/* Animated Risk Arc */}
            <path
              d="M 10 85 A 70 70 0 0 1 150 85"
              fill="none"
              stroke={styles.hex}
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-1000 ease-out"
            />
          </svg>

          {/* Central Score Text */}
          <div className="absolute top-10 flex flex-col items-center">
            <span
              className={`text-4xl font-black ${styles.text} tracking-tight`}
            >
              {scorePercent}%
            </span>

            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              Deterioration Risk
            </span>
          </div>

          {/* Threshold Legend */}
          <div className="flex items-center justify-between w-full text-[10px] font-semibold px-4 mt-2">
            <span className="text-emerald-600">0% Low</span>
            <span className="text-yellow-600">45% Med</span>
            <span className="text-orange-600">65% High</span>
            <span className="text-red-600">85% Crit</span>
          </div>
        </div>

        {/* Predictive Summary Cards */}
        <div className="md:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-3">

          {/* Predicted Event */}
          <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl">
            <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium mb-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              Predicted Event
            </div>

            <div className="text-sm font-bold text-slate-900 leading-tight">
              {predicted_event}
            </div>
          </div>

          {/* Time Horizon */}
          <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl">
            <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium mb-1">
              <Clock className="w-3.5 h-3.5 text-sky-600" />
              Time Horizon
            </div>

            <div className="text-sm font-bold text-slate-900 leading-tight">
              {time_horizon}
            </div>
          </div>

          {/* Current NEWS2 Score */}
          <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl">
            <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium mb-1">
              <Activity className="w-3.5 h-3.5 text-purple-600" />
              NEWS2 Score
            </div>

            <div className="text-xl font-extrabold text-slate-900">
              {derived.news2_score ?? '0'}

              <span className="text-xs text-slate-500 font-normal ml-2">
                ({derived.news2_risk ?? 'LOW'})
              </span>
            </div>
          </div>

          {/* Mean Arterial Pressure & Shock Index */}
          <div className="p-3 bg-sky-50 border border-sky-200 rounded-xl">
            <div className="flex items-center gap-1.5 text-xs text-slate-600 font-medium mb-1">
              <Activity className="w-3.5 h-3.5 text-cyan-600" />
              Hemodynamic Index
            </div>

            <div className="text-xs font-semibold text-slate-700">
              MAP:{' '}
              <span className="text-slate-900 font-bold">
                {derived.mean_arterial_pressure ?? '--'} mmHg
              </span>
            </div>

            <div className="text-xs font-semibold text-slate-700">
              Shock Index:{' '}
              <span className="text-slate-900 font-bold">
                {derived.shock_index ?? '--'}
              </span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}