import React from 'react';
import { Users, CheckCircle2, AlertTriangle, AlertCircle, Bell } from 'lucide-react';
import { usePatientContext } from '../../context/PatientContext';

export function KPISection() {
  const { summaryMetrics } = usePatientContext();
  const kpis = [
    { title:'Total Patients', value:summaryMetrics.total, subtitle:'Active ICU & Ward beds', icon:Users, color:'border-blue-200 text-blue-600 bg-blue-50' },
    { title:'Normal Status', value:summaryMetrics.normalCount, subtitle:'Hemodynamically stable', icon:CheckCircle2, color:'border-emerald-200 text-emerald-600 bg-emerald-50' },
    { title:'Medium Risk', value:summaryMetrics.mediumCount, subtitle:'Requires observation', icon:AlertTriangle, color:'border-yellow-200 text-yellow-600 bg-yellow-50' },
    { title:'High / Critical Risk', value:summaryMetrics.criticalCount, subtitle:'Deterioration detected', icon:AlertCircle, color:'border-red-200 text-red-600 bg-red-50 animate-pulse' },
    { title:'Active Alerts', value:summaryMetrics.activeAlertsCount, subtitle:'Unacknowledged', icon:Bell, color:summaryMetrics.activeAlertsCount > 0 ? 'border-orange-200 text-orange-600 bg-orange-50' : 'border-blue-100 text-slate-500 bg-slate-50' }
  ];
  return <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">{kpis.map(({ title, value, subtitle, icon: Icon, color }) => <div key={title} className={`p-4 rounded-xl border shadow-md shadow-blue-100/30 transition-transform hover:-translate-y-0.5 ${color}`}><div className="flex items-center justify-between mb-2"><span className="text-xs font-semibold text-slate-500 tracking-wide uppercase">{title}</span><Icon className="w-4 h-4" /></div><div className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-800 mb-0.5">{value}</div><div className="text-[10px] text-slate-500 font-medium">{subtitle}</div></div>)}</div>;
}
