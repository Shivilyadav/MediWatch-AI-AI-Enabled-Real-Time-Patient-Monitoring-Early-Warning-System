import React from 'react';
import { Radio, Clock, Activity, Cpu } from 'lucide-react';
import { usePatientContext } from '../../context/PatientContext';
import { SCENARIOS } from '../../simulator/scenarios';

export function SimulationStatus() {
  const {
    isSimulationRunning,
    activeScenarioId,
    simulationStep,
    virtualTime,
    selectedPatient,
    simulationSpeed
  } = usePatientContext();

  const currentScenario =
    SCENARIOS[activeScenarioId] || SCENARIOS.NORMAL;

  return (
    <div className="bg-white border border-sky-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-md shadow-sky-100/40 mb-6">

      {/* Running Status */}
      <div className="flex items-center gap-3">
        <div
          className={`p-2.5 rounded-xl border ${
            isSimulationRunning
              ? 'bg-emerald-50 border-emerald-200 text-emerald-600 animate-pulse'
              : 'bg-slate-50 border-slate-200 text-slate-400'
          }`}
        >
          <Radio className="w-5 h-5" />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Simulation Engine
            </span>

            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                isSimulationRunning
                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                  : 'bg-slate-100 text-slate-500 border border-slate-200'
              }`}
            >
              {isSimulationRunning ? 'RUNNING' : 'PAUSED'}
            </span>
          </div>

          <p className="text-sm font-bold text-slate-800 mt-0.5">
            Scenario:{' '}
            <span className="text-sky-600">
              {currentScenario.name}
            </span>
          </p>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">
            Target Patient
          </span>
          <span className="font-bold text-slate-700">
            {selectedPatient.patient_id} ({selectedPatient.name})
          </span>
        </div>

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">
            Simulation Tick
          </span>

          <span className="font-bold text-slate-700 flex items-center gap-1">
            <Cpu className="w-3.5 h-3.5 text-purple-500" />
            Step {simulationStep}
          </span>
        </div>

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">
            Virtual Time
          </span>

          <span className="font-mono font-bold text-slate-700 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-sky-500" />
            {virtualTime.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        </div>

        <div>
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">
            Tick Velocity
          </span>

          <span className="font-bold text-slate-700 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-cyan-500" />
            {simulationSpeed}x Speed
          </span>
        </div>

      </div>
    </div>
  );
}