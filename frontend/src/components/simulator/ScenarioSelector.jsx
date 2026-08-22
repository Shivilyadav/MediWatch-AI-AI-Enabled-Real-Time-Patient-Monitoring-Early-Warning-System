import React from 'react';
import { SCENARIOS } from '../../simulator/scenarios';
import { usePatientContext } from '../../context/PatientContext';
import {
  Layers,
  Activity,
  AlertTriangle,
  ShieldCheck,
  HeartPulse,
  RefreshCw
} from 'lucide-react';

export function ScenarioSelector() {
  const { activeScenarioId, changeScenario } = usePatientContext();

  const getScenarioIcon = (id) => {
    switch (id) {
      case 'DETERIORATING':
        return AlertTriangle;
      case 'SEPSIS_ONSET':
        return HeartPulse;
      case 'RESPIRATORY_FAILURE':
        return Activity;
      case 'RECOVERING':
        return RefreshCw;
      case 'NORMAL':
      default:
        return ShieldCheck;
    }
  };

  return (
    <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-md shadow-sky-100/40 mb-6">

      <div className="flex items-center gap-2 pb-3 border-b border-sky-100 mb-4">
        <Layers className="w-4 h-4 text-sky-600" />

        <h2 className="text-sm font-bold text-slate-800 tracking-wide">
          Physiological Simulation Scenarios
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">

        {Object.values(SCENARIOS).map((scenario) => {
          const isSelected = activeScenarioId === scenario.id;
          const Icon = getScenarioIcon(scenario.id);

          return (
            <button
              key={scenario.id}
              onClick={() => changeScenario(scenario.id)}
              className={`p-3.5 rounded-xl border text-left transition-all ${
                isSelected
                  ? 'bg-sky-50 border-sky-500 shadow-lg shadow-sky-100 ring-1 ring-sky-500'
                  : 'bg-white border-sky-100 hover:border-sky-300 hover:bg-sky-50/50'
              }`}
            >

              <div className="flex items-center gap-2 mb-2">
                <Icon
                  className={`w-4 h-4 ${
                    isSelected
                      ? 'text-sky-600'
                      : 'text-slate-400'
                  }`}
                />

                <span
                  className={`text-xs font-bold ${
                    isSelected
                      ? 'text-sky-700'
                      : 'text-slate-800'
                  }`}
                >
                  {scenario.name}
                </span>
              </div>

              <p className="text-[10px] text-slate-500 line-clamp-3 leading-normal">
                {scenario.description}
              </p>

            </button>
          );
        })}

      </div>
    </div>
  );
}