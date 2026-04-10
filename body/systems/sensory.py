"""
sensory.py — All Five Senses + Proprioception + Interoception

Eyes, ears, nose, tongue, skin (tactile), vestibular, and
the insula-mediated interoceptive sense of the body itself.

Models:
  - Pupil diameter (SNS dilates, PNS constricts)
  - Visual acuity and tunnel vision under stress
  - Auditory threshold shift (hyperacusis under stress)
  - Olfactory sensitivity (suppressed by cortisol)
  - Taste sensitivity and hedonic value
  - Tactile/pain thresholds (endorphins raise, stress lowers)
  - Vestibular stability (anxiety → dizziness)
  - Interoceptive accuracy (how well the body senses itself)
  - Tear production (lacrimation)
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class SensorySystem:

    def __init__(self):
        # Vision
        self.pupil_mm           = 3.5   # mm (2-8mm range)
        self.visual_acuity      = 0.80  # [0,1]
        self.peripheral_vision  = 0.75  # narrows under stress (tunnel vision)
        self.lacrimation        = 0.10  # tear production [0,1]
        self.blink_rate         = 15.0  # blinks/min (low=concentration, high=stress)
        self.accommodation      = 0.50  # lens focusing [0,1]

        # Auditory
        self.auditory_sensitivity = 0.55  # [0,1] (higher = more sensitive)
        self.auditory_threshold_db = 0.0  # shift from normal (positive = hyperacusis)
        self.startle_sensitivity  = 0.40  # [0,1]

        # Olfactory
        self.olfactory_sensitivity = 0.50
        self.olfactory_fatigue     = 0.10  # adaptation rate

        # Gustatory (taste)
        self.taste_sensitivity   = 0.50
        self.taste_hedonic       = 0.50  # how pleasant things taste [0,1]
        self.appetite_taste_link = 0.50

        # Tactile / somatosensory
        self.tactile_sensitivity = 0.55
        self.pain_threshold      = 0.50  # higher = less sensitive to pain
        self.temperature_sensitivity = 0.50
        self.itch_threshold      = 0.50

        # Vestibular
        self.vestibular_stability = 0.75
        self.dizziness           = 0.00
        self.nausea_vestibular   = 0.00

        # Interoception — insula-mediated body-sensing
        self.interoceptive_accuracy = 0.55  # how accurate the body's self-perception is
        self.heartbeat_awareness    = 0.30  # can the person "feel" their heartbeat?

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives: pupil_dilation_drive, lacrimation_drive, cortisol_blood,
                adrenaline, endorphins (brain), oxytocin, emotion_name,
                intensity, heart_rate, pCO2
        """
        pupil_drive  = drives.get("pupil_dilation_drive", 0.0)
        lacr_drive   = drives.get("lacrimation_drive", 0.0)
        cortisol     = drives.get("cortisol_blood", 0.30)
        adr          = drives.get("adrenaline", 0.15)
        endorphins   = drives.get("endorphins", 0.30)
        oxytocin     = drives.get("oxytocin_brain", 0.35)
        emotion      = drives.get("emotion_name", "calm").lower()
        intensity    = drives.get("intensity", 0.5)
        heart_rate   = drives.get("heart_rate", 70.0)
        pCO2         = drives.get("pCO2", 40.0)
        tau = max(1.0, dt_ms / 100.0)

        # ── Vision ────────────────────────────────────────────────────────────
        # Pupil: 2mm (bright/calm) to 8mm (dark/aroused/dilated)
        # SNS drives dilation; PNS drives constriction; emotional interest dilates
        pupil_target = 3.5 + pupil_drive * 2.5
        if emotion in ("awe", "love", "interest", "joy"):
            pupil_target += 0.5 * intensity  # cognitive dilation
        elif emotion in ("disgust",):
            pupil_target -= 0.3 * intensity  # constriction
        pupil_target = max(2.0, min(8.0, pupil_target))
        self.pupil_mm = _lag(self.pupil_mm, pupil_target, 3 * tau)

        # Tunnel vision / peripheral narrowing under acute stress
        periph_target = _clamp(0.75 - adr * 0.35 + oxytocin * 0.10)
        self.peripheral_vision = _lag(self.peripheral_vision, periph_target, 5 * tau)

        # Visual acuity: slightly reduced under high arousal (saccadic suppression)
        acuity_target = _clamp(0.80 - (adr * 0.15) + (endorphins - 0.30) * 0.10)
        self.visual_acuity = _lag(self.visual_acuity, acuity_target, 8 * tau)

        # Lacrimation: PNS + grief + joy + pain
        lacr_target = _clamp(0.10 + lacr_drive * 0.40)
        if emotion in ("grief", "sadness", "sorrow"):
            lacr_target = _clamp(lacr_target + 0.60 * intensity)
        elif emotion in ("joy", "ecstasy", "love"):
            lacr_target = _clamp(lacr_target + 0.25 * intensity)  # tears of joy
        elif emotion in ("pain",):
            lacr_target = _clamp(lacr_target + 0.40 * intensity)
        self.lacrimation = _lag(self.lacrimation, lacr_target, 4 * tau)

        # Blink rate: low during focus/fear fixation, high during stress
        blink_target = 15.0
        if emotion in ("fear", "shock"):
            blink_target = 8.0  # freeze stare
        elif emotion in ("anxiety", "panic"):
            blink_target = 24.0
        self.blink_rate = _lag(self.blink_rate, blink_target, 10 * tau)

        # ── Auditory ──────────────────────────────────────────────────────────
        # Hyperacusis: stress lowers threshold (sounds feel louder)
        thresh_target = cortisol * 15.0 + adr * 10.0  # dB equivalent shift
        self.auditory_threshold_db = _lag(self.auditory_threshold_db, thresh_target, 15 * tau)
        self.auditory_sensitivity = _clamp(0.55 + thresh_target / 50.0)

        # Startle reflex: amygdala-mediated, higher under SNS dominance
        startle_target = _clamp(0.40 + adr * 0.30 + cortisol * 0.15)
        self.startle_sensitivity = _lag(self.startle_sensitivity, startle_target, 8 * tau)

        # ── Olfactory ─────────────────────────────────────────────────────────
        # Cortisol blunts smell (chronic stress → anosmia)
        olf_target = _clamp(0.50 - cortisol * 0.25)
        self.olfactory_sensitivity = _lag(self.olfactory_sensitivity, olf_target, 100 * tau)

        # ── Gustatory ─────────────────────────────────────────────────────────
        taste_target = _clamp(0.50 - cortisol * 0.15)
        self.taste_sensitivity = _lag(self.taste_sensitivity, taste_target, 50 * tau)

        # Hedonic value of taste: positive with serotonin/dopamine, negative with stress
        dopamine = drives.get("dopamine", 0.50)
        hedonic_target = _clamp(0.50 + (dopamine - 0.50) * 0.30 - cortisol * 0.20)
        self.taste_hedonic = _lag(self.taste_hedonic, hedonic_target, 50 * tau)

        # ── Tactile / Pain ────────────────────────────────────────────────────
        # Pain threshold: endorphins raise it, inflammation lowers it
        pain_thresh_target = _clamp(0.50 + endorphins * 0.35 - cortisol * 0.10)
        self.pain_threshold = _lag(self.pain_threshold, pain_thresh_target, 10 * tau)

        # ── Vestibular ────────────────────────────────────────────────────────
        # Anxiety + hyperventilation (low pCO2) → dizziness
        dizzy_target = 0.0
        if pCO2 < 35.0:  # hypocapnia from hyperventilation
            dizzy_target += (35.0 - pCO2) / 20.0
        dizzy_target += max(0, (adr - 0.5) * 0.30)
        dizzy_target = _clamp(dizzy_target)
        self.dizziness = _lag(self.dizziness, dizzy_target, 6 * tau)

        vestib_target = _clamp(0.75 - self.dizziness * 0.60)
        self.vestibular_stability = _lag(self.vestibular_stability, vestib_target, 8 * tau)

        # ── Interoception ─────────────────────────────────────────────────────
        # High arousal + insula activity → heightened body awareness
        intero_target = _clamp(0.55 + adr * 0.20 - cortisol * 0.10)
        self.interoceptive_accuracy = _lag(self.interoceptive_accuracy, intero_target, 20 * tau)

        # Heartbeat awareness: rises with HR and interoceptive focus
        hb_target = _clamp((heart_rate - 70.0) / 60.0 * 0.5 + self.interoceptive_accuracy * 0.3)
        self.heartbeat_awareness = _lag(self.heartbeat_awareness, hb_target, 15 * tau)

    def get_params(self) -> Dict:
        return {
            "pupil_mm": round(self.pupil_mm, 2),
            "peripheral_vision": round(self.peripheral_vision, 3),
            "visual_acuity": round(self.visual_acuity, 3),
            "lacrimation": round(self.lacrimation, 3),
            "blink_rate": round(self.blink_rate, 1),
            "auditory_sensitivity": round(self.auditory_sensitivity, 3),
            "auditory_threshold_db_shift": round(self.auditory_threshold_db, 2),
            "startle_sensitivity": round(self.startle_sensitivity, 3),
            "olfactory_sensitivity": round(self.olfactory_sensitivity, 3),
            "taste_sensitivity": round(self.taste_sensitivity, 3),
            "taste_hedonic": round(self.taste_hedonic, 3),
            "pain_threshold": round(self.pain_threshold, 3),
            "vestibular_stability": round(self.vestibular_stability, 3),
            "dizziness": round(self.dizziness, 3),
            "interoceptive_accuracy": round(self.interoceptive_accuracy, 3),
            "heartbeat_awareness": round(self.heartbeat_awareness, 3),
        }
