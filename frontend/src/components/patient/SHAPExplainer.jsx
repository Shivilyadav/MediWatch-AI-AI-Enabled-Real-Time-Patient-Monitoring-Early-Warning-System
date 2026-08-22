import React from 'react';
import { Brain, Info, Sparkles } from 'lucide-react';
import { usePatientContext } from '../../context/PatientContext';

export function SHAPExplainer({ explanations = [] }) {
  const { isDemoMode } = usePatientContext();

  return (
    <div className="bg-white border border-blue-100 rounded-xl p-5 shadow-lg shadow-blue-100/50 backdrop-blur-md mb-6">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-blue-100 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-600">
            <Brain className="w-4 h-4" />
          </div>

          <div>
            <h2 className="text-sm font-bold text-slate-800 tracking-wide">
              Why is this patient at risk?
            </h2>

            <p className="text-[11px] text-slate-500">
              Explainable AI (SHAP) feature attribution breakdown
            </p>
          </div>
        </div>

        {/* Demo Mode / Live ML Label */}
        <span
          className={`px-2.5 py-1 rounded-lg text-xs font-semibold border flex items-center gap-1.5 ${
            isDemoMode
              ? 'bg-amber-50 border-amber-200 text-amber-700'
              : 'bg-purple-50 border-purple-200 text-purple-700'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          {isDemoMode ? 'Demo Explanation' : 'XGBoost SHAP Live Output'}
        </span>
      </div>

      {/* Factors List */}
      <div className="space-y-4">
        {explanations.length === 0 ? (
          <p className="text-xs text-slate-500 italic">
            No significant risk factor contributions calculated.
          </p>
        ) : (
          explanations.map((item, idx) => {
            const isPositive = item.contribution > 0;

            const percentWidth = Math.min(
              100,
              Math.max(
                10,
                Math.round(Math.abs(item.contribution) * 100 * 2.5)
              )
            );

            return (
              <div
                key={idx}
                className="p-3 bg-blue-50/50 border border-blue-100 rounded-xl"
              >
                <div className="flex items-center justify-between mb-1.5">
                  
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-800">
                      {item.feature}
                    </span>

                    <span className="text-xs text-slate-500 font-mono">
                      ({item.value})
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                        isPositive
                          ? 'bg-red-50 border-red-200 text-red-600'
                          : 'bg-emerald-50 border-emerald-200 text-emerald-600'
                      }`}
                    >
                      {item.status}
                    </span>

                    <span
                      className={`text-xs font-black font-mono ${
                        isPositive
                          ? 'text-red-500'
                          : 'text-emerald-600'
                      }`}
                    >
                      {isPositive ? '+' : ''}
                      {item.contribution.toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-2 bg-blue-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ease-out ${
                      isPositive
                        ? 'bg-gradient-to-r from-orange-400 to-red-500'
                        : 'bg-gradient-to-r from-emerald-400 to-teal-500'
                    }`}
                    style={{ width: `${percentWidth}%` }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Explanation */}
      <div className="mt-4 pt-3 border-t border-blue-100 flex items-center gap-2 text-[11px] text-slate-500">
        <Info className="w-3.5 h-3.5 text-blue-500 shrink-0" />

        <span>
          Positive SHAP values push predicted risk higher, indicating
          primary drivers of clinical deterioration.
        </span>
      </div>
    </div>
  );
}