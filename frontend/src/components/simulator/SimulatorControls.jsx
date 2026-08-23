import React from 'react';
import { Play, Pause, RotateCcw, FastForward, User } from 'lucide-react';
import { usePatientContext } from '../../context/PatientContext';

export function SimulatorControls() {
  const {
    patients,
    selectedPatientId,
    setSelectedPatientId,
    isSimulationRunning,
    startSimulation,
    pauseSimulation,
    resetSimulation,
    simulationSpeed,
    setSimulationSpeed
  } = usePatientContext();

  const speeds = [1, 2, 5, 10];

  return (
    <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-md shadow-sky-100/40 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">

        {/* Patient Selection */}
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-sky-50 border border-sky-200 text-sky-600">
            <User className="w-5 h-5" />
          </div>

          <div>
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
              Target Patient Simulation
            </label>

            <select
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              className="bg-white border border-sky-200 text-slate-800 font-bold text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100 transition-colors cursor-pointer"
            >
              {patients.map((p) => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.patient_id} — {p.name} ({p.diagnosis})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Play / Pause / Reset */}
        <div className="flex items-center gap-2">
          {!isSimulationRunning ? (
            <button
              onClick={startSimulation}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl shadow-lg shadow-emerald-600/20 transition-all flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-white" />
              START SIMULATION
            </button>
          ) : (
            <button
              onClick={pauseSimulation}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-white font-bold text-sm rounded-xl shadow-lg shadow-amber-500/20 transition-all flex items-center gap-2"
            >
              <Pause className="w-4 h-4 fill-white" />
              PAUSE
            </button>
          )}

          <button
            onClick={resetSimulation}
            className="px-4 py-2.5 bg-white hover:bg-slate-50 text-slate-700 font-bold text-sm rounded-xl border border-sky-200 transition-colors flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4 text-slate-500" />
            RESET
          </button>
        </div>

        {/* Speed */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 flex items-center gap-1">
            <FastForward className="w-3.5 h-3.5 text-sky-500" />
            Speed:
          </span>

          <div className="flex items-center gap-1 bg-sky-50 p-1 rounded-xl border border-sky-100">
            {speeds.map((s) => (
              <button
                key={s}
                onClick={() => setSimulationSpeed(s)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                  simulationSpeed === s
                    ? 'bg-sky-600 text-white shadow-md'
                    : 'text-slate-500 hover:text-sky-700 hover:bg-white'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}