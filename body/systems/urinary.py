"""
urinary.py — Urinary System

Kidneys, ureters, bladder, urethra.

Models:
  - Glomerular filtration rate (GFR) — kidney filtering efficiency
  - Urine output and concentration
  - Bladder detrusor muscle tone
  - Urinary urgency (fear famously causes bladder urgency)
  - Renin-angiotensin system (blood pressure regulation)
  - ADH/vasopressin effect (water retention under stress)
  - Aldosterone effect (sodium/potassium balance)
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class UrinarySystem:

    def __init__(self):
        self.GFR                 = 0.60   # glomerular filtration rate (norm ~120 mL/min)
        self.urine_output        = 0.50   # relative output [0,1]
        self.urine_concentration = 0.50   # osmolality proxy
        self.bladder_fullness    = 0.25   # [0,1]
        self.detrusor_tone       = 0.40   # bladder wall muscle
        self.urethral_sphincter  = 0.70   # closed = high value
        self.urinary_urgency     = 0.05
        self.renin               = 0.35   # angiotensin system
        self.angiotensin_II      = 0.30
        self.water_retention     = 0.40   # ADH effect

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        sns         = drives.get("sympathetic_tone", 0.35)
        cortisol    = drives.get("cortisol_blood", 0.30)
        adr         = drives.get("adrenaline", 0.15)
        vasopressin = drives.get("vasopressin", 0.35)
        aldosterone = drives.get("aldosterone", 0.30)
        bp          = drives.get("mean_arterial_pressure", 93.3)
        emotion     = drives.get("emotion_name", "calm").lower()
        intensity   = drives.get("intensity", 0.5)
        tau = max(1.0, dt_ms / 100.0)

        # GFR: drops with SNS (blood redirected away from kidneys during stress)
        gfr_target = _clamp(0.60 - sns * 0.20 - adr * 0.10 + (bp - 93.0) / 100.0)
        self.GFR = _lag(self.GFR, gfr_target, 30 * tau)

        # ADH/vasopressin: water retention (urine volume drops, concentration rises)
        retain_target = _clamp(0.40 + vasopressin * 0.40)
        self.water_retention = _lag(self.water_retention, retain_target, 20 * tau)

        # Urine output: inversely related to water retention and GFR drop
        output_target = _clamp(0.50 * self.GFR - self.water_retention * 0.30)
        self.urine_output = _lag(self.urine_output, output_target, 100 * tau)

        # Urine concentration: inverse of output
        conc_target = _clamp(0.50 + self.water_retention * 0.30 - self.urine_output * 0.20)
        self.urine_concentration = _lag(self.urine_concentration, conc_target, 80 * tau)

        # Renin-angiotensin: activated by low BP, SNS, stress
        renin_target = _clamp(0.35 + sns * 0.20 + max(0, (93.0 - bp) / 50.0))
        self.renin = _lag(self.renin, renin_target, 40 * tau)
        ang_target = _clamp(self.renin * 0.85)
        self.angiotensin_II = _lag(self.angiotensin_II, ang_target, 30 * tau)

        # Bladder: SNS relaxes detrusor (holds urine), PNS contracts (voiding)
        # Bladder slowly fills over time
        self.bladder_fullness = _clamp(self.bladder_fullness + self.urine_output * 0.0001 * (dt_ms / 100.0))

        detrusor_target = _clamp(0.40 - sns * 0.25 + (1 - sns) * 0.15)
        self.detrusor_tone = _lag(self.detrusor_tone, detrusor_target, 15 * tau)

        sphincter_target = _clamp(0.70 + sns * 0.20 - (1 - sns) * 0.15)
        self.urethral_sphincter = _lag(self.urethral_sphincter, sphincter_target, 10 * tau)

        # Urgency: fear/panic triggers involuntary urge
        urgency_target = _clamp(
            self.bladder_fullness * 0.40
            + (0.50 if emotion in ("fear", "panic", "terror") else 0.0) * intensity
            + adr * 0.15
            + self.detrusor_tone * 0.20
        )
        self.urinary_urgency = _lag(self.urinary_urgency, urgency_target, 5 * tau)

        # Void if urgency extremely high (clamp and reset bladder)
        if self.urinary_urgency > 0.90 and self.bladder_fullness > 0.70:
            self.bladder_fullness = max(0, self.bladder_fullness - 0.40)

    def get_params(self) -> Dict:
        return {
            "GFR": round(self.GFR, 3),
            "urine_output": round(self.urine_output, 3),
            "urine_concentration": round(self.urine_concentration, 3),
            "bladder_fullness": round(self.bladder_fullness, 3),
            "detrusor_tone": round(self.detrusor_tone, 3),
            "urethral_sphincter": round(self.urethral_sphincter, 3),
            "urinary_urgency": round(self.urinary_urgency, 3),
            "renin": round(self.renin, 3),
            "angiotensin_II": round(self.angiotensin_II, 3),
            "water_retention": round(self.water_retention, 3),
        }
