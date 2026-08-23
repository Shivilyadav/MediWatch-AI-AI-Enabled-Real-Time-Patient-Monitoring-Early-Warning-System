import { usePatientContext } from '../context/PatientContext';

export function useWebSocket() {
  const { connectionStatus, isDemoMode, setIsDemoMode } = usePatientContext();

  return {
    connectionStatus,
    isDemoMode,
    setIsDemoMode,
    isConnected: connectionStatus === 'CONNECTED'
  };
}
