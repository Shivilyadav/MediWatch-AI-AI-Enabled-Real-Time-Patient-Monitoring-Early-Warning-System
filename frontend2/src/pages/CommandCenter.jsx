import React from 'react';
import { KPISection } from '../components/dashboard/KPISection';
import { PatientGrid } from '../components/dashboard/PatientGrid';
import { AlertQueue } from '../components/dashboard/AlertQueue';

export function CommandCenter() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

      {/* Page Title & Clinical Subheading */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">

        <div>
          <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-wide">
            Hospital Command Center Dashboard
          </h1>

          <p className="text-xs sm:text-sm text-slate-600 font-medium">
            Real-time vital signs monitoring, AI risk scoring, and
            early warning alert queue across ICU & Ward units.
          </p>
        </div>

      </div>

      {/* KPI Section */}
      <KPISection />

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Patient Grid */}
        <div className="lg:col-span-8">

          <div className="flex items-center justify-between mb-3">

            <h2 className="text-sm font-bold text-slate-800 tracking-wide uppercase">
              Monitored Patient Units
            </h2>

            <span className="text-xs text-slate-500">
              Click any card to open clinical detail
            </span>

          </div>

          <PatientGrid />

        </div>

        {/* Alert Queue */}
        <div className="lg:col-span-4 lg:sticky lg:top-24">
          <AlertQueue />
        </div>

      </div>

    </div>
  );
}