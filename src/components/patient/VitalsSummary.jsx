import React from 'react';
import { Heart, Wind, Thermometer, Activity, Gauge } from 'lucide-react';
import { getVitalStatus } from '../../utils/formatters';

export function VitalsSummary({ vitals = {} }) {
  const {
    heart_rate,
    spo2,
    respiratory_rate,
    temperature,
    systolic_bp,
    diastolic_bp
  } = vitals;

  const hrStatus = getVitalStatus('heart_rate', heart_rate);
  const spo2Status = getVitalStatus('spo2', spo2);
  const rrStatus = getVitalStatus('respiratory_rate', respiratory_rate);
  const tempStatus = getVitalStatus('temperature', temperature);

  const vitalCards = [
    {
      label: 'Heart Rate',
      value: heart_rate ? `${heart_rate} bpm` : '--',
      normalRange: '60 - 100 bpm',
      icon: Heart,
      color: 'text-red-500',
      status: hrStatus
    },
    {
      label: 'Oxygen Saturation (SpO2)',
      value: spo2 ? `${spo2}%` : '--',
      normalRange: '95 - 100%',
      icon: Activity,
      color: 'text-cyan-600',
      status: spo2Status
    },
    {
      label: 'Respiratory Rate',
      value: respiratory_rate ? `${respiratory_rate} /min` : '--',
      normalRange: '12 - 20 /min',
      icon: Wind,
      color: 'text-blue-600',
      status: rrStatus
    },
    {
      label: 'Body Temperature',
      value: temperature ? `${temperature}°C` : '--',
      normalRange: '36.5 - 37.5°C',
      icon: Thermometer,
      color: 'text-amber-500',
      status: tempStatus
    },
    {
      label: 'Blood Pressure',
      value:
        systolic_bp && diastolic_bp
          ? `${systolic_bp}/${diastolic_bp} mmHg`
          : '--',
      normalRange: '120/80 mmHg',
      icon: Gauge,
      color: 'text-emerald-600',
      status: {
        label: systolic_bp < 90 ? 'Hypotensive' : 'Normal',
        severity: systolic_bp < 90 ? 'HIGH' : 'NORMAL'
      }
    }
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
      {vitalCards.map((card, idx) => {
        const Icon = card.icon;
        const isNormal = card.status.severity === 'NORMAL';

        return (
          <div
            key={idx}
            className={`p-3.5 rounded-xl border backdrop-blur-md transition-all shadow-sm ${
              isNormal
                ? 'border-blue-200 bg-white'
                : 'border-red-300 bg-red-50'
            }`}
          >
            <div className="flex items-center justify-between text-slate-600 mb-1.5">
              <span className="flex items-center gap-1.5 text-xs font-semibold">
                <Icon className={`w-3.5 h-3.5 ${card.color}`} />
                {card.label}
              </span>
            </div>

            <div className="text-lg sm:text-xl font-extrabold text-slate-900 mb-1">
              {card.value}
            </div>

            <div className="flex items-center justify-between text-[10px]">
              <span className="text-slate-500">
                Target: {card.normalRange}
              </span>

              <span
                className={`font-bold ${
                  isNormal ? 'text-emerald-600' : 'text-red-600'
                }`}
              >
                {card.status.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}