import React from 'react';
import { PatientCard } from './PatientCard';
import { usePatientContext } from '../../context/PatientContext';

export function PatientGrid() {
  const { patients } = usePatientContext();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-2 2xl:grid-cols-3 gap-4">
      {patients.map((patient) => (
        <PatientCard key={patient.patient_id} patient={patient} />
      ))}
    </div>
  );
}
