"""
body_engine.py — The Human Body Simulation Engine

Integrates all 12 organ systems with the existing BrainEngine via
bidirectional brain↔body connections:

  EFFERENT (brain → body):
    hypothalamus → ANS → all organs
    amygdala → SNS surge → adrenaline, HR, tension
    brainstem → heart, lungs, gut (vagal)
    vmPFC → vagal brake → calm
    motor cortex → muscles
    raphe → ENS serotonin
    HPA axis: amygdala → CRH → ACTH → cortisol (3-stage cascade)

  AFFERENT (body → brain):
    vagal signal (gut health, heart rate) → brainstem → insula
    skin conductance → insula → amygdala
    muscle tension → S1 → ACC
    pain → PAG → insula → ACC
    hypocapnia → aI → amygdala (panic loop)
    sickness behavior → dmPFC (withdrawal)

Each call to process_emotion() runs a full tick of the body
synchronized with the brain's emotional state.
"""

import math
import time
from typing import Dict, List, Optional

from .systems import (
    ANSSystem, CardiovascularSystem, RespiratorySystem,
    HPAAxis, HormonalSystem, DigestiveSystem, ImmuneSystem,
    MusculoskeletalSystem, IntegumentarySystem, SensorySystem,
    UrinarySystem, ReproductiveSystem,
)
from .organs import ORGANS, TOTAL_ORGANS


