"""
integumentary.py — Skin, Hair, Temperature

The body's largest organ and primary emotional readout surface.

Models:
  - Galvanic skin response / skin conductance (GSR/EDA) — microseconds
  - Skin surface temperature (thermal imaging equivalent)
  - Flushing / blushing (vasodilation) — embarrassment, joy
  - Pallor (vasoconstriction) — fear, shock
  - Piloerection (goosebumps) — awe, cold, fear
  - Sweating: eccrine (thermoregulatory + emotional) + apocrine (stress)
  - Facial flushing vs body flushing
  - Pain receptors (nociception index)
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class IntegumentarySystem:

    def __init__(self):
        self.skin_conductance   = 5.0   # microsiemens (µS), baseline 2-10 µS
        self.skin_temp_c        = 33.5  # surface temperature °C
        self.core_temp_c        = 37.0  # core body temperature
        self.flushing           = 0.0   # vasodilation → redness [0,1]
        self.pallor             = 0.0   # vasoconstriction → paleness [0,1]
        self.blushing           = 0.0   # facial-specific flushing
        self.piloerection       = 0.0   # goosebumps [0,1]
        self.sweating_eccrine   = 0.05  # thermoregulatory sweat
        self.sweating_apocrine  = 0.02  # emotional/stress sweat (armpits)
        self.sweating_palmar    = 0.03  # palmar sweating (hands, feet)
        self.pain_level         = 0.0   # nociception [0,1]
        self.itch               = 0.0   # pruritus [0,1]
        self.wound_healing_rate = 0.50  # (suppressed by chronic cortisol)
        self.sebum_production   = 0.35  # oil gland activity

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives: sweating_drive, piloerection_drive, skin_vasoconstriction,
                cortisol_blood, adrenaline, oxytocin_peripheral,
                emotion_name, intensity, metabolic_rate
        """
        sweat_drive  = drives.get("sweating_drive", 0.0)
        pilo_drive   = drives.get("piloerection_drive", 0.0)
        vaso_drive   = drives.get("skin_vasoconstriction", 0.0)
        cortisol     = drives.get("cortisol_blood", 0.30)
        adr          = drives.get("adrenaline", 0.15)
        oxytocin     = drives.get("oxytocin_peripheral", 0.25)
        emotion      = drives.get("emotion_name", "calm").lower()
        intensity    = drives.get("intensity", 0.5)
        metabolic    = drives.get("metabolic_rate", 0.50)
        tau = max(1.0, dt_ms / 100.0)

        # ── Skin conductance (EDA) — fastest emotional signal ───────────────
        # Rises with any SNS activation, emotional arousal
        gsr_target = _clamp(
            5.0 + sweat_drive * 18.0 + adr * 8.0
            - oxytocin * 3.0
        ) / 30.0  # normalize to [0,1] internally
        # Store as actual µS
        gsr_raw = _clamp(gsr_target * 30.0 + 1.0, 0.5, 35.0)
        # Fast rise (sympathetic), slow recovery
        tau_gsr = 3 * tau if sweat_drive > 0 else 12 * tau
        self.skin_conductance = self.skin_conductance + (gsr_raw - self.skin_conductance) * (1 - math.exp(-1/tau_gsr))

        # ── Sweating ─────────────────────────────────────────────────────────
        eccrine_target = _clamp(0.05 + sweat_drive * 0.40 + (metabolic - 0.5) * 0.20)
        self.sweating_eccrine = _lag(self.sweating_eccrine, eccrine_target, 5 * tau)

        apocrine_target = _clamp(0.02 + adr * 0.35 + cortisol * 0.20)
        self.sweating_apocrine = _lag(self.sweating_apocrine, apocrine_target, 4 * tau)

        palmar_target = _clamp(0.03 + sweat_drive * 0.35 + adr * 0.30)
        self.sweating_palmar = _lag(self.sweating_palmar, palmar_target, 3 * tau)

        # ── Piloerection (goosebumps) ─────────────────────────────────────
        # Awe, cold, fear, musical chills all trigger this
        pilo_target = _clamp(pilo_drive * 0.85)
        if emotion in ("awe", "wonder"):
            pilo_target = _clamp(pilo_target + 0.50 * intensity)
        elif emotion in ("fear", "terror"):
            pilo_target = _clamp(pilo_target + 0.35 * intensity)
        self.piloerection = _lag(self.piloerection, pilo_target, 3 * tau)

        # ── Flushing vs Pallor ────────────────────────────────────────────
        # Flushing: PNS vasodilation, joy, embarrassment, love
        flush_target = 0.0
        if emotion in ("embarrassment", "shame", "pride", "joy", "love", "ecstasy"):
            flush_target = 0.40 * intensity
        flush_target = _clamp(flush_target - vaso_drive * 0.30 + oxytocin * 0.20)
        self.flushing = _lag(self.flushing, flush_target, 5 * tau)

        # Blushing: facial-specific, social emotions
        blush_target = 0.0
        if emotion in ("embarrassment", "shame", "humiliation"):
            blush_target = 0.70 * intensity
        elif emotion in ("pride",):
            blush_target = 0.30 * intensity
        blush_target = _clamp(blush_target)
        self.blushing = _lag(self.blushing, blush_target, 4 * tau)

        # Pallor: vasoconstriction → blood drains from skin
        pallor_target = _clamp(vaso_drive * 0.65 + adr * 0.20)
        if emotion in ("shock", "terror", "grief"):
            pallor_target = _clamp(pallor_target + 0.35 * intensity)
        self.pallor = _lag(self.pallor, pallor_target, 4 * tau)

        # Pallor and flushing are somewhat antagonistic
        if self.pallor > 0.3:
            self.flushing = max(0, self.flushing - self.pallor * 0.5)

        # ── Temperature regulation ─────────────────────────────────────────
        # Skin temp: rises with flushing, drops with pallor
        temp_target = 33.5 + self.flushing * 2.5 - self.pallor * 3.0 + (metabolic - 0.5) * 1.5
        temp_target = max(28.0, min(38.0, temp_target))
        self.skin_temp_c = _lag(self.skin_temp_c, temp_target, 30 * tau)

        # Core temperature: mostly stable, rises with extreme exertion/fever
        core_target = 37.0 + cortisol * 0.15 + metabolic * 0.20
        core_target = max(35.5, min(40.0, core_target))
        self.core_temp_c = _lag(self.core_temp_c, core_target, 1000 * tau)

        # ── Wound healing / sebum ─────────────────────────────────────────
        heal_target = _clamp(0.50 - cortisol * 0.30)  # cortisol suppresses healing
        self.wound_healing_rate = _lag(self.wound_healing_rate, heal_target, 5000 * tau)

        sebum_target = _clamp(0.35 + cortisol * 0.15)  # stress → acne
        self.sebum_production = _lag(self.sebum_production, sebum_target, 3000 * tau)

    def get_params(self) -> Dict:
        return {
            "skin_conductance_us": round(self.skin_conductance, 2),
            "skin_temp_c": round(self.skin_temp_c, 2),
            "core_temp_c": round(self.core_temp_c, 2),
            "flushing": round(self.flushing, 3),
            "pallor": round(self.pallor, 3),
            "blushing": round(self.blushing, 3),
            "piloerection": round(self.piloerection, 3),
            "sweating_eccrine": round(self.sweating_eccrine, 3),
            "sweating_apocrine": round(self.sweating_apocrine, 3),
            "sweating_palmar": round(self.sweating_palmar, 3),
            "pain_level": round(self.pain_level, 3),
            "wound_healing_rate": round(self.wound_healing_rate, 3),
            "sebum_production": round(self.sebum_production, 3),
        }
