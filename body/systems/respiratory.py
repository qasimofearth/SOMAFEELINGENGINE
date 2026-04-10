"""
respiratory.py — Respiratory System

Lungs, diaphragm, airway, gas exchange.

Models:
  - Respiratory rate (breaths/min)
  - Tidal volume (mL)
  - SpO2 (oxygen saturation %)
  - pCO2 (carbon dioxide partial pressure)
  - Bronchial dilation (SNS dilates, PNS constricts)
  - Breath phase [0,1] for animation and RSA coupling to heart
  - Hyperventilation → hypocapnia → anxiety feedback loop
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class RespiratorySystem:

    def __init__(self):
        self.respiratory_rate  = 14.0   # breaths/min (12-20 normal)
        self.tidal_volume      = 500.0  # mL (350-500 normal)
        self.minute_ventilation = 7.0  # L/min
        self.SpO2              = 98.0   # %
        self.pCO2              = 40.0   # mmHg (35-45 normal)
        self.bronchial_dilation = 0.65  # [0,1]
        self.diaphragm_tension = 0.50
        self.breath_phase      = 0.0    # [0,1] 0=inhale start, 0.4=exhale start
        self.t_ms              = 0.0

        # Sighing: periodic deep breath (every ~5 min)
        self._sigh_timer = 0.0
        self._sigh_active = False

    def tick(self, dt_ms: float, ans_drives: Dict[str, float]):
        broncho_drive = ans_drives.get("bronchodilation", 0.0)
        rr_drive      = ans_drives.get("respiratory_rate_drive", 0.0)
        intensity     = ans_drives.get("intensity", 0.5)
        emotion_type  = ans_drives.get("emotion_type", "neutral")

        # Respiratory rate target
        rr_target = 14.0 + rr_drive * 10.0
        if emotion_type in ("fear", "panic", "terror"):
            rr_target += 6.0
        elif emotion_type in ("grief", "sadness"):
            rr_target += 2.0   # irregular sighing pattern
        elif emotion_type in ("calm", "contentment"):
            rr_target -= 2.0
        rr_target = max(6.0, min(35.0, rr_target))
        self.respiratory_rate = _lag(self.respiratory_rate, rr_target, 12.0)

        # Tidal volume: deeper with arousal, shallower with calm
        tv_target = 500.0 + rr_drive * 200.0
        if self._sigh_active:
            tv_target = 1200.0  # deep sigh
        tv_target = max(200.0, min(1500.0, tv_target))
        self.tidal_volume = _lag(self.tidal_volume, tv_target, 8.0)

        # Minute ventilation
        self.minute_ventilation = (self.respiratory_rate * self.tidal_volume) / 1000.0

        # Bronchial dilation (SNS dilates airways for fight/flight)
        bd_target = _clamp(0.65 + broncho_drive * 0.25)
        self.bronchial_dilation = _lag(self.bronchial_dilation, bd_target, 10.0)

        # Gas exchange — SpO2 and pCO2
        # Hyperventilation → low pCO2 (hypocapnia) → tingling, dizziness
        normal_ventilation = 14.0 * 0.5  # 7 L/min
        vent_ratio = self.minute_ventilation / max(0.1, normal_ventilation)
        pco2_target = 40.0 / max(0.5, vent_ratio)   # inversely proportional
        pco2_target = max(20.0, min(60.0, pco2_target))
        self.pCO2 = _lag(self.pCO2, pco2_target, 20.0)

        # SpO2: drops only with severely low ventilation or lung disease
        spo2_target = 98.0 - max(0.0, (20.0 - self.minute_ventilation) * 0.3)
        spo2_target = _clamp(spo2_target, 85.0, 100.0)
        self.SpO2 = _lag(self.SpO2, spo2_target, 30.0)

        # Breath phase: increments at respiratory rate
        breaths_per_ms = self.respiratory_rate / 60000.0
        self.breath_phase = (self.breath_phase + breaths_per_ms * dt_ms) % 1.0

        # Periodic sighing every ~3-5 min (important for alveolar recruitment)
        self._sigh_timer += dt_ms
        sigh_interval = 240000.0 - intensity * 60000.0  # more frequent under stress
        if self._sigh_timer > sigh_interval:
            self._sigh_active = True
            self._sigh_timer = 0.0
        elif self._sigh_active and self.breath_phase < 0.05:
            self._sigh_active = False

        self.t_ms += dt_ms

    def get_breath_phase_normalized(self) -> float:
        """Returns 0=full exhale, 1=full inhale (for lung animation)."""
        p = self.breath_phase
        if p < 0.40:   # inhale phase (40% of cycle)
            return p / 0.40
        else:           # exhale phase (60% of cycle)
            return 1.0 - (p - 0.40) / 0.60

    def get_params(self) -> Dict:
        return {
            "respiratory_rate": round(self.respiratory_rate, 1),
            "tidal_volume": round(self.tidal_volume, 0),
            "minute_ventilation": round(self.minute_ventilation, 2),
            "SpO2": round(self.SpO2, 1),
            "pCO2": round(self.pCO2, 1),
            "bronchial_dilation": round(self.bronchial_dilation, 3),
            "breath_phase": round(self.breath_phase, 3),
            "lung_fill": round(self.get_breath_phase_normalized(), 3),
            "sigh_active": self._sigh_active,
        }
