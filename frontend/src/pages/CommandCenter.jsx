import React from 'react';
import { Activity, ArrowUpRight, BrainCircuit, CircleDot, ShieldCheck, Sparkles } from 'lucide-react';
import { KPISection } from '../components/dashboard/KPISection';
import { PatientGrid } from '../components/dashboard/PatientGrid';
import { AlertQueue } from '../components/dashboard/AlertQueue';
import { ClinicalHeart3D } from '../components/visuals/ClinicalHeart3D';
import { usePatientContext } from '../context/PatientContext';

export function CommandCenter() {
  const { summaryMetrics } = usePatientContext();
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <section className="medical-hero rounded-[28px] px-5 py-5 sm:px-8 sm:py-7 mb-7">
        <div className="relative z-10 grid lg:grid-cols-[1fr_300px] items-center gap-5">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-3"><span className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.16em] text-sky-700"><CircleDot className="h-3 w-3" /> Clinical intelligence layer</span><span className="text-[11px] text-slate-500">Last sync · just now</span></div>
            <h1 className="max-w-2xl text-3xl sm:text-4xl font-black tracking-[-.04em] text-slate-900 leading-tight">See deterioration <span className="text-sky-600">before it becomes critical.</span></h1>
            <p className="max-w-xl mt-3 text-sm sm:text-[15px] leading-6 text-slate-600">Mediwatch AI turns continuous bedside signals into one calm, actionable view for your care team.</p>
            <div className="flex flex-wrap gap-3 mt-5"><div className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700"><ShieldCheck className="h-4 w-4" /> {summaryMetrics.normalCount} stable patients</div><div className="inline-flex items-center gap-2 rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-xs font-semibold text-violet-700"><BrainCircuit className="h-4 w-4" /> AI risk engine online</div><div className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-white/70 px-3 py-2 text-xs font-semibold text-slate-600"><Activity className="h-4 w-4 text-sky-600" /> 24/7 surveillance</div></div>
          </div>
          <div className="flex flex-col items-center justify-center"><ClinicalHeart3D /><div className="-mt-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[.16em] text-sky-700"><Sparkles className="h-3.5 w-3.5" /> Live 3D telemetry model</div></div>
        </div>
      </section>

      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-5"><div><p className="text-[10px] font-bold uppercase tracking-[.2em] text-sky-600">Overview / Live floor</p><h2 className="mt-1 text-xl sm:text-2xl font-black tracking-tight text-slate-900">Hospital command center</h2><p className="mt-1 text-xs sm:text-sm text-slate-600">Real-time vital signs, AI risk scoring, and early warning alerts across ICU and ward units.</p></div><div className="inline-flex items-center gap-2 text-xs font-medium text-slate-500"><span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,.65)]" /> Monitoring {summaryMetrics.total} beds <ArrowUpRight className="h-3.5 w-3.5 text-sky-600" /></div></div>
      <KPISection />
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start"><div className="lg:col-span-8"><div className="flex items-center justify-between mb-3"><h2 className="text-sm font-bold text-slate-800 tracking-wide uppercase">Monitored patient units</h2><span className="text-xs text-slate-500">Select a card to open clinical detail</span></div><PatientGrid /></div><div className="lg:col-span-4 lg:sticky lg:top-24"><AlertQueue /></div></div>
    </div>
  );
}
