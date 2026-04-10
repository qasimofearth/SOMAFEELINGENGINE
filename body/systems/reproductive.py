"""
reproductive.py — Reproductive System

The most emotion-coupled system in the body. Deeply integrated with
the limbic system, oxytocin, dopamine, and stress hormones.

Models:
  - Sexual arousal state (genital engorgement, lubrication)
  - Libido (desire drive — suppressed by cortisol, enhanced by testosterone/estrogen)
  - Oxytocin bonding response
  - Menstrual/hormonal cycle phase effects (simplified)
  - Fertility index (chronic stress suppresses)
  - Orgasm/climax response (peak release: oxytocin, dopamine, endorphins)
  - Postcoital bonding state
  - Reproductive anxiety (performance, fertility concerns)
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class ReproductiveSystem:

    def __init__(self):
        self.libido                = 0.35  # baseline desire [0,1]
        self.genital_arousal       = 0.05  # physical arousal [0,1]
        self.lubrication           = 0.05  # [0,1] (applies to all anatomy)
        self.oxytocin_bonding      = 0.25  # post-contact bonding drive
        self.dopamine_desire       = 0.30  # wanting/anticipation component
        self.endorphin_pleasure    = 0.15  # hedonic pleasure component
        self.fertility_index       = 0.55  # reproductive fitness [0,1]
        self.reproductive_anxiety  = 0.10  # performance/fertility worry
        self.climax_state          = 0.00  # [0,1] approaching climax
        self.refractory_index      = 0.00  # post-climax cooldown [0,1]
        self.testosterone_drive    = 0.40  # sex hormone contribution
        self.estrogen_drive        = 0.35
        self.pheromone_sensitivity = 0.40  # social chemosensory

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        cortisol    = drives.get("cortisol_blood", 0.30)
        adr         = drives.get("adrenaline", 0.15)
        oxytocin    = drives.get("oxytocin_brain", 0.35)
        dopamine    = drives.get("dopamine", 0.50)
        endorphins  = drives.get("endorphins", 0.30)
        testosterone = drives.get("testosterone", 0.40)
        estrogen    = drives.get("estrogen", 0.35)
        sns         = drives.get("sympathetic_tone", 0.35)
        pns         = drives.get("parasympathetic_tone", 0.65)
        emotion     = drives.get("emotion_name", "calm").lower()
        intensity   = drives.get("intensity", 0.5)
        tau = max(1.0, dt_ms / 100.0)

        # Testosterone and estrogen drives from hormonal system
        test_drive = _clamp(testosterone * 0.85)
        estr_drive = _clamp(estrogen * 0.85)
        self.testosterone_drive = _lag(self.testosterone_drive, test_drive, 500 * tau)
        self.estrogen_drive = _lag(self.estrogen_drive, estr_drive, 500 * tau)

        # Libido: testosterone + estrogen + dopamine − cortisol (stress kills desire)
        libido_target = _clamp(
            0.20
            + self.testosterone_drive * 0.25
            + self.estrogen_drive * 0.20
            + (dopamine - 0.50) * 0.20
            - cortisol * 0.40
            - self.refractory_index * 0.30
        )
        if emotion in ("love", "lust", "desire", "intimacy"):
            libido_target = _clamp(libido_target + 0.30 * intensity)
        if emotion in ("disgust", "grief", "shame", "anxiety"):
            libido_target = _clamp(libido_target - 0.25 * intensity)
        self.libido = _lag(self.libido, libido_target, 100 * tau)

        # Physical arousal: PNS mediates engorgement (rest = arousal, fight ≠ arousal)
        # High SNS kills physical arousal even if desire is present
        arousal_target = _clamp(
            self.libido * 0.60
            + pns * 0.25
            + oxytocin * 0.20
            - adr * 0.40
            - cortisol * 0.25
            - self.refractory_index * 0.50
        )
        if emotion in ("love", "lust", "desire", "ecstasy"):
            arousal_target = _clamp(arousal_target + 0.35 * intensity)
        self.genital_arousal = _lag(self.genital_arousal, arousal_target, 15 * tau)
        self.lubrication = _lag(self.lubrication, self.genital_arousal * 0.90, 20 * tau)

        # Dopamine desire (wanting component — separate from liking/pleasure)
        da_desire_target = _clamp(0.30 + (dopamine - 0.50) * 0.40 + self.libido * 0.30)
        self.dopamine_desire = _lag(self.dopamine_desire, da_desire_target, 10 * tau)

        # Endorphin pleasure
        ep_target = _clamp(0.15 + endorphins * 0.50 + self.genital_arousal * 0.20)
        self.endorphin_pleasure = _lag(self.endorphin_pleasure, ep_target, 8 * tau)

        # Oxytocin bonding: physical contact + orgasm release + social safety
        bond_target = _clamp(oxytocin * 0.70 + self.genital_arousal * 0.20)
        self.oxytocin_bonding = _lag(self.oxytocin_bonding, bond_target, 20 * tau)

        # Fertility index: suppressed by chronic cortisol (pregnenolone steal)
        fert_target = _clamp(0.55 - cortisol * 0.40 + self.testosterone_drive * 0.10)
        self.fertility_index = _lag(self.fertility_index, fert_target, 2000 * tau)

        # Reproductive anxiety: performance + fertility concerns
        anxiety_target = _clamp(cortisol * 0.20 + (1 - self.fertility_index) * 0.15)
        if emotion in ("anxiety", "shame", "embarrassment"):
            anxiety_target = _clamp(anxiety_target + 0.25 * intensity)
        self.reproductive_anxiety = _lag(self.reproductive_anxiety, anxiety_target, 30 * tau)

        # Climax: builds with sustained high arousal + dopamine surge + low anxiety
        if self.refractory_index < 0.10:
            climax_delta = self.genital_arousal * 0.02 + self.dopamine_desire * 0.01 - self.reproductive_anxiety * 0.02
            self.climax_state = _clamp(self.climax_state + climax_delta * (dt_ms / 100.0))
        else:
            self.climax_state = _lag(self.climax_state, 0.0, 10 * tau)

        # Climax trigger: massive oxytocin, dopamine, endorphin release
        if self.climax_state > 0.90 and self.refractory_index < 0.05:
            self.climax_state = 1.0
            self.refractory_index = 1.0  # refractory period kicks in

        # Refractory: fades over time
        if self.refractory_index > 0:
            self.refractory_index = _lag(self.refractory_index, 0.0, 300 * tau)
            if self.refractory_index > 0.90:  # just climaxed
                self.climax_state = _lag(self.climax_state, 0.0, 20 * tau)

        # Pheromone sensitivity: rises with arousal and oxytocin
        phero_target = _clamp(0.40 + self.libido * 0.20 + oxytocin * 0.15)
        self.pheromone_sensitivity = _lag(self.pheromone_sensitivity, phero_target, 50 * tau)

    def get_params(self) -> Dict:
        return {
            "libido": round(self.libido, 3),
            "genital_arousal": round(self.genital_arousal, 3),
            "lubrication": round(self.lubrication, 3),
            "oxytocin_bonding": round(self.oxytocin_bonding, 3),
            "dopamine_desire": round(self.dopamine_desire, 3),
            "endorphin_pleasure": round(self.endorphin_pleasure, 3),
            "fertility_index": round(self.fertility_index, 3),
            "reproductive_anxiety": round(self.reproductive_anxiety, 3),
            "climax_state": round(self.climax_state, 3),
            "refractory_index": round(self.refractory_index, 3),
            "testosterone_drive": round(self.testosterone_drive, 3),
            "estrogen_drive": round(self.estrogen_drive, 3),
            "pheromone_sensitivity": round(self.pheromone_sensitivity, 3),
        }
