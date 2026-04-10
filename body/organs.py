"""
organs.py — Complete Human Organ Registry

Every organ in the human body, modeled with:
  - Anatomical identity and system membership
  - Normalized canvas position (x=0 left, x=1 right; y=0 head, y=1 feet)
  - Physiological baseline parameters
  - Brain region connections (efferent and afferent)
  - Autonomic innervation ratios
  - Visualization properties

~80 organs covering all major and minor structures.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Organ:
    name: str
    abbrev: str
    system: str           # organ system category
    body_region: str      # head / neck / thorax / abdomen / pelvis / limbs / skin
    mass_g: float         # approximate mass in grams
    # Canvas visualization
    vx: float             # normalized x position [0,1] on body canvas
    vy: float             # normalized y position [0,1] on body canvas
    viz_shape: str        # circle / ellipse / line / custom
    color_rest: str       # hex color at baseline
    color_active: str     # hex color at peak activation
    # Physiology
    baseline_activity: float   # [0,1]
    sympathetic_effect: float  # +1 = SNS activates, -1 = SNS suppresses
    parasympathetic_effect: float  # +1 = PNS activates, -1 = PNS suppresses
    brain_efferent: List[str]  # brain regions that drive this organ
    brain_afferent: List[str]  # brain regions this organ reports to
    # optional physiological params dict (used by systems)
    params: Dict[str, float] = field(default_factory=dict)
    notes: str = ""


# ── ORGAN REGISTRY ────────────────────────────────────────────────────────────

ORGANS: Dict[str, Organ] = {}

def _o(organ: Organ) -> Organ:
    ORGANS[organ.abbrev] = organ
    return organ


# ── HEAD ──────────────────────────────────────────────────────────────────────

_o(Organ("Brain", "brain", "nervous", "head", 1400,
    0.50, 0.06, "ellipse", "1a1a4a", "6688ff",
    0.50, 0.2, 0.1,
    brain_efferent=[], brain_afferent=[],
    notes="Handled by BrainEngine separately"))

_o(Organ("Eye Left", "eye_L", "sensory", "head", 7.5,
    0.43, 0.095, "circle", "1a2040", "44aaff",
    0.45, 0.6, -0.5,  # SNS dilates pupil, PNS constricts
    brain_efferent=["visual_cortex", "FPC", "SC"],
    brain_afferent=["visual_cortex", "MT_V5"],
    params={"pupil_mm": 3.5, "accommodation": 0.5, "lacrimation": 0.1, "blink_rate": 15.0}))

_o(Organ("Eye Right", "eye_R", "sensory", "head", 7.5,
    0.57, 0.095, "circle", "1a2040", "44aaff",
    0.45, 0.6, -0.5,
    brain_efferent=["visual_cortex", "FPC"],
    brain_afferent=["visual_cortex", "MT_V5"],
    params={"pupil_mm": 3.5, "accommodation": 0.5, "lacrimation": 0.1, "blink_rate": 15.0}))

_o(Organ("Ear Left", "ear_L", "sensory", "head", 2.0,
    0.37, 0.105, "circle", "1a1a38", "aa88ff",
    0.45, 0.0, 0.0,
    brain_efferent=["auditory_cortex"],
    brain_afferent=["auditory_cortex", "STG"],
    params={"sensitivity_db": 0.5, "threshold_shift": 0.0, "tinnitus": 0.0}))

_o(Organ("Ear Right", "ear_R", "sensory", "head", 2.0,
    0.63, 0.105, "circle", "1a1a38", "aa88ff",
    0.45, 0.0, 0.0,
    brain_efferent=["auditory_cortex"],
    brain_afferent=["auditory_cortex", "STG"],
    params={"sensitivity_db": 0.5, "threshold_shift": 0.0}))

_o(Organ("Nose / Olfactory", "nose", "sensory", "head", 2.0,
    0.50, 0.115, "circle", "1a1a30", "ffaa44",
    0.40, -0.2, 0.3,
    brain_efferent=["OFC"],
    brain_afferent=["OFC", "amygdala", "hippocampus"],
    params={"sensitivity": 0.5, "mucosal_flow": 0.5, "congestion": 0.1}))

_o(Organ("Tongue / Taste", "tongue", "sensory", "head", 70.0,
    0.50, 0.135, "ellipse", "551122", "ff6688",
    0.45, -0.2, 0.4,
    brain_efferent=["OFC"],
    brain_afferent=["OFC", "aI"],
    params={"sensitivity": 0.5, "salivation": 0.4, "taste_threshold": 0.5}))

_o(Organ("Salivary Glands", "salivary", "digestive", "head", 50.0,
    0.50, 0.145, "circle", "221122", "ffaacc",
    0.35, -0.8, 0.9,  # PNS strongly activates (dry mouth from SNS)
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"secretion_rate": 0.35, "amylase": 0.4}))

_o(Organ("Pituitary Gland", "pituitary", "endocrine", "head", 0.5,
    0.50, 0.11, "circle", "220033", "cc44ff",
    0.40, 0.1, 0.0,
    brain_efferent=["hypothalamus"],
    brain_afferent=["hypothalamus", "vmPFC"],
    params={"ACTH": 0.3, "GH": 0.3, "TSH": 0.4, "LH": 0.3, "FSH": 0.3, "prolactin": 0.2}))

_o(Organ("Pineal Gland", "pineal", "endocrine", "head", 0.17,
    0.50, 0.09, "circle", "110022", "9944ff",
    0.30, 0.0, 0.0,
    brain_efferent=["hypothalamus"],
    brain_afferent=[],
    params={"melatonin": 0.3, "circadian_phase": 0.5}))


# ── NECK ──────────────────────────────────────────────────────────────────────

_o(Organ("Thyroid Gland", "thyroid", "endocrine", "neck", 25.0,
    0.50, 0.185, "ellipse", "112233", "44ccdd",
    0.45, 0.2, 0.0,
    brain_efferent=["pituitary", "hypothalamus"],
    brain_afferent=["hypothalamus"],
    params={"T3": 0.45, "T4": 0.45, "TSH_sensitivity": 0.5, "metabolic_rate": 0.5}))

_o(Organ("Parathyroid Glands", "parathyroid", "endocrine", "neck", 0.14,
    0.53, 0.19, "circle", "112222", "22ccbb",
    0.40, 0.0, 0.0,
    brain_efferent=[],
    brain_afferent=[],
    params={"PTH": 0.4, "calcium_regulation": 0.5}))

_o(Organ("Larynx / Vocal Cords", "larynx", "respiratory", "neck", 30.0,
    0.50, 0.195, "circle", "221100", "ff8844",
    0.35, 0.3, -0.3,
    brain_efferent=["M1", "SMA", "brainstem"],
    brain_afferent=["STG", "M1"],
    params={"tension": 0.5, "airway_diameter": 0.7, "vocalization": 0.0}))

_o(Organ("Trachea", "trachea", "respiratory", "neck", 20.0,
    0.50, 0.215, "line", "112233", "33aacc",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"diameter": 0.75, "mucociliary_clearance": 0.5}))


# ── THORAX ────────────────────────────────────────────────────────────────────

_o(Organ("Heart", "heart", "cardiovascular", "thorax", 300.0,
    0.46, 0.335, "heart", "440011", "ff3355",
    0.50, 0.7, -0.7,
    brain_efferent=["brainstem", "hypothalamus"],
    brain_afferent=["aI", "thalamus", "brainstem"],
    params={"heart_rate": 70.0, "stroke_volume": 70.0, "cardiac_output": 4.9,
            "contractility": 0.65, "ejection_fraction": 0.60,
            "beat_phase": 0.0, "coronary_flow": 0.60}))

_o(Organ("Lung Left", "lung_L", "respiratory", "thorax", 600.0,
    0.38, 0.335, "lung", "111a33", "4499ff",
    0.50, 0.3, 0.2,
    brain_efferent=["brainstem"],
    brain_afferent=["aI", "brainstem"],
    params={"volume_fraction": 0.5, "bronchial_dilation": 0.65,
            "SpO2": 0.98, "breath_phase": 0.0}))

_o(Organ("Lung Right", "lung_R", "respiratory", "thorax", 700.0,
    0.62, 0.335, "lung", "111a33", "4499ff",
    0.50, 0.3, 0.2,
    brain_efferent=["brainstem"],
    brain_afferent=["aI", "brainstem"],
    params={"volume_fraction": 0.5, "bronchial_dilation": 0.65,
            "SpO2": 0.98, "pCO2": 0.40}))

_o(Organ("Diaphragm", "diaphragm", "respiratory", "thorax", 250.0,
    0.50, 0.395, "ellipse", "221122", "cc66aa",
    0.50, 0.2, 0.1,
    brain_efferent=["brainstem", "M1"],
    brain_afferent=["brainstem"],
    params={"tension": 0.5, "excursion": 0.5}))

_o(Organ("Thymus", "thymus", "immune", "thorax", 30.0,
    0.50, 0.285, "ellipse", "112200", "66cc44",
    0.35, -0.3, 0.1,
    brain_efferent=["hypothalamus"],
    brain_afferent=[],
    params={"T_cell_output": 0.4, "involution": 0.3}))

_o(Organ("Aorta", "aorta", "cardiovascular", "thorax", 120.0,
    0.50, 0.36, "line", "330011", "cc2244",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem"],
    params={"systolic_bp": 120.0, "diastolic_bp": 80.0, "wall_compliance": 0.65}))

_o(Organ("Pulmonary Vessels", "pulm_vessels", "cardiovascular", "thorax", 80.0,
    0.50, 0.32, "line", "111a44", "3366cc",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"pulm_bp": 0.22, "flow": 0.65}))

_o(Organ("Esophagus", "esophagus", "digestive", "thorax", 40.0,
    0.51, 0.31, "line", "221100", "aa5533",
    0.40, -0.3, 0.5,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem"],
    params={"peristalsis": 0.4, "LES_tone": 0.7}))

_o(Organ("Thoracic Spinal Cord", "sc_thoracic", "nervous", "thorax", 30.0,
    0.50, 0.37, "line", "112233", "3366aa",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem", "M1"],
    brain_afferent=["brainstem", "S1"],
    params={"conduction_velocity": 0.7}))


# ── ABDOMEN ───────────────────────────────────────────────────────────────────

_o(Organ("Liver", "liver", "digestive", "abdomen", 1500.0,
    0.58, 0.435, "ellipse", "330800", "cc4400",
    0.55, -0.2, 0.4,
    brain_efferent=["hypothalamus", "brainstem"],
    brain_afferent=["hypothalamus"],
    params={"glycogen_store": 0.65, "gluconeogenesis": 0.3, "bile_production": 0.4,
            "detoxification": 0.5, "protein_synthesis": 0.6}))

_o(Organ("Stomach", "stomach", "digestive", "abdomen", 200.0,
    0.44, 0.430, "ellipse", "221100", "cc6622",
    0.45, -0.6, 0.8,
    brain_efferent=["brainstem", "hypothalamus"],
    brain_afferent=["aI", "brainstem"],
    params={"motility": 0.5, "acid_secretion": 0.45, "hunger": 0.3, "fullness": 0.3}))

_o(Organ("Pancreas", "pancreas", "endocrine", "abdomen", 100.0,
    0.51, 0.455, "ellipse", "221133", "8844cc",
    0.45, -0.3, 0.5,
    brain_efferent=["hypothalamus", "brainstem"],
    brain_afferent=["hypothalamus"],
    params={"insulin": 0.45, "glucagon": 0.35, "blood_glucose": 0.50,
            "digestive_enzymes": 0.45}))

_o(Organ("Spleen", "spleen", "immune", "abdomen", 180.0,
    0.37, 0.440, "ellipse", "220022", "aa22aa",
    0.40, 0.4, -0.3,  # SNS contracts (mobilizes blood), PNS mild
    brain_efferent=["hypothalamus"],
    brain_afferent=[],
    params={"nk_cell_activity": 0.5, "blood_reservoir": 0.6, "immune_activation": 0.3}))

_o(Organ("Gallbladder", "gallbladder", "digestive", "abdomen", 60.0,
    0.61, 0.455, "ellipse", "223300", "88cc00",
    0.40, -0.4, 0.7,
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"bile_concentration": 0.5, "contraction": 0.3}))

_o(Organ("Small Intestine", "small_intestine", "digestive", "abdomen", 1000.0,
    0.50, 0.515, "loop", "221100", "cc7733",
    0.55, -0.5, 0.8,
    brain_efferent=["brainstem", "raphe"],
    brain_afferent=["aI", "brainstem"],
    params={"motility": 0.55, "absorption": 0.55, "ens_serotonin": 0.55,
            "permeability": 0.3, "microbiome_health": 0.65}))

_o(Organ("Large Intestine", "large_intestine", "digestive", "abdomen", 500.0,
    0.50, 0.550, "loop", "221100", "aa6622",
    0.45, -0.4, 0.7,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem"],
    params={"motility": 0.45, "water_absorption": 0.5, "transit_time": 0.5}))

_o(Organ("Appendix", "appendix", "immune", "abdomen", 8.0,
    0.60, 0.545, "circle", "221100", "cc4422",
    0.25, 0.0, 0.0,
    brain_efferent=[],
    brain_afferent=[],
    params={"lymphoid_activity": 0.25}))

_o(Organ("Kidney Left", "kidney_L", "urinary", "abdomen", 150.0,
    0.39, 0.490, "ellipse", "220011", "cc2266",
    0.55, 0.2, -0.3,
    brain_efferent=["hypothalamus", "brainstem"],
    brain_afferent=["hypothalamus"],
    params={"GFR": 0.60, "renin": 0.35, "erythropoietin": 0.30, "urine_output": 0.5}))

_o(Organ("Kidney Right", "kidney_R", "urinary", "abdomen", 150.0,
    0.61, 0.490, "ellipse", "220011", "cc2266",
    0.55, 0.2, -0.3,
    brain_efferent=["hypothalamus", "brainstem"],
    brain_afferent=["hypothalamus"],
    params={"GFR": 0.60, "renin": 0.35, "urine_output": 0.5}))

_o(Organ("Adrenal Gland Left", "adrenal_L", "endocrine", "abdomen", 5.0,
    0.40, 0.470, "circle", "332200", "ffaa00",
    0.35, 0.9, 0.0,  # almost entirely SNS driven
    brain_efferent=["hypothalamus", "pituitary"],
    brain_afferent=["hypothalamus", "amygdala"],
    params={"adrenaline": 0.20, "noradrenaline_peripheral": 0.25,
            "cortisol_blood": 0.30, "aldosterone": 0.30, "DHEA": 0.35}))

_o(Organ("Adrenal Gland Right", "adrenal_R", "endocrine", "abdomen", 5.0,
    0.60, 0.470, "circle", "332200", "ffaa00",
    0.35, 0.9, 0.0,
    brain_efferent=["hypothalamus", "pituitary"],
    brain_afferent=["hypothalamus"],
    params={"adrenaline": 0.20, "cortisol_blood": 0.30, "aldosterone": 0.30}))

_o(Organ("Abdominal Aorta", "aorta_abd", "cardiovascular", "abdomen", 40.0,
    0.50, 0.500, "line", "330011", "cc2244",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"blood_pressure": 0.5, "flow_velocity": 0.5}))

_o(Organ("Portal Vein", "portal_vein", "cardiovascular", "abdomen", 20.0,
    0.52, 0.480, "line", "220022", "882288",
    0.50, 0.0, 0.0,
    brain_efferent=[],
    brain_afferent=[],
    params={"portal_pressure": 0.3, "flow": 0.5}))

_o(Organ("Lymph Nodes (Abdominal)", "lymph_abd", "immune", "abdomen", 30.0,
    0.50, 0.52, "circle", "112200", "44bb22",
    0.35, 0.0, 0.0,
    brain_efferent=["hypothalamus"],
    brain_afferent=[],
    params={"immune_activity": 0.3, "cytokine_output": 0.25}))

_o(Organ("Lumbar Spinal Cord", "sc_lumbar", "nervous", "abdomen", 15.0,
    0.50, 0.52, "line", "112233", "3366aa",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem", "M1"],
    brain_afferent=["S1", "brainstem"],
    params={"conduction_velocity": 0.65}))


# ── PELVIS ────────────────────────────────────────────────────────────────────

_o(Organ("Bladder", "bladder", "urinary", "pelvis", 50.0,
    0.50, 0.610, "ellipse", "221133", "6644cc",
    0.40, -0.4, 0.6,  # SNS relaxes detrusor, PNS contracts
    brain_efferent=["brainstem", "hypothalamus"],
    brain_afferent=["aI", "brainstem"],
    params={"fullness": 0.3, "detrusor_tone": 0.4, "urethral_sphincter": 0.7, "urgency": 0.1}))

_o(Organ("Rectum", "rectum", "digestive", "pelvis", 80.0,
    0.50, 0.640, "ellipse", "221100", "884422",
    0.40, -0.4, 0.6,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem"],
    params={"fullness": 0.2, "sphincter_tone": 0.7}))

# Reproductive — modeled as shared/neutral (engine can parameterize per context)
_o(Organ("Gonads / Reproductive", "gonads", "reproductive", "pelvis", 50.0,
    0.50, 0.660, "ellipse", "330022", "ff44aa",
    0.35, 0.4, 0.3,
    brain_efferent=["hypothalamus", "pituitary", "amygdala"],
    brain_afferent=["hypothalamus", "amygdala", "aI"],
    params={"testosterone": 0.40, "estrogen": 0.35, "progesterone": 0.25,
            "LH": 0.30, "FSH": 0.30, "arousal": 0.10,
            "genital_engorgement": 0.05}))

_o(Organ("Uterus / Prostate", "uterus_prostate", "reproductive", "pelvis", 60.0,
    0.50, 0.645, "ellipse", "330022", "dd3388",
    0.30, 0.3, 0.2,
    brain_efferent=["hypothalamus", "brainstem"],
    brain_afferent=["aI"],
    params={"muscle_tone": 0.35, "secretion": 0.20, "sensitivity": 0.35}))

_o(Organ("Pelvic Floor Muscles", "pelvic_floor", "musculoskeletal", "pelvis", 80.0,
    0.50, 0.655, "ellipse", "222200", "aaaa22",
    0.45, 0.5, -0.3,
    brain_efferent=["M1", "brainstem"],
    brain_afferent=["S1"],
    params={"tension": 0.45, "coordination": 0.5}))

_o(Organ("Sacral Spinal Cord", "sc_sacral", "nervous", "pelvis", 8.0,
    0.50, 0.63, "line", "112233", "3366aa",
    0.50, 0.0, 0.0,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem"],
    params={"conduction_velocity": 0.60}))


# ── LIMBS ─────────────────────────────────────────────────────────────────────

_o(Organ("Arm Left", "arm_L", "musculoskeletal", "limbs", 4000.0,
    0.22, 0.45, "limb", "1a1a2a", "5566cc",
    0.35, 0.3, -0.2,
    brain_efferent=["M1", "SMA", "premotor", "cerebellum"],
    brain_afferent=["S1", "S2"],
    params={"tension": 0.30, "grip_strength": 0.35, "temperature": 0.50, "tremor": 0.0}))

_o(Organ("Arm Right", "arm_R", "musculoskeletal", "limbs", 4000.0,
    0.78, 0.45, "limb", "1a1a2a", "5566cc",
    0.35, 0.3, -0.2,
    brain_efferent=["M1", "SMA", "cerebellum"],
    brain_afferent=["S1", "S2"],
    params={"tension": 0.30, "grip_strength": 0.35, "temperature": 0.50, "tremor": 0.0}))

_o(Organ("Hand Left", "hand_L", "sensory", "limbs", 400.0,
    0.18, 0.62, "circle", "1a1a2a", "8899dd",
    0.35, 0.2, 0.1,
    brain_efferent=["M1", "S1"],
    brain_afferent=["S1", "S2"],
    params={"temperature": 0.48, "sweating": 0.10, "sensitivity": 0.55}))

_o(Organ("Hand Right", "hand_R", "sensory", "limbs", 400.0,
    0.82, 0.62, "circle", "1a1a2a", "8899dd",
    0.35, 0.2, 0.1,
    brain_efferent=["M1", "S1"],
    brain_afferent=["S1", "S2"],
    params={"temperature": 0.48, "sweating": 0.10, "sensitivity": 0.55}))

_o(Organ("Leg Left", "leg_L", "musculoskeletal", "limbs", 10000.0,
    0.38, 0.78, "limb", "1a1a2a", "5566cc",
    0.35, 0.3, -0.2,
    brain_efferent=["M1", "SMA", "cerebellum"],
    brain_afferent=["S1", "S2"],
    params={"tension": 0.30, "blood_flow": 0.50, "temperature": 0.50, "tremor": 0.0}))

_o(Organ("Leg Right", "leg_R", "musculoskeletal", "limbs", 10000.0,
    0.62, 0.78, "limb", "1a1a2a", "5566cc",
    0.35, 0.3, -0.2,
    brain_efferent=["M1", "SMA", "cerebellum"],
    brain_afferent=["S1", "S2"],
    params={"tension": 0.30, "blood_flow": 0.50, "temperature": 0.50, "tremor": 0.0}))

_o(Organ("Foot Left", "foot_L", "sensory", "limbs", 500.0,
    0.36, 0.96, "circle", "1a1a2a", "7788bb",
    0.30, 0.1, 0.0,
    brain_efferent=["M1"],
    brain_afferent=["S1"],
    params={"temperature": 0.44, "sweating": 0.08, "sensitivity": 0.45}))

_o(Organ("Foot Right", "foot_R", "sensory", "limbs", 500.0,
    0.64, 0.96, "circle", "1a1a2a", "7788bb",
    0.30, 0.1, 0.0,
    brain_efferent=["M1"],
    brain_afferent=["S1"],
    params={"temperature": 0.44, "sweating": 0.08, "sensitivity": 0.45}))


# ── INTEGUMENTARY (SKIN) ─────────────────────────────────────────────────────

_o(Organ("Skin (Torso)", "skin_torso", "integumentary", "thorax", 3000.0,
    0.50, 0.40, "skin", "1a1510", "ffccaa",
    0.50, 0.6, 0.0,
    brain_efferent=["hypothalamus"],
    brain_afferent=["aI", "S1"],
    params={"conductance_us": 5.0, "temperature_c": 33.5, "flushing": 0.0,
            "pallor": 0.0, "piloerection": 0.0, "sweating": 0.0, "pain_level": 0.0}))

_o(Organ("Skin (Face)", "skin_face", "integumentary", "head", 200.0,
    0.50, 0.085, "skin", "1a1510", "ffddbb",
    0.50, 0.5, 0.1,
    brain_efferent=["hypothalamus", "vmPFC"],
    brain_afferent=["aI", "S1"],
    params={"conductance_us": 4.5, "temperature_c": 34.0, "flushing": 0.0,
            "pallor": 0.0, "blushing": 0.0}))


# ── MUSCULOSKELETAL (KEY STRUCTURES) ──────────────────────────────────────────

_o(Organ("Trapezius / Shoulder", "trapezius", "musculoskeletal", "thorax", 400.0,
    0.50, 0.245, "ellipse", "1a1a22", "6677cc",
    0.35, 0.7, -0.4,
    brain_efferent=["M1", "PAG"],
    brain_afferent=["S1", "S2"],
    params={"tension": 0.35, "pain": 0.0}))

_o(Organ("Jaw / Masseter", "jaw", "musculoskeletal", "head", 80.0,
    0.50, 0.145, "ellipse", "1a1a22", "8877cc",
    0.35, 0.7, -0.4,
    brain_efferent=["M1", "amygdala", "PAG"],
    brain_afferent=["S1"],
    params={"tension": 0.30, "clenching": 0.0, "bruxism": 0.0}))

_o(Organ("Core / Abdominal Muscles", "core_muscles", "musculoskeletal", "abdomen", 800.0,
    0.50, 0.47, "ellipse", "1a1a22", "5566bb",
    0.35, 0.5, -0.3,
    brain_efferent=["M1", "SMA"],
    brain_afferent=["S1"],
    params={"tension": 0.30, "bracing": 0.0}))

_o(Organ("Cardiac Muscle", "cardiac_muscle", "cardiovascular", "thorax", 300.0,
    0.46, 0.335, "heart", "440011", "ff3355",
    0.60, 0.6, -0.5,
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"tension": 0.60, "ischemia": 0.0}))

_o(Organ("Spinal Column", "spine", "musculoskeletal", "thorax", 1000.0,
    0.50, 0.50, "line", "222233", "4455aa",
    0.50, 0.2, -0.1,
    brain_efferent=["brainstem", "M1"],
    brain_afferent=["S1"],
    params={"posture": 0.5, "tension": 0.35, "disc_pressure": 0.45}))


# ── VASCULAR (KEY VESSELS) ───────────────────────────────────────────────────

_o(Organ("Carotid Arteries", "carotid", "cardiovascular", "neck", 10.0,
    0.50, 0.175, "line", "330011", "cc2244",
    0.55, 0.3, -0.2,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem"],
    params={"flow_velocity": 0.55, "baroreceptor_firing": 0.45}))

_o(Organ("Femoral Vessels", "femoral", "cardiovascular", "limbs", 15.0,
    0.50, 0.72, "line", "330011", "cc2244",
    0.50, 0.4, -0.3,
    brain_efferent=["brainstem"],
    brain_afferent=[],
    params={"blood_flow": 0.50, "vasoconstriction": 0.35}))

_o(Organ("Peripheral Vasculature", "periph_vessels", "cardiovascular", "limbs", 200.0,
    0.50, 0.55, "custom", "221100", "cc3322",
    0.50, 0.5, -0.4,
    brain_efferent=["brainstem", "hypothalamus"],
    brain_afferent=["brainstem"],
    params={"resistance": 0.50, "vasoconstriction": 0.40, "skin_blood_flow": 0.45}))


# ── IMMUNE / LYMPHATIC ───────────────────────────────────────────────────────

_o(Organ("Bone Marrow", "bone_marrow", "immune", "limbs", 1500.0,
    0.50, 0.75, "custom", "221133", "8833cc",
    0.45, 0.0, 0.0,
    brain_efferent=["hypothalamus"],
    brain_afferent=[],
    params={"hematopoiesis": 0.5, "stem_cell_activity": 0.45}))

_o(Organ("Lymphatic System", "lymphatics", "immune", "thorax", 200.0,
    0.50, 0.45, "custom", "112200", "44bb22",
    0.40, 0.0, 0.0,
    brain_efferent=["hypothalamus"],
    brain_afferent=[],
    params={"cytokine_IL6": 0.20, "cytokine_IL10": 0.35, "nk_cells": 0.45,
            "t_cells": 0.45, "b_cells": 0.40, "inflammation": 0.15}))

_o(Organ("Vagus Nerve", "vagus", "nervous", "neck", 5.0,
    0.50, 0.22, "line", "223344", "44aacc",
    0.55, 0.0, 0.0,
    brain_efferent=["brainstem"],
    brain_afferent=["brainstem", "aI"],
    params={"tone": 0.55, "HRV": 0.55, "efferent_firing": 0.45, "afferent_firing": 0.55},
    notes="Cranial nerve X — primary PNS highway; 80% afferent (body→brain)"))

_o(Organ("Sympathetic Chain", "symp_chain", "nervous", "thorax", 8.0,
    0.54, 0.38, "line", "332200", "cc8800",
    0.35, 0.0, 0.0,
    brain_efferent=["hypothalamus", "brainstem"],
    brain_afferent=[],
    params={"firing_rate": 0.35, "noradrenaline_release": 0.30}))

_o(Organ("Enteric Nervous System", "ENS", "nervous", "abdomen", 100.0,
    0.50, 0.52, "loop", "221133", "8844bb",
    0.55, 0.0, 0.0,
    brain_efferent=["brainstem", "raphe"],
    brain_afferent=["brainstem", "aI"],
    params={"serotonin_ens": 0.55, "motility_drive": 0.50, "neuropeptides": 0.45},
    notes="Second brain — 100M neurons, 90% of body serotonin"))


# ── ENDOCRINE SUMMARY ────────────────────────────────────────────────────────

_o(Organ("Hypothalamus", "hypothalamus_body", "endocrine", "head", 4.0,
    0.50, 0.115, "circle", "220033", "aa44ff",
    0.55, 0.0, 0.0,  # ANS master controller
    brain_efferent=["brainstem", "pituitary"],
    brain_afferent=["amygdala", "vmPFC", "hippocampus"],
    params={"CRH": 0.25, "TRH": 0.35, "GnRH": 0.30, "GHRH": 0.30,
            "ADH_vasopressin": 0.35, "oxytocin_peripheral": 0.25},
    notes="Master neuroendocrine controller — in brain module but also drives body"))


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_organs_by_system(system: str) -> List[Organ]:
    return [o for o in ORGANS.values() if o.system == system]

def get_organs_by_region(region: str) -> List[Organ]:
    return [o for o in ORGANS.values() if o.body_region == region]

ORGAN_SYSTEMS = list({o.system for o in ORGANS.values()})
TOTAL_ORGANS = len(ORGANS)
