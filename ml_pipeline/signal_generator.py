"""
Biomedical Waveform Generator
Generates continuous high-frequency mathematical waveforms for:
- ECG (Electrocardiogram - Lead II with P, Q, R, S, T waves)
- PPG (Photoplethysmogram - systolic peak, dicrotic notch, diastolic wave)
- Resp (Respiration thoracic impedance wave)
"""

import math
import numpy as np

class WaveformGenerator:
    def __init__(self, sampling_rate_hz: int = 125):
        self.fs = sampling_rate_hz
        self.phase_ecg = 0.0
        self.phase_ppg = 0.0
        self.phase_resp = 0.0

    def generate_point(self, hr: float = 75.0, spo2: float = 98.0, resp_rate: float = 16.0, condition: str = "NORMAL"):
        """
        Generate 1 synchronized point for ECG, PPG, and Resp given current patient vitals.
        Returns: tuple of (ecg_val, ppg_val, resp_val)
        """
        # Frequency in Hz
        freq_cardiac = max(30.0, min(220.0, hr)) / 60.0
        freq_resp = max(6.0, min(50.0, resp_rate)) / 60.0

        # Step phase
        dt = 1.0 / self.fs
        self.phase_ecg = (self.phase_ecg + 2 * math.pi * freq_cardiac * dt) % (2 * math.pi)
        self.phase_ppg = (self.phase_ppg + 2 * math.pi * freq_cardiac * dt) % (2 * math.pi)
        self.phase_resp = (self.phase_resp + 2 * math.pi * freq_resp * dt) % (2 * math.pi)

        # Baseline wander from breathing
        resp_mod = 0.08 * math.sin(self.phase_resp)

        # ECG Lead II Synthesis using Gaussian wavelets
        ecg_val = self._synthesize_ecg(self.phase_ecg, condition) + resp_mod
        
        # PPG Synthesis (Blood volume pulse with dicrotic notch)
        ppg_val = self._synthesize_ppg(self.phase_ppg, spo2)
        
        # Respiration Wave
        resp_val = (math.sin(self.phase_resp) + 1.0) * 0.5

        return float(ecg_val), float(ppg_val), float(resp_val)

    def _synthesize_ecg(self, phase: float, condition: str) -> float:
        # Normalize phase to 0 -> 1 range
        t = phase / (2 * math.pi)
        
        # Noise component
        noise = (np.random.rand() - 0.5) * 0.02
        
        if condition == "VFIB": # Ventricular Fibrillation (chaotic)
            return float(0.4 * math.sin(phase * 4.5) + 0.3 * math.sin(phase * 7.2) + noise * 3)
        elif condition == "ASYSTOLE": # Flatline with low hum
            return float(noise * 0.5)

        # Normal P-Q-R-S-T wave model
        # P-wave: center 0.20, width 0.04, amp 0.15
        p = 0.15 * math.exp(-((t - 0.20) ** 2) / (2 * (0.025 ** 2)))
        
        # Q-wave: center 0.35, width 0.015, amp -0.15
        q = -0.15 * math.exp(-((t - 0.35) ** 2) / (2 * (0.012 ** 2)))
        
        # R-wave (Main spike): center 0.40, width 0.018, amp 1.0
        r_amp = 1.0 if condition != "ISCHEMIA" else 0.6
        r = r_amp * math.exp(-((t - 0.40) ** 2) / (2 * (0.015 ** 2)))
        
        # S-wave: center 0.45, width 0.02, amp -0.3
        s = -0.28 * math.exp(-((t - 0.45) ** 2) / (2 * (0.015 ** 2)))
        
        # ST Segment elevation / depression
        st_shift = 0.25 if condition == "STEMI" else (-0.15 if condition == "ISCHEMIA" else 0.0)
        st = st_shift * math.exp(-((t - 0.53) ** 2) / (2 * (0.06 ** 2)))
        
        # T-wave: center 0.65, width 0.07, amp 0.3
        t_amp = 0.45 if condition == "HYPERKALEMIA" else 0.28
        tw = t_amp * math.exp(-((t - 0.65) ** 2) / (2 * (0.045 ** 2)))

        return p + q + r + s + st + tw + noise

    def _synthesize_ppg(self, phase: float, spo2: float) -> float:
        t = phase / (2 * math.pi)
        
        # Amplitude modulated by SpO2
        amp_scale = max(0.2, min(1.0, (spo2 - 60) / 40.0))
        
        # Systolic upstroke & peak
        systolic = 0.85 * math.exp(-((t - 0.28) ** 2) / (2 * (0.07 ** 2)))
        
        # Dicrotic notch & reflected diastolic wave
        diastolic = 0.38 * math.exp(-((t - 0.55) ** 2) / (2 * (0.09 ** 2)))
        
        noise = (np.random.rand() - 0.5) * 0.01
        raw_ppg = (systolic + diastolic) * amp_scale + noise
        return max(0.0, min(1.0, raw_ppg))
