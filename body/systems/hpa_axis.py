"""
hpa_axis.py — Hypothalamic-Pituitary-Adrenal Axis + Adrenal Medulla

The body's slow stress cascade. Three sequential stages with negative feedback:

  Hypothalamus → CRH
       ↓  (minutes)
  Pituitary → ACTH
       ↓  (minutes to hours)
  Adrenal Cortex → Cortisol (peripheral blood)
       ↓  (negative feedback loop — high cortisol suppresses step 1+2)

Separate fast pathway (adrenal medulla, SNS-driven, seconds):
  SNS activation → Adrenal Medulla → Adrenaline + Noradrenaline

The HPA cortisol is DISTINCT from the brain's NT cortisol.
Brain cortisol = central effect on behavior.
HPA cortisol = peripheral blood level affecting immune, metabolism, etc.

Also models:
  - Adrenaline surge and blood glucose mobilization
  - Aldosterone (sodium retention, BP regulation)
  - DHEA (anti-aging, protective against cortisol)
  - Cortisol's negative feedback timing
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class HPAAxis:

    def __init__(self):
        # Hormones — all [0,1] normalized
        self.CRH          = 0.25    # hypothalamic corticotropin-releasing hormone
        self.ACTH         = 0.30    # pituitary adrenocorticotropic hormone
        self.cortisol_blood = 0.30  # peripheral blood cortisol (slow)
        self.aldosterone  = 0.30    # adrenal mineralocorticoid
        self.DHEA         = 0.35    # dehydroepiandrosterone (protective)

        # Adrenal medulla (fast — SNS-driven, seconds)
        self.adrenaline         = 0.15  # epinephrine
        self.noradrenaline_peri = 0.22  # peripheral norepinephrine
        self.blood_glucose      = 0.50  # normalized blood glucose
        self.insulin            = 0.45  # pancreatic insulin (reactive)

        # Negative feedback gate
        self._feedback_active = False

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives: amygdala, hypothalamus, intensity, sympathetic_tone
        """
        am  = drives.get("amygdala", 0.30)
        hyp = drives.get("hypothalamus", 0.50)
        sns = drives.get("sympathetic_tone", 0.35)
        intensity = drives.get("intensity", 0.5)

        tau = max(1.0, dt_ms / 100.0)

        # ── Adrenal Medulla (fast, seconds) ──────────────────────────────────
        # Pure SNS drive — this is the fight/flight adrenaline surge
        adr_target = _clamp(sns * 0.85 + am * 0.15 - 0.05)
        self.adrenaline = _lag(self.adrenaline, adr_target, 4 * tau)  # ~400ms

        nor_target = _clamp(sns * 0.70 + am * 0.10)
        self.noradrenaline_peri = _lag(self.noradrenaline_peri, nor_target, 5 * tau)

        # Blood glucose mobilization (adrenaline breaks down glycogen)
        glucose_target = _clamp(0.50 + self.adrenaline * 0.35 - self.insulin * 0.20)
        self.blood_glucose = _lag(self.blood_glucose, glucose_target, 8 * tau)

        # Insulin rebound (pancreas responds to elevated glucose)
        insulin_target = _clamp(0.45 + (self.blood_glucose - 0.50) * 0.60)
        self.insulin = _lag(self.insulin, insulin_target, 20 * tau)

        # ── HPA Cascade (slow, minutes-to-hours) ─────────────────────────────
        # Negative feedback: high cortisol suppresses CRH and ACTH
        nf_strength = self.cortisol_blood * 0.55
        self._feedback_active = self.cortisol_blood > 0.55

        # Stage 1: Hypothalamus CRH
        crh_target = _clamp(
            0.25
            + (am * 0.40 + hyp * 0.30 + intensity * 0.20) * (1.0 - nf_strength)
        )
        self.CRH = _lag(self.CRH, crh_target, 50 * tau)  # ~5s

        # Stage 2: Pituitary ACTH
        acth_target = _clamp(self.CRH * 0.90 * (1.0 - nf_strength * 0.40))
        self.ACTH = _lag(self.ACTH, acth_target, 150 * tau)  # ~15s

        # Stage 3: Adrenal Cortex Cortisol (very slow)
        cort_target = _clamp(self.ACTH * 0.85)
        self.cortisol_blood = _lag(self.cortisol_blood, cort_target, 600 * tau)  # ~60s

        # Aldosterone: driven by ACTH + angiotensin (simplified)
        aldo_target = _clamp(0.30 + self.ACTH * 0.25 + sns * 0.10)
        self.aldosterone = _lag(self.aldosterone, aldo_target, 400 * tau)

        # DHEA: inversely related to chronic cortisol (pregnenolone steal)
        dhea_target = _clamp(0.35 - self.cortisol_blood * 0.25)
        self.DHEA = _lag(self.DHEA, dhea_target, 500 * tau)

    def get_params(self) -> Dict:
        return {
            "CRH": round(self.CRH, 3),
            "ACTH": round(self.ACTH, 3),
            "cortisol_blood": round(self.cortisol_blood, 3),
            "adrenaline": round(self.adrenaline, 3),
            "noradrenaline_peripheral": round(self.noradrenaline_peri, 3),
            "aldosterone": round(self.aldosterone, 3),
            "DHEA": round(self.DHEA, 3),
            "blood_glucose": round(self.blood_glucose, 3),
            "insulin": round(self.insulin, 3),
            "negative_feedback_active": self._feedback_active,
        }
