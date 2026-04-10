"""
hormonal.py — Full Peripheral Hormonal System

All major hormones beyond HPA axis:
  - Thyroid axis (TSH → T3/T4 → metabolic rate)
  - Sex hormones (testosterone, estrogen, progesterone, LH, FSH)
  - Growth hormone, prolactin
  - Melatonin (circadian)
  - Leptin / Ghrelin (hunger/satiety)
  - Vasopressin / ADH (water retention, social bonding)
  - Oxytocin peripheral (bonding, labor, milk ejection)
  - Insulin-like growth factor (IGF-1)

Each hormone has real physiological time constants.
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class HormonalSystem:

    def __init__(self):
        # Thyroid axis
        self.TSH     = 0.40  # thyroid-stimulating hormone (pituitary)
        self.T4      = 0.45  # thyroxine (pro-hormone)
        self.T3      = 0.45  # triiodothyronine (active)
        self.metabolic_rate = 0.50

        # Sex hormones
        self.testosterone  = 0.40
        self.estrogen      = 0.35
        self.progesterone  = 0.25
        self.LH            = 0.30   # luteinizing hormone
        self.FSH           = 0.30   # follicle-stimulating hormone
        self.prolactin     = 0.20

        # Growth
        self.growth_hormone = 0.30
        self.IGF1           = 0.40

        # Peptide/other
        self.melatonin          = 0.30
        self.leptin             = 0.50   # satiety (fat stores)
        self.ghrelin            = 0.40   # hunger (stomach)
        self.vasopressin        = 0.35   # ADH — water retention + social memory
        self.oxytocin_peripheral = 0.25  # bonding, trust, warmth
        self.substance_P_body   = 0.30   # pain, inflammation

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives: emotion_name, intensity, cortisol_blood, adrenaline,
                dopamine (brain NT), oxytocin (brain NT), serotonin
        """
        cortisol = drives.get("cortisol_blood", 0.30)
        adr      = drives.get("adrenaline", 0.15)
        dopamine = drives.get("dopamine", 0.50)
        oc_brain = drives.get("oxytocin_brain", 0.35)
        serotonin = drives.get("serotonin", 0.50)
        emotion  = drives.get("emotion_name", "calm").lower()
        intensity = drives.get("intensity", 0.5)
        tau = max(1.0, dt_ms / 100.0)

        # ── Thyroid axis ─────────────────────────────────────────────────────
        # Stress suppresses thyroid over time (adaptive)
        tsh_target = _clamp(0.40 - cortisol * 0.15 + 0.05 * (1 - intensity))
        self.TSH = _lag(self.TSH, tsh_target, 2000 * tau)

        t4_target = _clamp(self.TSH * 0.90)
        self.T4 = _lag(self.T4, t4_target, 3000 * tau)

        t3_target = _clamp(self.T4 * 0.85 - cortisol * 0.10)  # cortisol blocks T4→T3
        self.T3 = _lag(self.T3, t3_target, 2500 * tau)

        self.metabolic_rate = _clamp(0.40 + self.T3 * 0.25 - cortisol * 0.10)

        # ── Sex hormones ─────────────────────────────────────────────────────
        # Pregnenolone steal: chronic cortisol diverts to cortisol, away from sex hormones
        steal = cortisol * 0.30

        test_target = _clamp(0.40 - steal
                             + (0.10 if emotion in ("love", "lust", "desire", "ecstasy") else 0))
        self.testosterone = _lag(self.testosterone, test_target, 3000 * tau)

        estr_target = _clamp(0.35 - steal * 0.7
                             + (0.08 if emotion in ("love", "tenderness", "joy") else 0))
        self.estrogen = _lag(self.estrogen, estr_target, 3000 * tau)

        prog_target = _clamp(0.25 - steal * 0.5)
        self.progesterone = _lag(self.progesterone, prog_target, 4000 * tau)

        # LH/FSH: pituitary gonadotropins
        lh_target = _clamp(0.30 - cortisol * 0.20 + self.estrogen * 0.15)
        self.LH = _lag(self.LH, lh_target, 2500 * tau)
        self.FSH = _lag(self.FSH, _clamp(0.30 - cortisol * 0.15), 2500 * tau)

        # Prolactin: rises with stress, oxytocin, physical contact
        prl_target = _clamp(0.20 + cortisol * 0.15 + oc_brain * 0.10)
        self.prolactin = _lag(self.prolactin, prl_target, 1000 * tau)

        # ── Growth & repair ──────────────────────────────────────────────────
        # GH: pulsatile during sleep/calm; suppressed by cortisol
        gh_target = _clamp(0.30 - cortisol * 0.20 + (0.15 if emotion == "calm" else 0))
        self.growth_hormone = _lag(self.growth_hormone, gh_target, 2000 * tau)
        self.IGF1 = _lag(self.IGF1, _clamp(0.40 + self.growth_hormone * 0.20), 5000 * tau)

        # ── Peptide hormones ─────────────────────────────────────────────────
        # Melatonin: not driven by emotion in our model (circadian), holds steady
        self.melatonin = _lag(self.melatonin, 0.30, 10000 * tau)

        # Leptin: falls with stress (hunger signal) — chronic stress → overeating risk
        lep_target = _clamp(0.50 - cortisol * 0.20 - adr * 0.10)
        self.leptin = _lag(self.leptin, lep_target, 5000 * tau)

        # Ghrelin: inversely related to leptin; rises when leptin falls
        ghr_target = _clamp(0.60 - self.leptin * 0.40)
        self.ghrelin = _lag(self.ghrelin, ghr_target, 3000 * tau)

        # Vasopressin: stress + social threat + dehydration
        vaso_target = _clamp(0.35 + cortisol * 0.20 + (0.10 if emotion == "fear" else 0))
        self.vasopressin = _lag(self.vasopressin, vaso_target, 500 * tau)

        # Oxytocin peripheral: mirrored from brain oxytocin NT
        oc_target = _clamp(oc_brain * 0.85 + self.estrogen * 0.10)
        self.oxytocin_peripheral = _lag(self.oxytocin_peripheral, oc_target, 300 * tau)

        # Substance P: pain/stress neurochemical
        sp_target = _clamp(0.30 + cortisol * 0.15 + adr * 0.10)
        self.substance_P_body = _lag(self.substance_P_body, sp_target, 400 * tau)

    def get_params(self) -> Dict:
        return {
            "TSH": round(self.TSH, 3),
            "T3": round(self.T3, 3),
            "T4": round(self.T4, 3),
            "metabolic_rate": round(self.metabolic_rate, 3),
            "testosterone": round(self.testosterone, 3),
            "estrogen": round(self.estrogen, 3),
            "progesterone": round(self.progesterone, 3),
            "LH": round(self.LH, 3),
            "FSH": round(self.FSH, 3),
            "prolactin": round(self.prolactin, 3),
            "growth_hormone": round(self.growth_hormone, 3),
            "IGF1": round(self.IGF1, 3),
            "melatonin": round(self.melatonin, 3),
            "leptin": round(self.leptin, 3),
            "ghrelin": round(self.ghrelin, 3),
            "vasopressin": round(self.vasopressin, 3),
            "oxytocin_peripheral": round(self.oxytocin_peripheral, 3),
            "substance_P": round(self.substance_P_body, 3),
        }
