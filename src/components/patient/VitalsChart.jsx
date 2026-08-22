import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import { Heart, Wind, Thermometer, Activity, Gauge } from 'lucide-react';

export function VitalsChart({ vitalHistory = [] }) {
  const [selectedVital, setSelectedVital] = useState('heart_rate');

  const chartConfigs = {
    heart_rate: {
      title: 'Heart Rate (HR)',
      unit: 'bpm',
      color: '#EF4444',
      icon: Heart,
      domain: [40, 150],
      referenceLines: [
        { y: 60, label: 'Min (60)' },
        { y: 100, label: 'Max (100)' }
      ]
    },
    spo2: {
      title: 'Oxygen Saturation (SpO2)',
      unit: '%',
      color: '#0891B2',
      domain: [75, 100],
      icon: Activity,
      referenceLines: [
        { y: 92, label: 'Hypoxic Threshold (92%)' },
        { y: 95, label: 'Normal (95%)' }
      ]
    },
    respiratory_rate: {
      title: 'Respiratory Rate (RR)',
      unit: '/min',
      color: '#2563EB',
      domain: [8, 35],
      icon: Wind,
      referenceLines: [
        { y: 12, label: 'Min (12)' },
        { y: 20, label: 'Max (20)' }
      ]
    },
    temperature: {
      title: 'Body Temperature',
      unit: '°C',
      color: '#D97706',
      domain: [35, 41],
      icon: Thermometer,
      referenceLines: [
        { y: 37.5, label: 'Fever Threshold (37.5°C)' }
      ]
    },
    systolic_bp: {
      title: 'Systolic Blood Pressure',
      unit: 'mmHg',
      color: '#059669',
      domain: [70, 180],
      icon: Gauge,
      referenceLines: [
        { y: 90, label: 'Hypotensive (90)' },
        { y: 120, label: 'Normal (120)' }
      ]
    }
  };

  const activeConfig = chartConfigs[selectedVital];
  const Icon = activeConfig.icon;

  const latestPoint =
    vitalHistory.length > 0
      ? vitalHistory[vitalHistory.length - 1]
      : {};

  const currentValue = latestPoint[selectedVital] ?? '--';

  return (
    <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-sm mb-6">

      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-sky-100 mb-4">

        <div className="flex items-center gap-3">

          <div className="p-2 rounded-xl bg-sky-50 border border-sky-200 text-sky-700">
            <Icon
              className="w-5 h-5"
              style={{ color: activeConfig.color }}
            />
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-wide">
              {activeConfig.title}
            </h3>

            <div className="text-xs text-slate-500 flex items-center gap-2">
              <span>
                Current:{' '}
                <strong className="text-slate-900 text-sm">
                  {currentValue} {activeConfig.unit}
                </strong>
              </span>

              <span>•</span>

              <span>Last 24 Hours View</span>
            </div>
          </div>

        </div>

        {/* Vital Switcher Tabs */}
        <div className="flex items-center gap-1 bg-sky-50 p-1 rounded-xl border border-sky-200 overflow-x-auto">

          {Object.keys(chartConfigs).map((key) => (
            <button
              key={key}
              onClick={() => setSelectedVital(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                selectedVital === key
                  ? 'bg-sky-600 text-white shadow-md'
                  : 'text-slate-600 hover:text-sky-700 hover:bg-white'
              }`}
            >
              {key === 'heart_rate' && 'HR'}
              {key === 'spo2' && 'SpO2'}
              {key === 'respiratory_rate' && 'RR'}
              {key === 'temperature' && 'Temp'}
              {key === 'systolic_bp' && 'BP'}
            </button>
          ))}

        </div>
      </div>

      {/* Recharts Responsive Container */}
      <div className="h-64 w-full">

        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={vitalHistory}
            margin={{
              top: 10,
              right: 20,
              left: -10,
              bottom: 0
            }}
          >

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#E0F2FE"
              vertical={false}
            />

            <XAxis
              dataKey="timestamp"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#BAE6FD' }}
            />

            <YAxis
              stroke="#64748B"
              fontSize={11}
              domain={activeConfig.domain}
              tickLine={false}
              axisLine={{ stroke: '#BAE6FD' }}
              unit={` ${activeConfig.unit}`}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderColor: '#BAE6FD',
                borderRadius: '8px',
                color: '#0F172A',
                fontSize: '12px',
                boxShadow: '0 10px 25px -5px rgba(14, 116, 144, 0.15)'
              }}
              labelStyle={{
                color: '#334155',
                fontWeight: '600'
              }}
            />

            {activeConfig.referenceLines.map((ref, idx) => (
              <ReferenceLine
                key={idx}
                y={ref.y}
                stroke="#EF4444"
                strokeDasharray="4 4"
                label={{
                  value: ref.label,
                  fill: '#64748B',
                  fontSize: 10,
                  position: 'right'
                }}
              />
            ))}

            <Line
              type="monotone"
              dataKey={selectedVital}
              stroke={activeConfig.color}
              strokeWidth={3}
              dot={false}
              activeDot={{
                r: 6,
                fill: activeConfig.color,
                stroke: '#FFFFFF',
                strokeWidth: 2
              }}
              animationDuration={800}
            />

          </LineChart>
        </ResponsiveContainer>

      </div>
    </div>
  );
}