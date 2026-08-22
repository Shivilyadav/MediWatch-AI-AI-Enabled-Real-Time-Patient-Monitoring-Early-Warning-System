import React from 'react';
import { AlertTriangle } from 'lucide-react';

export function PrototypeDisclaimer() {
  return (
    <div className="bg-amber-950/40 border-b border-amber-500/30 px-4 py-1.5 text-xs text-amber-300 flex items-center justify-center gap-2 font-medium tracking-wide shadow-inner">
      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 animate-pulse" />
      <span>Prototype — Simulated data only. Not for clinical diagnosis or real patient care.</span>
    </div>
  );
}
