import React from 'react';
import { Activity } from 'lucide-react';

export function LoadingState({ message = 'Loading patient monitoring telemetry...' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] p-8 text-slate-400">
      <Activity className="w-10 h-10 text-blue-500 animate-spin mb-3" />
      <p className="text-sm font-medium animate-pulse">{message}</p>
    </div>
  );
}
