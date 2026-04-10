"""
ans.py — Autonomic Nervous System

The ANS is the master controller that translates brain state into
organ drives. It has two branches:

  Sympathetic (SNS): fight/flight/freeze — fast, diffuse, adrenaline-mediated
  Parasympathetic (PNS): rest/digest/connect — slow, specific, vagus-mediated

The balance between them (sns_pns_ratio) governs nearly every organ.

Also models the enteric nervous system coupling (ENS — the "second brain")
and the polyvagal hierarchy (ventral vagal → sympathetic → dorsal vagal).

Inputs from brain:
  - hypothalamus activity (primary ANS driver)
  - brainstem activity (NTS, dorsal motor vagal nucleus, locus coeruleus)
  - amygdala activity (threat → SNS surge)
  - vmPFC activity (regulation → vagal tone)
  - norepinephrine, acetylcholine, cortisol NT levels
"""

import math
from typing import Dict


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _lag(current: float, target: float, tau_frames: float) -> float:
    """Exponential lag toward target."""
    alpha = 1.0 - math.exp(-1.0 / tau_frames)
    return current + alpha * (target - current)


class ANSSystem:
    """Autonomic Nervous System — SNS/PNS balance."""

    # Time constants in update-frames (each frame = 100ms real time in tick)
    TAU_SNS = 5.0    # ~500ms to shift sympathetic tone
    TAU_PNS = 8.0    # ~800ms to shift parasympathetic tone

    def __init__(self):
        self.sympathetic_tone = 0.35     # baseline resting SNS [0,1]
        self.parasympathetic_tone = 0.65  # baseline resting PNS [0,1] (vagal dominance at rest)
        self.sns_pns_ratio = 0.54        # derived: SNS / (SNS + PNS)
        # Polyvagal state: 0=dorsal vagal shutdown, 0.5=sympathetic, 1=ventral vagal safe
        self.polyvagal_state = 0.75
        self.hrv = 0.55                  # heart rate variability (index of vagal tone)
        self.vagal_tone = 0.65           # direct vagus nerve firing rate

        # Organ-level drives this system outputs (consumed by other systems)
        self.organ_drives: Dict[str, float] = {}

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives keys: hypothalamus, brainstem, amygdala, vmPFC,
                     norepinephrine, acetylcholine, cortisol (from brain state)
        """
        h  = drives.get("hypothalamus", 0.50)
        bs = drives.get("brainstem", 0.50)
        am = drives.get("amygdala", 0.30)
        pfc = drives.get("vmPFC", 0.45)
        ne = drives.get("norepinephrine", 0.45)
        ach = drives.get("acetylcholine", 0.45)
        cort = drives.get("cortisol", 0.30)
        intensity = drives.get("intensity", 0.5)

        # SNS target: threat + arousal drives it up; PFC regulation damps it
        sns_target = _clamp(
            0.20
            + h * 0.30
            + am * 0.35
            + ne * 0.20
            + cort * 0.15
            - pfc * 0.25
        )

        # PNS target: brainstem vagal nuclei + PFC + acetylcholine
        pns_target = _clamp(
            0.30
            + bs * 0.30
            + pfc * 0.25
            + ach * 0.20
            - am * 0.20
            - cort * 0.10
        )

        tau_frames = max(1.0, dt_ms / 100.0)
        self.sympathetic_tone = _lag(self.sympathetic_tone, sns_target, self.TAU_SNS * tau_frames)
        self.parasympathetic_tone = _lag(self.parasympathetic_tone, pns_target, self.TAU_PNS * tau_frames)

        total = self.sympathetic_tone + self.parasympathetic_tone + 1e-6
        self.sns_pns_ratio = self.sympathetic_tone / total

        # Vagal tone inversely related to SNS dominance
        self.vagal_tone = _clamp(1.0 - self.sns_pns_ratio * 1.2 + 0.1)

        # HRV proxy: high vagal tone → high HRV
        self.hrv = _clamp(self.vagal_tone * 0.85 + pfc * 0.15)

        # Polyvagal state: ventral vagal safe (1.0), sympathetic (0.5), dorsal shutdown (0.0)
        if self.vagal_tone > 0.60 and self.sympathetic_tone < 0.45:
            self.polyvagal_state = _lag(self.polyvagal_state, 0.85, 10)
        elif self.sympathetic_tone > 0.55:
            self.polyvagal_state = _lag(self.polyvagal_state, 0.45, 5)
        elif self.sympathetic_tone < 0.35 and self.parasympathetic_tone < 0.45:
            # Both low = dorsal vagal freeze/shutdown
            self.polyvagal_state = _lag(self.polyvagal_state, 0.10, 15)
        else:
            self.polyvagal_state = _lag(self.polyvagal_state, 0.65, 8)

        # Compute downstream organ drives
        s = self.sympathetic_tone
        p = self.parasympathetic_tone
        self.organ_drives = {
            # Cardiovascular
            "heart_rate_drive":         s * 0.7 - p * 0.6,
            "cardiac_contractility":    s * 0.6 - p * 0.3,
            "peripheral_resistance":    s * 0.8 - p * 0.2,
            "coronary_dilation":       -s * 0.2 + p * 0.1,   # SNS constricts coronaries
            # Respiratory
            "bronchodilation":          s * 0.6 - p * 0.5,
            "respiratory_rate_drive":   s * 0.5 - p * 0.2,
            # Digestive
            "gut_motility_drive":      -s * 0.7 + p * 0.8,
            "gastric_acid_drive":      -s * 0.4 + p * 0.6,
            "salivation_drive":        -s * 0.6 + p * 0.9,
            "anal_sphincter_relax":     s * 0.5 - p * 0.5,
            # Endocrine
            "adrenaline_release":       s * 0.9,
            "insulin_suppression":      s * 0.5,
            # Skin
            "sweating_drive":           s * 0.8,
            "piloerection_drive":       s * 0.7,
            "skin_vasoconstriction":    s * 0.7 - p * 0.1,
            # Eyes
            "pupil_dilation_drive":     s * 0.8 - p * 0.8,
            "lacrimation_drive":       -s * 0.3 + p * 0.7,
            # Bladder
            "bladder_relax":            s * 0.6 - p * 0.6,
            # Immune
            "nk_cell_suppression":      s * 0.4,
            # Reproductive
            "reproductive_arousal":    -s * 0.2 + p * 0.3,
        }

    def get_params(self) -> Dict[str, float]:
        return {
            "sympathetic_tone": round(self.sympathetic_tone, 4),
            "parasympathetic_tone": round(self.parasympathetic_tone, 4),
            "sns_pns_ratio": round(self.sns_pns_ratio, 4),
            "vagal_tone": round(self.vagal_tone, 4),
            "hrv": round(self.hrv, 4),
            "polyvagal_state": round(self.polyvagal_state, 4),
        }

    def get_drive(self, key: str, default: float = 0.0) -> float:
        return self.organ_drives.get(key, default)
