import React from 'react';
import { Sliders, Sparkles } from 'lucide-react';

import { SimulatorControls } from '../components/simulator/SimulatorControls';
import { ScenarioSelector } from '../components/simulator/ScenarioSelector';
import { SimulationStatus } from '../components/simulator/SimulationStatus';
import { PatientCard } from '../components/dashboard/PatientCard';
import { SHAPExplainer } from '../components/patient/SHAPExplainer';
import { usePatientContext } from '../context/PatientContext';

export function Simulator() {
  const { selectedPatient } = usePatientContext();

  // Prevent rendering errors if no patient is available
  if (!selectedPatient) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
          <p className="text-sm font-semibold text-slate-400">
            No patient selected for simulation.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-wide">
              Interactive Patient Simulator
            </h1>

            <span className="px-2.5 py-0.5 rounded-full bg-blue-950 text-blue-300 border border-blue-500/30 text-xs font-bold flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              Hackathon Controller
            </span>
          </div>

          <p className="text-xs sm:text-sm text-slate-400 font-medium mt-1">
            Control physiological progression curves, test early warnings,
            and validate AI risk score predictions.
          </p>
        </div>
      </div>

      {/* Simulator Controls */}
      <SimulatorControls />

      {/* Simulation Status */}
      <SimulationStatus />

      {/* Scenario Selector */}
      <ScenarioSelector />

      {/* Live Target Patient Telemetry Preview */}
      <div className="mt-6">

        <h2 className="text-sm font-bold text-white tracking-wide uppercase mb-3 flex items-center gap-2">
          <Sliders className="w-4 h-4 text-blue-400" />
          Target Patient Live Telemetry Preview
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

          {/* Patient Preview */}
          <div className="lg:col-span-6">
            <PatientCard patient={selectedPatient} />
          </div>

          {/* AI Explanation */}
          <div className="lg:col-span-6">
            <SHAPExplainer
              explanations={selectedPatient.risk?.explanations || []}
            />
          </div>

        </div>
      </div>

    </div>
  );
}