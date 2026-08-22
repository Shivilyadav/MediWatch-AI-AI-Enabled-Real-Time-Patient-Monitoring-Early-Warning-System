import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import { Activity } from 'lucide-react';

export function NEWS2Timeline({ vitalHistory = [] }) {
  const latestScore =
    vitalHistory.length > 0
      ? vitalHistory[vitalHistory.length - 1].news2_score
      : 0;

  return (
    <div className="bg-white border border-blue-100 rounded-xl p-5 shadow-lg shadow-blue-100/50 backdrop-blur-md mb-6">

      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-blue-100 mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-purple-500" />

          <h2 className="text-sm font-bold text-slate-800 tracking-wide">
            NEWS2 Progression Timeline
          </h2>
        </div>

        <div className="flex items-center gap-3 text-xs font-semibold">
          <span className="text-slate-500">
            Current NEWS2:{' '}
            <strong className="text-slate-800 text-sm">
              {latestScore}
            </strong>
          </span>
        </div>
      </div>

      {/* Threshold Zone Legend */}
      <div className="flex items-center justify-end gap-4 text-[11px] font-semibold text-slate-500 mb-2">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          Low (0-4)
        </span>

        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
          Medium (5-6)
        </span>

        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
          High (7+)
        </span>
      </div>

      {/* Chart */}
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={vitalHistory}
            margin={{
              top: 10,
              right: 20,
              left: -20,
              bottom: 0
            }}
          >
            <defs>
              <linearGradient
                id="news2Gradient"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="5%"
                  stopColor="#8B5CF6"
                  stopOpacity={0.3}
                />

                <stop
                  offset="95%"
                  stopColor="#8B5CF6"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#DBEAFE"
              vertical={false}
            />

            <XAxis
              dataKey="timestamp"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#BFDBFE' }}
            />

            <YAxis
              stroke="#64748B"
              fontSize={11}
              domain={[0, 12]}
              tickLine={false}
              axisLine={{ stroke: '#BFDBFE' }}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: '#FFFFFF',
                borderColor: '#BFDBFE',
                borderRadius: '8px',
                color: '#1E293B',
                fontSize: '12px',
                boxShadow: '0 10px 25px -5px rgba(59, 130, 246, 0.15)'
              }}
            />

            <ReferenceLine
              y={5}
              stroke="#EAB308"
              strokeDasharray="3 3"
              label={{
                value: 'Medium Threshold (5)',
                fill: '#A16207',
                fontSize: 10
              }}
            />

            <ReferenceLine
              y={7}
              stroke="#EF4444"
              strokeDasharray="3 3"
              label={{
                value: 'High Threshold (7)',
                fill: '#DC2626',
                fontSize: 10
              }}
            />

            <Area
              type="monotone"
              dataKey="news2_score"
              stroke="#8B5CF6"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#news2Gradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}