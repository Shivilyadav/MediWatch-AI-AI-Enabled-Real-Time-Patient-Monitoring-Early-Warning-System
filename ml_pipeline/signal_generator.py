import numpy as np
import time

class VitalSignalGenerator:
    """
    Generates realistic synthetic physiological signals and vital parameters for patient monitoring.
    Includes mathematical modeling of ECG PQRST waveforms and Photoplethysmogram (PPG) waves.
    """
    
    def __init__(self, heart_rate=72, spo2=98, sys_bp=120, dia_bp=80, resp_rate=16, temp=36.8):
        self.heart_rate = heart_rate
        self.spo2 = spo2
        self.sys_bp = sys_bp
        self.dia_bp = dia_bp
        self.resp_rate = resp_rate
        self.temp = temp
        self.condition = "Normal" # Normal, Bradycardia, Tachycardia, Arrhythmia, Hypoxia, Fever, Cardiac Arrest
        self.phase = 0.0

    def set_condition(self, condition: str):
        """Inject physiological conditions into the generator."""
        self.condition = condition
        cond_lower = condition.lower()
        if "bradycardia" in cond_lower:
            self.heart_rate = 42
            self.spo2 = 96
        elif "tachycardia" in cond_lower:
            self.heart_rate = 145
            self.spo2 = 95
        elif "hypoxia" in cond_lower:
            self.heart_rate = 110
            self.spo2 = 82
        elif "arrhythmia" in cond_lower:
            self.heart_rate = 88
            self.spo2 = 94
        elif "fever" in cond_lower or "hyperthermia" in cond_lower:
            self.heart_rate = 105
            self.temp = 39.4
            self.sys_bp = 135
        elif "normal" in cond_lower:
            self.heart_rate = 72
            self.spo2 = 98
            self.sys_bp = 120
            self.dia_bp = 80
            self.resp_rate = 16
            self.temp = 36.8

    def generate_ecg_sample(self, t: float) -> float:
        """
        Synthesizes an ECG waveform sample at timestamp t using a sum-of-gaussians model for PQRST complex.
        """
        period = 60.0 / max(30, self.heart_rate)
        if self.condition == "Arrhythmia":
            # Add irregular beat timing perturbation
            period += 0.15 * np.sin(2 * np.pi * t * 0.7)
            
        phase = (t % period) / period
        
        # PQRST Gaussian parameters: (amplitude, center_phase, width)
        components = [
            (0.15, 0.15, 0.03),  # P wave
            (-0.15, 0.38, 0.015), # Q wave
            (1.25, 0.40, 0.02),   # R wave peak
            (-0.35, 0.42, 0.02),  # S wave
            (0.25, 0.65, 0.06),   # T wave
        ]
        
        signal = 0.0
        for amp, mu, sig in components:
            signal += amp * np.exp(-((phase - mu) ** 2) / (2 * sig ** 2))
            
        # Add high-frequency baseline muscle noise / tremor
        noise = np.random.normal(0, 0.02)
        return float(signal + noise)

    def generate_ppg_sample(self, t: float) -> float:
        """
        Synthesizes a PPG (SpO2 optical pulse) wave sample.
        """
        period = 60.0 / max(30, self.heart_rate)
        phase = (t % period) / period
        
        systolic_peak = np.exp(-((phase - 0.3) ** 2) / (2 * 0.05 ** 2))
        dicrotic_notch = 0.3 * np.exp(-((phase - 0.5) ** 2) / (2 * 0.04 ** 2))
        
        amplitude = (self.spo2 / 100.0)
        signal = amplitude * (systolic_peak + dicrotic_notch)
        noise = np.random.normal(0, 0.01)
        return float(signal + noise)

    def get_vital_snapshot(self) -> dict:
        """
        Returns a snapshot of instantaneous vital parameters with slight natural baseline variation.
        """
        hr_var = np.random.normal(0, 1.2)
        spo2_var = np.random.normal(0, 0.3)
        sys_var = np.random.normal(0, 1.5)
        dia_var = np.random.normal(0, 1.0)
        
        curr_hr = max(30, int(round(self.heart_rate + hr_var)))
        curr_spo2 = min(100, max(60, int(round(self.spo2 + spo2_var))))
        curr_sys = max(60, int(round(self.sys_bp + sys_var)))
        curr_dia = max(40, int(round(self.dia_bp + dia_var)))
        curr_rr = max(6, int(round(self.resp_rate + np.random.normal(0, 0.5))))
        curr_temp = round(float(self.temp + np.random.normal(0, 0.05)), 1)
        
        mean_arterial_pressure = int(round(curr_dia + (curr_sys - curr_dia) / 3.0))
        
        return {
            "heart_rate": curr_hr,
            "spo2": curr_spo2,
            "sys_bp": curr_sys,
            "dia_bp": curr_dia,
            "map": mean_arterial_pressure,
            "resp_rate": curr_rr,
            "temp": curr_temp,
            "condition": self.condition
        }