class BodyEngine:

    def __init__(self):
        # All 12 organ systems
        self.ans          = ANSSystem()
        self.cardiovascular = CardiovascularSystem()
        self.respiratory  = RespiratorySystem()
        self.hpa          = HPAAxis()
        self.hormonal     = HormonalSystem()
        self.digestive    = DigestiveSystem()
        self.immune       = ImmuneSystem()
        self.musculoskeletal = MusculoskeletalSystem()
        self.integumentary = IntegumentarySystem()
        self.sensory      = SensorySystem()
        self.urinary      = UrinarySystem()
        self.reproductive = ReproductiveSystem()

        self.current_emotion  = "Calm"
        self.current_intensity = 0.5
        self.t_ms             = 0.0
        self.history: List[Dict] = []

        print(f"[BODY ENGINE] Initialized")
        print(f"  Organs: {TOTAL_ORGANS}")
        print(f"  Systems: 12 (ANS, CV, Resp, HPA, Hormonal, GI, Immune, MSK, Skin, Sensory, Urinary, Reproductive)")

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    def tick_background(self, dt_ms: float = 100.0):
        """Advance body between conversations using live brain NT state.
        Pulls current NT levels from the shared NT_SYSTEMS so body and brain
        stay synchronized even when Claude isn't generating text."""
        try:
            from feeling_engine.brain.neurotransmitters import NT_SYSTEMS as _NT
            nt = {k: v.current_level for k, v in _NT.items()}
        except Exception:
            nt = {}

        try:
            from feeling_engine.brain import get_brain as _gb
            brain_sim = _gb().sim
            region_act = {ab: st.get_activity() for ab, st in brain_sim.states.items()}
        except Exception:
            region_act = {}

        signals = {
            "emotion_name":    self.current_emotion,
            "intensity":       self.current_intensity,
            "dopamine":        nt.get("dopamine",       0.50),
            "serotonin":       nt.get("serotonin",      0.50),
            "norepinephrine":  nt.get("norepinephrine", 0.45),
            "gaba":            nt.get("gaba",           0.55),
            "acetylcholine":   nt.get("acetylcholine",  0.45),
            "oxytocin_brain":  nt.get("oxytocin",       0.35),
            "endorphins":      nt.get("endorphins",      0.30),
            "cortisol":        self.hpa.cortisol_blood,
            "anandamide":      nt.get("anandamide",     0.35),
            "substance_P":     nt.get("substance_P",    0.30),
            "hypothalamus":    region_act.get("hypothalamus", 0.35),
            "brainstem":       region_act.get("brainstem",    0.40),
            "amygdala":        region_act.get("amygdala",     0.25),
            "vmPFC":           region_act.get("vmPFC",        0.45),
            "mPFC":            region_act.get("mPFC",         0.45),
            "NAcc":            region_act.get("NAcc",         0.35),
            "VTA":             region_act.get("VTA",          0.35),
            "aI":              region_act.get("aI",           0.35),
            "PAG":             region_act.get("PAG",          0.30),
            "M1":              region_act.get("M1",           0.25),
            "SMA":             region_act.get("SMA",          0.25),
            "raphe":           region_act.get("raphe",        0.40),
            "locus_coeruleus": region_act.get("locus_coeruleus", 0.35),
            "hippocampus":     region_act.get("hippocampus",  0.35),
        }
        self._tick_all(dt_ms, signals)

    def inject_drives(self, drives: dict):
        """Directly spike physiological state — bypasses brain pathway.
        Used for somatic commands: run, breathe, panic, relax, etc.
        Values are DELTAS applied immediately; systems decay naturally."""
        clamp = lambda v: max(0.0, min(1.0, v))

        if "heart_rate_delta" in drives:
            self.cardiovascular.heart_rate = max(35.0, min(220.0,
                self.cardiovascular.heart_rate + drives["heart_rate_delta"]))
        if "resp_rate_delta" in drives:
            self.respiratory.respiratory_rate = max(6.0, min(60.0,
                self.respiratory.respiratory_rate + drives["resp_rate_delta"]))
        if "adrenaline_delta" in drives:
            self.hpa.adrenaline = clamp(self.hpa.adrenaline + drives["adrenaline_delta"])
        if "cortisol_delta" in drives:
            self.hpa.cortisol_blood = clamp(self.hpa.cortisol_blood + drives["cortisol_delta"])
        if "sympathetic_delta" in drives:
            self.ans.sympathetic_tone = clamp(self.ans.sympathetic_tone + drives["sympathetic_delta"])
        if "vagal_delta" in drives:
            self.ans.vagal_tone = clamp(self.ans.vagal_tone + drives["vagal_delta"])
        if "tension_delta" in drives:
            self.musculoskeletal.global_tension = clamp(
                self.musculoskeletal.global_tension + drives["tension_delta"])
            self.musculoskeletal.trapezius_tension = clamp(
                self.musculoskeletal.trapezius_tension + drives["tension_delta"] * 0.8)
        if "sweating_delta" in drives:
            self.integumentary.sweating_eccrine = clamp(
                self.integumentary.sweating_eccrine + drives["sweating_delta"])
        if "tidal_volume_delta" in drives:
            self.respiratory.tidal_volume = max(200.0, min(2500.0,
                self.respiratory.tidal_volume + drives["tidal_volume_delta"]))
        if "emotion_name" in drives:
            self.current_emotion = drives["emotion_name"]
        if "intensity" in drives:
            self.current_intensity = clamp(drives["intensity"])

    def process_emotion(self, emotion_name: str, intensity: float,
                        brain_result: Dict, dt_ms: float = 200.0) -> Dict:
        """
        Main entry point — called after brain.process_emotion().
        Takes brain result, ticks all body systems, returns body state.
        """
        self.current_emotion   = emotion_name
        self.current_intensity = intensity

        # Extract brain signals for body
        brain_signals = self._extract_brain_signals(brain_result)
        brain_signals["emotion_name"] = emotion_name
        brain_signals["intensity"]    = intensity

        # Tick all systems in dependency order
        self._tick_all(dt_ms, brain_signals)

        snapshot = self.get_snapshot()
        self.history.append({
            "emotion": emotion_name,
            "t_ms": self.t_ms,
            "vitals": snapshot["vitals"],
        })
        if len(self.history) > 200:
            self.history.pop(0)

        return snapshot

    def get_snapshot(self) -> Dict:
        """Full body state for frontend."""
        cv   = self.cardiovascular.get_params()
        resp = self.respiratory.get_params()
        integ = self.integumentary.get_params()
        sens = self.sensory.get_params()

        return {
            "t_ms":             round(self.t_ms, 1),
            "current_emotion":  self.current_emotion,
            "ans":              self.ans.get_params(),
            "cardiovascular":   cv,
            "respiratory":      resp,
            "hpa":              self.hpa.get_params(),
            "hormonal":         self.hormonal.get_params(),
            "digestive":        self.digestive.get_params(),
            "immune":           self.immune.get_params(),
            "musculoskeletal":  self.musculoskeletal.get_params(),
            "integumentary":    integ,
            "sensory":          sens,
            "urinary":          self.urinary.get_params(),
            "reproductive":     self.reproductive.get_params(),
            "vitals":           self._compute_vitals(cv, resp, integ, sens),
            "organ_activities": self._compute_organ_activities(),
            "afferent_signals": self._compute_afferent_signals(),
        }

    def get_afferent_brain_drives(self) -> Dict[str, float]:
        """
        Body → brain feedback drives.
        Returns {brain_region_abbrev: drive_delta} for BrainEngine to apply.
        """
        signals = self._compute_afferent_signals()
        drives = {}

        # Vagal afferent (gut + heart → brainstem → insula)
        vag = self.digestive.vagal_afferent_signal
        drives["brainstem"]     = drives.get("brainstem", 0) + vag * 0.20
        drives["aI"]            = drives.get("aI", 0) + vag * 0.15

        # High heart rate → insula → ACC (body awareness)
        hr_signal = max(0, (self.cardiovascular.heart_rate - 70.0) / 50.0)
        drives["aI"]            = drives.get("aI", 0) + hr_signal * 0.18
        drives["ACC"]           = drives.get("ACC", 0) + hr_signal * 0.10

        # Skin conductance → amygdala (threat signal from periphery)
        gsr_norm = max(0, (self.integumentary.skin_conductance - 5.0) / 20.0)
        drives["amygdala"]      = drives.get("amygdala", 0) + gsr_norm * 0.15

        # Muscle tension → S1 → ACC
        tension = self.musculoskeletal.global_tension
        drives["S1"]            = drives.get("S1", 0) + tension * 0.10
        drives["ACC"]           = drives.get("ACC", 0) + tension * 0.08

        # Hypocapnia (over-breathing) → aI → amygdala (panic loop)
        if self.respiratory.pCO2 < 35.0:
            hypocapnia = (35.0 - self.respiratory.pCO2) / 15.0
            drives["aI"]        = drives.get("aI", 0) + hypocapnia * 0.20
            drives["amygdala"]  = drives.get("amygdala", 0) + hypocapnia * 0.15

        # Sickness behavior → dmPFC (withdrawal/fatigue signal)
        sick = self.immune.sickness_behavior
        if sick > 0.25:
            drives["mPFC"]      = drives.get("mPFC", 0) - sick * 0.15
            drives["NAcc"]      = drives.get("NAcc", 0) - sick * 0.10

        # High nausea → aI → brainstem (vomiting center)
        nausea = self.digestive.nausea
        if nausea > 0.30:
            drives["aI"]        = drives.get("aI", 0) + nausea * 0.18
            drives["brainstem"] = drives.get("brainstem", 0) + nausea * 0.15

        # Positive vagal/gut signal → vmPFC (safety signal)
        if vag > 0.55:
            drives["vmPFC"]     = drives.get("vmPFC", 0) + (vag - 0.55) * 0.20

        # High arousal/pleasure → NAcc (reward signal from body)
        pleasure = self.reproductive.endorphin_pleasure
        if pleasure > 0.30:
            drives["NAcc"]      = drives.get("NAcc", 0) + pleasure * 0.12

        return {k: round(v, 4) for k, v in drives.items()}

    # ── INTERNAL ──────────────────────────────────────────────────────────────

    def _extract_brain_signals(self, brain_result: Dict) -> Dict:
        """Pull the signals the body needs from the brain result dict."""
        nt = brain_result.get("nt_levels", {})
        regions = {r["abbrev"]: r["activity"]
                   for r in brain_result.get("active_regions", [])}
        region_all = brain_result.get("region_activities", regions)

        def r(abbrev): return region_all.get(abbrev, regions.get(abbrev, 0.30))

        return {
            # NTs
            "dopamine":        nt.get("dopamine", 0.50),
            "serotonin":       nt.get("serotonin", 0.50),
            "norepinephrine":  nt.get("norepinephrine", 0.45),
            "gaba":            nt.get("gaba", 0.55),
            "acetylcholine":   nt.get("acetylcholine", 0.45),
            "oxytocin_brain":  nt.get("oxytocin", 0.35),
            "endorphins":      nt.get("endorphins", 0.30),
            "cortisol":        nt.get("cortisol", 0.30),
            "anandamide":      nt.get("anandamide", 0.35),
            "substance_P":     nt.get("substance_P", 0.30),
            # Key brain regions
            "hypothalamus":    r("hypothalamus"),
            "brainstem":       r("brainstem"),
            "amygdala":        r("amygdala"),
            "vmPFC":           r("vmPFC"),
            "mPFC":            r("mPFC"),
            "NAcc":            r("NAcc"),
            "VTA":             r("VTA"),
            "aI":              r("aI"),
            "PAG":             r("PAG"),
            "M1":              r("M1"),
            "SMA":             r("SMA"),
            "raphe":           r("raphe"),
            "locus_coeruleus": r("locus_coeruleus"),
            "hippocampus":     r("hippocampus"),
        }

    def _tick_all(self, dt_ms: float, signals: Dict):
        """Tick all systems in physiological dependency order."""
        emotion   = signals["emotion_name"]
        intensity = signals["intensity"]

        # 1. ANS first — it drives most other systems
        self.ans.tick(dt_ms, {
            "hypothalamus":   signals["hypothalamus"],
            "brainstem":      signals["brainstem"],
            "amygdala":       signals["amygdala"],
            "vmPFC":          signals["vmPFC"],
            "norepinephrine": signals["norepinephrine"],
            "acetylcholine":  signals["acetylcholine"],
            "cortisol":       signals["cortisol"],
            "intensity":      intensity,
        })
        ans_drives = self.ans.organ_drives
        ans_params = self.ans.get_params()

        # 2. HPA axis (stress cascade — slow hormones)
        self.hpa.tick(dt_ms, {
            "amygdala":         signals["amygdala"],
            "hypothalamus":     signals["hypothalamus"],
            "intensity":        intensity,
            "sympathetic_tone": ans_params["sympathetic_tone"],
        })
        hpa = self.hpa.get_params()

        # 3. Cardiovascular
        self.cardiovascular.tick(dt_ms, ans_drives,
                                  resp_phase=self.respiratory.breath_phase)

        # 4. Respiratory
        self.respiratory.tick(dt_ms, {
            **ans_drives,
            "emotion_type": emotion.lower(),
            "intensity": intensity,
        })

        # 5. Hormonal (depends on HPA and brain NTs)
        self.hormonal.tick(dt_ms, {
            "cortisol_blood":  hpa["cortisol_blood"],
            "adrenaline":      hpa["adrenaline"],
            "dopamine":        signals["dopamine"],
            "serotonin":       signals["serotonin"],
            "oxytocin_brain":  signals["oxytocin_brain"],
            "emotion_name":    emotion,
            "intensity":       intensity,
        })
        hormonal = self.hormonal.get_params()
        cv = self.cardiovascular.get_params()

        # 6. Digestive (gut-brain axis)
        self.digestive.tick(dt_ms, {
            **ans_drives,
            "cortisol_blood": hpa["cortisol_blood"],
            "adrenaline":     hpa["adrenaline"],
            "serotonin":      signals["serotonin"],
            "emotion_name":   emotion,
            "ghrelin":        hormonal["ghrelin"],
            "leptin":         hormonal["leptin"],
        })

        # 7. Immune
        self.immune.tick(dt_ms, {
            "cortisol_blood":  hpa["cortisol_blood"],
            "adrenaline":      hpa["adrenaline"],
            "oxytocin_brain":  signals["oxytocin_brain"],
            "sympathetic_tone": ans_params["sympathetic_tone"],
            "emotion_name":    emotion,
            "intensity":       intensity,
        })

        # 8. Musculoskeletal
        self.musculoskeletal.tick(dt_ms, {
            "sympathetic_tone": ans_params["sympathetic_tone"],
            "adrenaline":      hpa["adrenaline"],
            "cortisol_blood":  hpa["cortisol_blood"],
            "intensity":       intensity,
            "emotion_name":    emotion,
            "M1":              signals["M1"],
            "SMA":             signals["SMA"],
            "PAG":             signals["PAG"],
            "vmPFC":           signals["vmPFC"],
            "endorphins":      signals["endorphins"],
        })

        # 9. Integumentary (skin — reflects everything)
        self.integumentary.tick(dt_ms, {
            **ans_drives,
            "cortisol_blood":      hpa["cortisol_blood"],
            "adrenaline":          hpa["adrenaline"],
            "oxytocin_peripheral": hormonal["oxytocin_peripheral"],
            "emotion_name":        emotion,
            "intensity":           intensity,
            "metabolic_rate":      hormonal["metabolic_rate"],
        })

        # 10. Sensory
        self.sensory.tick(dt_ms, {
            **ans_drives,
            "cortisol_blood":  hpa["cortisol_blood"],
            "adrenaline":      hpa["adrenaline"],
            "endorphins":      signals["endorphins"],
            "oxytocin_brain":  signals["oxytocin_brain"],
            "dopamine":        signals["dopamine"],
            "emotion_name":    emotion,
            "intensity":       intensity,
            "heart_rate":      cv["heart_rate"],
            "pCO2":            self.respiratory.pCO2,
        })

        # 11. Urinary
        self.urinary.tick(dt_ms, {
            "sympathetic_tone":        ans_params["sympathetic_tone"],
            "cortisol_blood":          hpa["cortisol_blood"],
            "adrenaline":              hpa["adrenaline"],
            "vasopressin":             hormonal["vasopressin"],
            "aldosterone":             hpa["aldosterone"],
            "mean_arterial_pressure":  cv["mean_arterial_pressure"],
            "emotion_name":            emotion,
            "intensity":               intensity,
        })

        # 12. Reproductive
        self.reproductive.tick(dt_ms, {
            "cortisol_blood":    hpa["cortisol_blood"],
            "adrenaline":        hpa["adrenaline"],
            "oxytocin_brain":    signals["oxytocin_brain"],
            "dopamine":          signals["dopamine"],
            "endorphins":        signals["endorphins"],
            "testosterone":      hormonal["testosterone"],
            "estrogen":          hormonal["estrogen"],
            "sympathetic_tone":  ans_params["sympathetic_tone"],
            "parasympathetic_tone": ans_params["parasympathetic_tone"],
            "emotion_name":      emotion,
            "intensity":         intensity,
        })

        self.t_ms += dt_ms

    def _compute_vitals(self, cv, resp, integ, sens) -> Dict:
        """Key vitals strip — what you'd see on a medical monitor."""
        hpa = self.hpa.get_params()
        ans = self.ans.get_params()
        return {
            "heart_rate_bpm":   cv["heart_rate"],
            "systolic_bp":      cv["systolic_bp"],
            "diastolic_bp":     cv["diastolic_bp"],
            "respiratory_rate": resp["respiratory_rate"],
            "SpO2_pct":         resp["SpO2"],
            "pCO2_mmhg":        resp["pCO2"],
            "skin_conductance_us": integ["skin_conductance_us"],
            "skin_temp_c":      integ["skin_temp_c"],
            "core_temp_c":      integ["core_temp_c"],
            "pupil_mm":         sens["pupil_mm"],
            "adrenaline":       round(hpa["adrenaline"], 3),
            "cortisol_blood":   round(hpa["cortisol_blood"], 3),
            "vagal_tone":       round(ans["vagal_tone"], 3),
            "polyvagal_state":  round(ans["polyvagal_state"], 3),
        }

    def _compute_organ_activities(self) -> Dict[str, float]:
        """
        Normalized activity [0,1] for each organ — used by frontend
        to light up the body canvas exactly as brainAct lights up the brain.
        """
        cv    = self.cardiovascular.get_params()
        resp  = self.respiratory.get_params()
        hpa   = self.hpa.get_params()
        ans   = self.ans.get_params()
        integ = self.integumentary.get_params()
        sens  = self.sensory.get_params()
        msk   = self.musculoskeletal.get_params()
        dig   = self.digestive.get_params()
        imm   = self.immune.get_params()
        repro = self.reproductive.get_params()
        horm  = self.hormonal.get_params()
        urin  = self.urinary.get_params()

        def _norm_hr(hr): return min(1.0, max(0.0, (hr - 50.0) / 100.0))
        def _norm_bp(bp): return min(1.0, max(0.0, (bp - 80.0) / 80.0))

        return {
            "brain":           0.60,  # brain handled separately
            "eye_L":           _norm(sens["pupil_mm"], 2.0, 8.0),
            "eye_R":           _norm(sens["pupil_mm"], 2.0, 8.0),
            "ear_L":           sens["auditory_sensitivity"],
            "ear_R":           sens["auditory_sensitivity"],
            "nose":            sens["olfactory_sensitivity"],
            "tongue":          sens["taste_sensitivity"],
            "salivary":        dig["salivation"],
            "pituitary":       _norm(horm["ACTH"] if "ACTH" in horm else 0.3, 0, 1) if False else horm.get("prolactin", 0.3),
            "pineal":          horm["melatonin"],
            "thyroid":         horm["T3"],
            "parathyroid":     0.35,
            "larynx":          0.35,
            "heart":           _norm_hr(cv["heart_rate"]) * 0.7 + cv["beat_pulse"] * 0.3,
            "lung_L":          resp["lung_fill"],
            "lung_R":          resp["lung_fill"],
            "diaphragm":       abs(math.sin(resp["breath_phase"] * 2 * math.pi)) * 0.6 + 0.2,
            "thymus":          imm["t_cell_activity"],
            "liver":           dig["liver_glycogen"],
            "stomach":         dig["gut_motility"] * 0.5 + dig["gastric_acid"] * 0.5,
            "pancreas":        horm.get("insulin", 0.45),
            "spleen":          imm["nk_cell_activity"],
            "gallbladder":     dig.get("bile_flow", 0.40),
            "small_intestine": dig["gut_motility"],
            "large_intestine": dig["intestinal_permeability"] * 0.3 + dig["gut_motility"] * 0.7,
            "kidney_L":        urin["GFR"],
            "kidney_R":        urin["GFR"],
            "adrenal_L":       hpa["adrenaline"],
            "adrenal_R":       hpa["cortisol_blood"],
            "bladder":         urin["bladder_fullness"],
            "gonads":          repro["libido"],
            "arm_L":           msk["motor_readiness"] * 0.5 + msk["global_tension"] * 0.5,
            "arm_R":           msk["motor_readiness"] * 0.5 + msk["global_tension"] * 0.5,
            "leg_L":           msk["limb_blood_flow"],
            "leg_R":           msk["limb_blood_flow"],
            "hand_L":          msk["tremor_amplitude"] * 0.3 + integ["sweating_palmar"] * 0.7,
            "hand_R":          msk["tremor_amplitude"] * 0.3 + integ["sweating_palmar"] * 0.7,
            "skin_torso":      integ["skin_conductance_us"] / 30.0,
            "skin_face":       max(integ["flushing"], integ["blushing"], integ["pallor"]),
            "trapezius":       msk["trapezius_tension"],
            "jaw":             msk["jaw_tension"],
            "vagus":           ans["vagal_tone"],
            "ENS":             dig["ens_serotonin"],
            "lymphatics":      imm["lymphatic_flow"],
        }

    def _compute_afferent_signals(self) -> Dict[str, float]:
        """Named signals sent from body to brain."""
        return {
            "vagal_afferent":      round(self.digestive.vagal_afferent_signal, 3),
            "gut_serotonin":       round(self.digestive.ens_serotonin, 3),
            "heart_rate_signal":   round(max(0, (self.cardiovascular.heart_rate - 70) / 60), 3),
            "skin_conductance_signal": round(max(0, (self.integumentary.skin_conductance - 5) / 25), 3),
            "muscle_tension_signal": round(self.musculoskeletal.global_tension, 3),
            "nausea_signal":       round(self.digestive.nausea, 3),
            "sickness_signal":     round(self.immune.sickness_behavior, 3),
            "hypocapnia":          round(max(0, (35.0 - self.respiratory.pCO2) / 15.0), 3),
            "pain_signal":         round(max(0, 1.0 - self.sensory.pain_threshold), 3),
        }


def _norm(v: float, lo: float, hi: float) -> float:
    return max(0.0, min(1.0, (v - lo) / (hi - lo + 1e-9)))
