import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Activity,
  ShieldAlert,
  Sliders,
  Smartphone,
  Radio
} from 'lucide-react';
import { usePatientContext } from '../../context/PatientContext';
import { ConnectionStatus } from './ConnectionStatus';
import { PrototypeDisclaimer } from './PrototypeDisclaimer';

export function Header() {
  const location = useLocation();

  const {
    connectionStatus,
    isDemoMode,
    setIsDemoMode,
    selectedPatientId
  } = usePatientContext();

  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const navLinks = [
    {
      path: '/',
      label: 'Command Center',
      icon: Activity
    },
    {
      path: `/patient/${selectedPatientId}`,
      label: 'Patient Detail',
      icon: ShieldAlert
    },
    {
      path: '/simulator',
      label: 'Patient Simulator',
      icon: Sliders
    },
    {
      path: '/mobile-alert/ALT-P003-01',
      label: 'Mobile Alert View',
      icon: Smartphone
    }
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-sky-100 shadow-md">
      <PrototypeDisclaimer />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">

        {/* Left Branding */}
        <div className="flex items-center gap-3">

          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-cyan-400 p-0.5 shadow-lg shadow-sky-200 flex items-center justify-center">
            <div className="w-full h-full bg-white rounded-[10px] flex items-center justify-center">
              <Activity className="w-5 h-5 text-sky-600 animate-pulse" />
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2">

              <h1 className="text-lg font-bold text-slate-900 tracking-wider flex items-center gap-2">
                MEDIWATCH
                <span className="text-sky-600 font-extrabold">
                  AI
                </span>
              </h1>

              {/* LIVE Indicator */}
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 border border-red-200 text-red-600 text-[10px] font-bold rounded-full tracking-wider uppercase animate-pulse">
                <Radio className="w-3 h-3 text-red-500 animate-ping" />
                LIVE
              </span>

            </div>

            <p className="text-xs text-slate-500 font-medium hidden sm:block">
              Real-Time Patient Monitoring & Early Warning System
            </p>
          </div>
        </div>

        {/* Center Navigation */}
        <nav className="hidden md:flex items-center gap-1 bg-sky-50 p-1 rounded-xl border border-sky-100">

          {navLinks.map((link) => {
            const Icon = link.icon;

            const isActive =
              location.pathname === link.path ||
              (
                link.path.startsWith('/patient') &&
                location.pathname.startsWith('/patient')
              );

            return (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive ? 'bg-sky-600 text-white shadow-md shadow-sky-200' : 'text-slate-600 hover:text-sky-700 hover:bg-white'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {link.label}
              </Link>
            );
          })}

        </nav>

        {/* Right Status Controls */}
        <div className="flex items-center gap-3">

          <ConnectionStatus
            status={connectionStatus}
            isDemoMode={isDemoMode}
          />

          {/* Mode Toggle */}
          <button
            onClick={() => setIsDemoMode(!isDemoMode)}
            className="text-xs px-2.5 py-1.5 rounded-lg font-semibold border border-sky-200 bg-sky-50 hover:bg-sky-100 text-sky-700 transition-colors hidden lg:block"
            title="Toggle between independent Demo Mode and live FastAPI backend mode"
          >
            {isDemoMode
              ? 'Switch to Live Mode'
              : 'Switch to Demo Mode'}
          </button>

          {/* System Clock */}
          <div className="text-xs font-mono font-bold text-slate-700 bg-sky-50 border border-sky-100 px-2.5 py-1.5 rounded-lg hidden sm:block">
            {time.toLocaleTimeString()}
          </div>

        </div>

      </div>

      {/* Mobile Navigation Sub-Bar */}
      <div className="md:hidden flex items-center justify-around bg-white px-2 py-2 border-t border-sky-100 text-xs font-semibold text-slate-500">

        {navLinks.map((link) => {
          const Icon = link.icon;

          const isActive =
            location.pathname === link.path ||
            (
              link.path.startsWith('/patient') &&
              location.pathname.startsWith('/patient')
            );

          return (
            <Link
              key={link.path}
              to={link.path}
              className={`flex flex-col items-center gap-1 py-1 px-2 rounded-lg ${
                isActive ? 'text-sky-600 font-bold bg-sky-50' : 'text-slate-500'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="text-[10px]">
                {link.label}
              </span>
            </Link>
          );
        })}

      </div>
    </header>
  );
}