import React from 'react';
import { Bell, CheckCircle2, Clock, Check } from 'lucide-react';
import { usePatientContext } from '../../context/PatientContext';
import { formatTimeAgo, getRiskColor } from '../../utils/formatters';

export function AlertHistory({ alerts = [] }) {
  const { acknowledgeAlertAction } = usePatientContext();

  return (
    <div className="bg-white border border-blue-100 rounded-xl p-5 shadow-lg shadow-blue-100/50">

      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-blue-100 mb-4">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-orange-500" />

          <h2 className="text-sm font-bold text-slate-800 tracking-wide">
            Patient Alert Log & Audit History
          </h2>
        </div>

        <span className="text-xs text-slate-500 font-semibold">
          {alerts.length} Total Logged
        </span>
      </div>

      {/* Alert List */}
      <div className="space-y-3">
        {alerts.length === 0 ? (
          <p className="text-xs text-slate-500 italic p-4 text-center">
            No alert history recorded for this patient.
          </p>
        ) : (
          alerts.map((alert) => {
            const styles = getRiskColor(alert.severity);
            const isAck = alert.status === 'ACKNOWLEDGED';
            const isResolved = alert.status === 'RESOLVED';

            return (
              <div
                key={alert.alert_id}
                className="p-3.5 rounded-xl border border-blue-100 bg-blue-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >

                {/* Alert Information */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">

                    <span
                      className={`text-[10px] font-black px-2 py-0.5 rounded border uppercase ${styles.badgeBg} ${styles.badgeText} ${styles.border}`}
                    >
                      {alert.severity}
                    </span>

                    <span className="text-xs font-bold text-slate-800">
                      {alert.reason}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[11px] text-slate-500">
                    <span className="flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {formatTimeAgo(alert.timestamp)}
                    </span>

                    <span>•</span>

                    <span>
                      Risk: {Math.round(alert.risk_score * 100)}%
                    </span>
                  </div>
                </div>

                {/* Status & Action */}
                <div className="flex items-center gap-2 shrink-0">

                  {isResolved ? (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-100 text-slate-500 border border-slate-200 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
                      RESOLVED
                    </span>
                  ) : isAck ? (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-blue-50 text-blue-600 border border-blue-200 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                      ACKNOWLEDGED
                    </span>
                  ) : (
                    <button
                      onClick={() =>
                        acknowledgeAlertAction(alert.alert_id)
                      }
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs rounded-lg shadow-md transition-colors flex items-center gap-1"
                    >
                      <Check className="w-3.5 h-3.5 text-white" />
                      ACKNOWLEDGE
                    </button>
                  )}

                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}