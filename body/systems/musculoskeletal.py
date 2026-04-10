"""
musculoskeletal.py — Muscles, Bones, Posture, Tension

Models:
  - Global muscle tension (fight/flight tightens everything)
  - Specific tension hotspots: jaw, trapezius, diaphragm, pelvic floor
  - Postural stability and collapse under grief/shutdown
  - Tremor amplitude (fear, adrenaline)
  - Motor readiness (premotor cortex activation)
  - Fatigue index (cortisol + sustained tension → depletion)
  - Limb blood flow (SNS redirects to muscles during threat)
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class MusculoskeletalSystem:

    def __init__(self):
        self.global_tension      = 0.30  # overall muscle tone [0,1]
        self.jaw_tension         = 0.20  # masseter/temporalis [0,1]
        self.trapezius_tension   = 0.30  # shoulders/neck [0,1]
        self.diaphragm_bracing   = 0.20  # breath-holding reflex [0,1]
        self.pelvic_floor_tension = 0.35
        self.core_bracing        = 0.25
        self.postural_stability  = 0.65  # upright vs collapsed [0,1]
        self.tremor_amplitude    = 0.00  # visible tremor [0,1]
        self.motor_readiness     = 0.40  # premotor activation [0,1]
        self.limb_blood_flow     = 0.50  # blood redirected to muscles
        self.fatigue_index       = 0.20  # accumulated fatigue [0,1]
        self.grip_strength       = 0.50
        self.reaction_time       = 0.50  # 0=slow, 1=fast (inverted: low=fast)

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives: sympathetic_tone, adrenaline, cortisol_blood, intensity,
                emotion_name, motor_cortex (M1 activity), PAG_activity
        """
        sns         = drives.get("sympathetic_tone", 0.35)
        adr         = drives.get("adrenaline", 0.15)
        cortisol    = drives.get("cortisol_blood", 0.30)
        intensity   = drives.get("intensity", 0.5)
        emotion     = drives.get("emotion_name", "calm").lower()
        m1          = drives.get("M1", 0.40)
        pag         = drives.get("PAG", 0.30)
        pfc         = drives.get("vmPFC", 0.45)
        endorphins  = drives.get("endorphins", 0.30)
        tau = max(1.0, dt_ms / 100.0)

        # Global tension: SNS + adrenaline + threat
        global_target = _clamp(0.30 + sns * 0.45 + adr * 0.20 - pfc * 0.15)
        if emotion in ("anger", "rage", "fury"):    global_target = _clamp(global_target + 0.35 * intensity)
        if emotion in ("fear", "panic", "terror"):  global_target = _clamp(global_target + 0.30 * intensity)
        if emotion in ("grief", "sadness"):         global_target = _clamp(global_target - 0.15 * intensity)
        if emotion in ("calm", "contentment"):      global_target = _clamp(global_target - 0.10 * intensity)
        self.global_tension = _lag(self.global_tension, global_target, 6 * tau)

        # Jaw: clenching under anger, fear, concentration
        jaw_target = _clamp(0.20 + sns * 0.40 + (0.40 if emotion in ("anger","frustration","rage") else 0) * intensity)
        self.jaw_tension = _lag(self.jaw_tension, jaw_target, 5 * tau)

        # Trapezius/shoulders: rises with stress, drops with relaxation
        trap_target = _clamp(0.30 + sns * 0.40 + cortisol * 0.15 - pfc * 0.20)
        self.trapezius_tension = _lag(self.trapezius_tension, trap_target, 8 * tau)

        # Diaphragm bracing: breath-holding response (fear, surprise, effort)
        diaphragm_target = _clamp(0.20 + (0.50 if emotion in ("fear","shock","surprise") else 0) * intensity + sns * 0.15)
        self.diaphragm_bracing = _lag(self.diaphragm_bracing, diaphragm_target, 3 * tau)

        # Pelvic floor: contracts under threat, fear
        pf_target = _clamp(0.35 + sns * 0.25 + (0.25 if emotion in ("fear","anxiety") else 0) * intensity)
        self.pelvic_floor_tension = _lag(self.pelvic_floor_tension, pf_target, 8 * tau)

        # Core: bracing for action
        core_target = _clamp(0.25 + m1 * 0.30 + pag * 0.20)
        self.core_bracing = _lag(self.core_bracing, core_target, 6 * tau)

        # Postural stability: collapses with grief/dorsal vagal, rises with joy/confidence
        posture_target = _clamp(0.65 + (0.20 if emotion in ("joy","pride","confidence") else 0)
                                     - (0.35 if emotion in ("grief","sadness","shame","depression") else 0) * intensity
                                     - cortisol * 0.10)
        self.postural_stability = _lag(self.postural_stability, posture_target, 20 * tau)

        # Tremor: fear + adrenaline surge → visible shaking
        tremor_target = _clamp(0.0 + adr * 0.35 + (0.30 if emotion in ("fear","terror","rage") else 0) * intensity)
        self.tremor_amplitude = _lag(self.tremor_amplitude, tremor_target, 4 * tau)

        # Motor readiness: premotor + SNS
        motor_target = _clamp(0.40 + m1 * 0.30 + sns * 0.25)
        self.motor_readiness = _lag(self.motor_readiness, motor_target, 5 * tau)

        # Limb blood flow: SNS redirects to muscles (vasoconstriction in gut, dilation in muscles)
        limb_flow_target = _clamp(0.50 + sns * 0.30 + adr * 0.20)
        self.limb_blood_flow = _lag(self.limb_blood_flow, limb_flow_target, 10 * tau)

        # Grip strength: SNS + motor readiness
        grip_target = _clamp(0.50 + sns * 0.25 + motor_target * 0.15)
        self.grip_strength = _lag(self.grip_strength, grip_target, 8 * tau)

        # Reaction time (1=fast, 0=slow) — SNS speeds it up, fatigue slows
        react_target = _clamp(0.50 + sns * 0.30 - self.fatigue_index * 0.25)
        self.reaction_time = _lag(self.reaction_time, react_target, 6 * tau)

        # Fatigue: accumulates with sustained tension and cortisol
        fatigue_target = _clamp(self.global_tension * 0.15 + cortisol * 0.10 - endorphins * 0.05)
        self.fatigue_index = _lag(self.fatigue_index, fatigue_target, 500 * tau)

    def get_params(self) -> Dict:
        return {
            "global_tension": round(self.global_tension, 3),
            "jaw_tension": round(self.jaw_tension, 3),
            "trapezius_tension": round(self.trapezius_tension, 3),
            "diaphragm_bracing": round(self.diaphragm_bracing, 3),
            "pelvic_floor_tension": round(self.pelvic_floor_tension, 3),
            "core_bracing": round(self.core_bracing, 3),
            "postural_stability": round(self.postural_stability, 3),
            "tremor_amplitude": round(self.tremor_amplitude, 3),
            "motor_readiness": round(self.motor_readiness, 3),
            "limb_blood_flow": round(self.limb_blood_flow, 3),
            "grip_strength": round(self.grip_strength, 3),
            "reaction_time": round(self.reaction_time, 3),
            "fatigue_index": round(self.fatigue_index, 3),
        }
