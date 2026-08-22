import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { PatientProvider } from './context/PatientContext';
import { Header } from './components/common/Header';
import { CommandCenter } from './pages/CommandCenter';
import { PatientDetail } from './pages/PatientDetail';
import { MobileAlert } from './pages/MobileAlert';
import { Simulator } from './pages/Simulator';

export function App() {
  return (
    <PatientProvider>
      <Router>
        <div className="min-h-screen bg-[#D6F0FF] text-slate-900 flex flex-col font-sans">
          <Header />

          <main className="flex-1">
            <Routes>
              <Route path="/" element={<CommandCenter />} />
              <Route path="/patient/:patientId" element={<PatientDetail />} />
              <Route path="/mobile-alert/:alertId" element={<MobileAlert />} />
              <Route path="/simulator" element={<Simulator />} />
            </Routes>
          </main>
        </div>
      </Router>
    </PatientProvider>
  );
}

export default App;