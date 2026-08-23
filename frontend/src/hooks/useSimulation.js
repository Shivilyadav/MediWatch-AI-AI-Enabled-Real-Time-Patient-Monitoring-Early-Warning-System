import { usePatientContext } from '../context/PatientContext';

export function useSimulation() {
  const {
    isSimulationRunning,
    startSimulation,
    pauseSimulation,
    resetSimulation,
    simulationSpeed,
    setSimulationSpeed,
    activeScenarioId,
    changeScenario,
    simulationStep,
    virtualTime
  } = usePatientContext();

  return {
    isSimulationRunning,
    startSimulation,
    pauseSimulation,
    resetSimulation,
    simulationSpeed,
    setSimulationSpeed,
    activeScenarioId,
    changeScenario,
    simulationStep,
    virtualTime
  };
}
