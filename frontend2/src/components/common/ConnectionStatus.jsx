import React from 'react';
import { Wifi, WifiOff, Radio } from 'lucide-react';

export function ConnectionStatus({ status, isDemoMode }) {
  const isConnected = status === 'CONNECTED';

  if (isDemoMode) {
    return (
      <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-amber-200 bg-amber-50 text-amber-700">
        <Radio className="w-3.5 h-3.5" />
        <span className="text-[10px] font-bold uppercase tracking-wide">
          Demo Mode
        </span>
      </div>
    );
  }

  return (
    <div
      className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border ${
        isConnected
          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
          : 'border-red-200 bg-red-50 text-red-700'
      }`}
    >
      {isConnected ? (
        <Wifi className="w-3.5 h-3.5" />
      ) : (
        <WifiOff className="w-3.5 h-3.5" />
      )}

      <span className="text-[10px] font-bold uppercase tracking-wide">
        {isConnected ? 'Connected' : 'Disconnected'}
      </span>
    </div>
  );
}