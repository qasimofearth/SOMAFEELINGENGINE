"""
immune.py — Immune / Lymphatic System

The immune system is deeply emotion-coupled. Chronic stress suppresses it;
acute stress briefly boosts it; positive social connection enhances it.

Models:
  - NK cell activity (natural killer cells — first responders)
  - T-cell and B-cell activity (adaptive immunity)
  - Cytokines: IL-6 (pro-inflammatory), IL-10 (anti-inflammatory), TNF-α
  - Inflammatory index (chronic = bad, acute = normal)
  - Cortisol immune suppression
  - Sickness behavior (fatigue, withdrawal, low mood — immune→brain feedback)
  - Lymphatic drainage
  - Wound healing coupling
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class ImmuneSystem:

    def __init__(self):
        self.nk_cell_activity    = 0.50
        self.t_cell_activity     = 0.45
        self.b_cell_activity     = 0.40
        self.macrophage_activity = 0.40
        self.il6                 = 0.20  # pro-inflammatory (low baseline)
        self.il10                = 0.35  # anti-inflammatory
        self.tnf_alpha           = 0.15  # tumor necrosis factor
        self.inflammatory_index  = 0.20  # overall inflammation [0,1]
        self.immune_suppression  = 0.20  # cortisol-mediated suppression
        self.sickness_behavior   = 0.00  # fatigue/withdrawal signal to brain
        self.lymphatic_flow      = 0.50
        self.histamine           = 0.15  # allergy/mast cell mediator
        self.interferon          = 0.25  # antiviral response

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        cortisol    = drives.get("cortisol_blood", 0.30)
        adr         = drives.get("adrenaline", 0.15)
        oxytocin    = drives.get("oxytocin_brain", 0.35)
        sns         = drives.get("sympathetic_tone", 0.35)
        emotion     = drives.get("emotion_name", "calm").lower()
        intensity   = drives.get("intensity", 0.5)
        tau = max(1.0, dt_ms / 100.0)

        # Immune suppression: cortisol is the primary immunosuppressant
        supp_target = _clamp(cortisol * 0.70 + adr * 0.10)
        self.immune_suppression = _lag(self.immune_suppression, supp_target, 50 * tau)

        # NK cells: acute SNS burst briefly increases them; chronic stress depletes
        nk_target = _clamp(0.50 + adr * 0.15 - self.immune_suppression * 0.50
                           + oxytocin * 0.10)
        self.nk_cell_activity = _lag(self.nk_cell_activity, nk_target, 80 * tau)

        # T-cells: suppressed by cortisol, enhanced by sleep/calm
        t_target = _clamp(0.45 - self.immune_suppression * 0.40
                         + (0.10 if emotion in ("calm","contentment","love") else 0))
        self.t_cell_activity = _lag(self.t_cell_activity, t_target, 100 * tau)

        # B-cells: antibody producers — slower, chronic suppression
        b_target = _clamp(0.40 - self.immune_suppression * 0.30)
        self.b_cell_activity = _lag(self.b_cell_activity, b_target, 200 * tau)

        # Macrophages: activated by stress (danger sensing), suppressed chronically
        mac_target = _clamp(0.40 + sns * 0.15 - cortisol * 0.20)
        self.macrophage_activity = _lag(self.macrophage_activity, mac_target, 60 * tau)

        # IL-6 (pro-inflammatory): rises with chronic stress, loneliness, poor sleep
        il6_target = _clamp(0.20 + cortisol * 0.30 + self.inflammatory_index * 0.20
                           + (0.15 if emotion in ("grief","loneliness","depression") else 0))
        self.il6 = _lag(self.il6, il6_target, 200 * tau)

        # IL-10 (anti-inflammatory): rises with social bonding, positive emotion
        il10_target = _clamp(0.35 + oxytocin * 0.20
                            + (0.10 if emotion in ("love","joy","calm","contentment") else 0)
                            - cortisol * 0.15)
        self.il10 = _lag(self.il10, il10_target, 150 * tau)

        # TNF-alpha: acute inflammatory signal
        tnf_target = _clamp(0.15 + self.il6 * 0.30 - self.il10 * 0.20)
        self.tnf_alpha = _lag(self.tnf_alpha, tnf_target, 100 * tau)

        # Overall inflammatory index
        inflam_target = _clamp(self.il6 * 0.45 + self.tnf_alpha * 0.30 - self.il10 * 0.25)
        self.inflammatory_index = _lag(self.inflammatory_index, inflam_target, 150 * tau)

        # Sickness behavior: high inflammation → brain gets told to withdraw/rest
        sick_target = _clamp(self.inflammatory_index * 0.70 - oxytocin * 0.15)
        self.sickness_behavior = _lag(self.sickness_behavior, sick_target, 300 * tau)

        # Lymphatic flow: movement and breathing drive it (PNS state helps)
        lymph_target = _clamp(0.50 + (1 - sns) * 0.20 - self.inflammatory_index * 0.10)
        self.lymphatic_flow = _lag(self.lymphatic_flow, lymph_target, 50 * tau)

        # Histamine: allergy/stress mast cell response
        hist_target = _clamp(0.15 + adr * 0.10 + self.inflammatory_index * 0.15)
        self.histamine = _lag(self.histamine, hist_target, 20 * tau)

        # Interferon: antiviral; mildly elevated with general immune activation
        ifn_target = _clamp(0.25 + self.nk_cell_activity * 0.15)
        self.interferon = _lag(self.interferon, ifn_target, 200 * tau)

    def get_params(self) -> Dict:
        return {
            "nk_cell_activity": round(self.nk_cell_activity, 3),
            "t_cell_activity": round(self.t_cell_activity, 3),
            "b_cell_activity": round(self.b_cell_activity, 3),
            "macrophage_activity": round(self.macrophage_activity, 3),
            "il6": round(self.il6, 3),
            "il10": round(self.il10, 3),
            "tnf_alpha": round(self.tnf_alpha, 3),
            "inflammatory_index": round(self.inflammatory_index, 3),
            "immune_suppression": round(self.immune_suppression, 3),
            "sickness_behavior": round(self.sickness_behavior, 3),
            "lymphatic_flow": round(self.lymphatic_flow, 3),
            "histamine": round(self.histamine, 3),
            "interferon": round(self.interferon, 3),
        }
