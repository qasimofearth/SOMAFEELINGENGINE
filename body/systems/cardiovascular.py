"""
cardiovascular.py — Cardiovascular System

Heart, blood vessels, blood pressure, cardiac output.

Models:
  - Heart rate (bpm) with baroreflex negative feedback
  - Stroke volume and cardiac output
  - Systolic/diastolic blood pressure (Windkessel model)
  - Peripheral vascular resistance
  - Coronary blood flow
  - Respiratory sinus arrhythmia (RSA) — HR couples to breathing
  - Animated beat phase for visualization
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class CardiovascularSystem:

    def __init__(self):
        # Vital signs
        self.heart_rate   = 70.0    # bpm
        self.stroke_volume = 70.0   # mL per beat
        self.cardiac_output = 4.9   # L/min
        self.systolic_bp   = 120.0  # mmHg
        self.diastolic_bp  = 80.0   # mmHg
        self.mean_arterial_pressure = 93.3

        # Internal state
        self.contractility  = 0.65  # [0,1]
        self.ejection_frac  = 0.60  # [0,1]
        self.peripheral_res = 0.50  # normalized peripheral resistance
        self.coronary_flow  = 0.60
        self.venous_tone    = 0.50
        self.beat_phase     = 0.0   # [0, 2π] — for animation
        self.t_ms           = 0.0

        # Baroreceptor state
        self._baro_signal   = 0.0

    def tick(self, dt_ms: float, ans_drives: Dict[str, float],
             resp_phase: float = 0.0):
        """
        ans_drives: from ANSSystem.organ_drives
        resp_phase: breathing phase [0,1] for RSA coupling
        """
        hr_drive  = ans_drives.get("heart_rate_drive", 0.0)
        cont_drive = ans_drives.get("cardiac_contractility", 0.0)
        res_drive = ans_drives.get("peripheral_resistance", 0.0)

        # Target heart rate — baseline 70 ± 40 bpm with ANS
        hr_target = 70.0 + hr_drive * 40.0
        # Respiratory Sinus Arrhythmia: +5 bpm peak inhale, -5 bpm peak exhale
        rsa = 5.0 * math.sin(resp_phase * 2 * math.pi)
        hr_target += rsa

        # Baroreflex: high BP → lower HR (negative feedback)
        baro_error = (self.systolic_bp - 120.0) * 0.12
        self._baro_signal = _lag(self._baro_signal, baro_error, 5.0)
        hr_target -= self._baro_signal

        hr_target = max(40.0, min(180.0, hr_target))

        tau_hr = max(1.0, dt_ms / 100.0) * 15.0   # ~1.5s time constant
        self.heart_rate = _lag(self.heart_rate, hr_target, tau_hr)

        # Contractility
        cont_target = _clamp(0.65 + cont_drive * 0.25)
        self.contractility = _lag(self.contractility, cont_target, 12.0)

        # Stroke volume: driven by preload, contractility, afterload
        sv_target = 70.0 * self.contractility / 0.65 * (1.0 - res_drive * 0.15)
        sv_target = max(20.0, min(130.0, sv_target))
        self.stroke_volume = _lag(self.stroke_volume, sv_target, 10.0)

        # Cardiac output
        self.cardiac_output = (self.heart_rate * self.stroke_volume) / 1000.0

        # Peripheral resistance
        res_target = _clamp(0.50 + res_drive * 0.40)
        self.peripheral_res = _lag(self.peripheral_res, res_target, 8.0)

        # Blood pressure (simplified Windkessel)
        # Systolic driven by CO and peripheral resistance
        sys_target = 80.0 + self.cardiac_output * 8.5 + self.peripheral_res * 35.0
        dia_target = sys_target * 0.67 * (0.85 + self.peripheral_res * 0.15)
        sys_target = max(70.0, min(210.0, sys_target))
        dia_target = max(40.0, min(130.0, dia_target))
        self.systolic_bp  = _lag(self.systolic_bp,  sys_target, 8.0)
        self.diastolic_bp = _lag(self.diastolic_bp, dia_target, 10.0)
        self.mean_arterial_pressure = self.diastolic_bp + (self.systolic_bp - self.diastolic_bp) / 3.0

        # Coronary flow — inversely related to peripheral vasoconstriction
        cor_target = _clamp(0.60 + cont_drive * 0.20 - res_drive * 0.10)
        self.coronary_flow = _lag(self.coronary_flow, cor_target, 6.0)

        # Ejection fraction
        ef_target = _clamp(0.55 + self.contractility * 0.10 - res_drive * 0.08)
        self.ejection_frac = _lag(self.ejection_frac, ef_target, 12.0)

        # Beat phase: increments at heart rate (for animation)
        beats_per_ms = self.heart_rate / 60000.0
        self.beat_phase = (self.beat_phase + beats_per_ms * dt_ms * 2 * math.pi) % (2 * math.pi)
        self.t_ms += dt_ms

    def get_beat_pulse(self) -> float:
        """Returns [0,1] pulse intensity for animation — peaks at systole."""
        # Sharp systolic peak then dicrotic notch shape
        p = self.beat_phase / (2 * math.pi)  # [0,1]
        if p < 0.15:
            return math.sin(p / 0.15 * math.pi)
        elif p < 0.25:
            return 0.25 + (0.25 - (p - 0.15) / 0.10 * 0.25)
        elif p < 0.35:
            return 0.18 + math.sin((p - 0.25) / 0.10 * math.pi) * 0.12
        else:
            return 0.05

    def get_params(self) -> Dict:
        return {
            "heart_rate": round(self.heart_rate, 1),
            "stroke_volume": round(self.stroke_volume, 1),
            "cardiac_output": round(self.cardiac_output, 2),
            "systolic_bp": round(self.systolic_bp, 1),
            "diastolic_bp": round(self.diastolic_bp, 1),
            "mean_arterial_pressure": round(self.mean_arterial_pressure, 1),
            "contractility": round(self.contractility, 3),
            "ejection_fraction": round(self.ejection_frac, 3),
            "peripheral_resistance": round(self.peripheral_res, 3),
            "coronary_flow": round(self.coronary_flow, 3),
            "beat_pulse": round(self.get_beat_pulse(), 3),
            "beat_phase": round(self.beat_phase, 3),
        }
