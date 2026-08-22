import React from 'react';
import { Bell, Clock, ChevronRight, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { usePatientContext } from '../../context/PatientContext';
import { formatTimeAgo, getRiskColor } from '../../utils/formatters';

export function AlertQueue() {
  const navigate = useNavigate();
  const { activeAlerts, acknowledgeAlertAction } = usePatientContext();

  const sortedAlerts = [...activeAlerts].sort(
    (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
  );

  return (
    <div className="bg-white border border-sky-200 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-sky-100 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-orange-50 border border-orange-200">
            <Bell className="w-4 h-4 text-orange-500" />
          </div>

          <div>
            <h2 className="text-sm font-extrabold text-slate-900">
              Active Alert Queue
            </h2>

            <p className="text-[10px] text-slate-500 font-medium">
              Requires clinical attention
            </p>
          </div>
        </div>

        <span className="px-2 py-1 rounded-lg bg-orange-50 border border-orange-200 text-orange-600 text-xs font-black">
          {activeAlerts.length}
        </span>
      </div>

      {/* Alerts */}
      <div className="space-y-3">
        {sortedAlerts.length === 0 ? (
          <div className="py-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />

            <p className="text-sm font-bold text-slate-700">
              No Active Alerts
            </p>

            <p className="text-[11px] text-slate-500 mt-1">
              All monitored patients are currently stable.
            </p>
          </div>
        ) : (
          sortedAlerts.map((alert) => {
            const styles = getRiskColor(alert.severity);

            return (
              <div
                key={alert.alert_id}
                className={`rounded-xl border p-3 bg-white transition-all hover:shadow-md ${styles.border}`}
              >
                {/* Alert Header */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`px-2 py-0.5 rounded-md border text-[10px] font-black uppercase ${styles.badgeBg} ${styles.badgeText} ${styles.border}`}
                    >
                      {alert.severity}
                    </span>

                    <span className="text-xs font-extrabold text-slate-900 truncate">
                      {alert.patient_id}
                    </span>
                  </div>

                  <span className="text-[10px] text-slate-400 whitespace-nowrap">
                    {formatTimeAgo(alert.timestamp)}
                  </span>
                </div>

                {/* Patient / Reason */}
                <div className="mb-3">
                  <p className="text-xs font-bold text-slate-800 mb-1">
                    {alert.patient_name || 'Patient Alert'}
                  </p>

                  <p className="text-[11px] text-slate-500 leading-relaxed">
                    {alert.reason}
                  </p>
                </div>

                {/* Risk Score */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-1 text-[10px] text-slate-500">
                    <Clock className="w-3 h-3" />
                    Alert Time
                  </div>

                  <span className={`text-xs font-black ${styles.text}`}>
                    Risk {Math.round((alert.risk_score || 0) * 100)}%
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      navigate(`/patient/${alert.patient_id}`)
                    }
                    className="flex-1 px-3 py-2 rounded-lg bg-sky-50 border border-sky-200 text-sky-700 text-[11px] font-bold hover:bg-sky-100 transition-colors flex items-center justify-center gap-1"
                  >
                    View Patient
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() =>
                      acknowledgeAlertAction(alert.alert_id)
                    }
                    className="px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-[11px] font-bold transition-colors"
                  >
                    ACK
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      {sortedAlerts.length > 0 && (
        <div className="mt-4 pt-3 border-t border-sky-100">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-slate-400 font-medium">
              Showing active unacknowledged alerts
            </span>

            <button
              onClick={() =>
                document
                  .getElementById('alert-history')
                  ?.scrollIntoView({ behavior: 'smooth' })
              }
              className="text-[10px] font-bold text-sky-600 hover:text-sky-700"
            >
              View History
            </button>
          </div>
        </div>
      )}
    </div>
  );
}