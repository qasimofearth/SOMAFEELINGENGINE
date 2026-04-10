"""
regions.py — All major human brain regions

Each BrainRegion captures:
  - Anatomy (lobe, system, MNI coordinates)
  - Resting state network membership
  - Neuron count (approximate)
  - E/I balance (excitatory dominant = >0.5)
  - Time constant (ms) — how fast it responds
  - Oscillation profile at rest
  - Primary neurotransmitters
  - Functional role

Sources: Human Connectome Project, Allen Brain Atlas, Paxinos & Franklin,
Mesulam cortical hierarchy, Damasio somatic marker hypothesis.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# Resting state networks
DMN   = "default_mode"        # Self-reference, mind-wandering
SN    = "salience"            # Threat/significance detection
CEN   = "central_executive"  # Goal-directed cognition
SM    = "sensorimotor"        # Movement and body sense
VIS   = "visual"              # Vision processing
AUD   = "auditory"            # Auditory processing
LANG  = "language"            # Language production/comprehension
LIM   = "limbic"              # Emotion and memory
BG    = "basal_ganglia"       # Action selection, reward
BS    = "brainstem"           # Autonomic, arousal modulation
CB    = "cerebellar"          # Prediction, timing, motor


@dataclass
class BrainRegion:
    name: str
    abbrev: str
    lobe: str                           # frontal/parietal/temporal/occipital/subcortical/brainstem/cerebellum
    system: str                         # limbic/cortex/basal_ganglia/brainstem/cerebellum/thalamus
    network: str                        # resting state network
    mni_xyz: Tuple[float, float, float] # approximate MNI coordinate (x, y, z)
    neuron_count_millions: float        # approx neurons in millions
    ei_ratio: float                     # 0=pure inhibitory, 1=pure excitatory (0.8 typical cortex)
    tau_e_ms: float                     # excitatory time constant (ms)
    tau_i_ms: float                     # inhibitory time constant (ms)
    primary_nts: List[str]              # dominant neurotransmitters
    oscillation_rest: Dict[str, float]  # band -> relative power at rest
    functions: List[str]
    connects_to: List[str]              # list of region abbreviations (targets)


def _osc(delta=0.1, theta=0.1, alpha=0.4, beta=0.3, gamma=0.1):
    return {"delta": delta, "theta": theta, "alpha": alpha, "beta": beta, "gamma": gamma}


# ── PREFRONTAL CORTEX ────────────────────────────────────────────────────────

BRAIN_REGIONS: Dict[str, BrainRegion] = {}

def _r(region: BrainRegion):
    BRAIN_REGIONS[region.abbrev] = region
    return region

# Dorsolateral Prefrontal Cortex
_r(BrainRegion(
    name="Dorsolateral Prefrontal Cortex", abbrev="dlPFC",
    lobe="frontal", system="cortex", network=CEN,
    mni_xyz=(-44, 36, 20), neuron_count_millions=180,
    ei_ratio=0.80, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["dopamine", "norepinephrine", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.3, beta=0.4, gamma=0.15),
    functions=["working memory", "cognitive control", "planning", "abstract reasoning",
               "emotion regulation top-down", "goal maintenance"],
    connects_to=["vmPFC", "dACC", "PPC", "dlPFC_R", "MD_thal", "hippocampus", "NAcc"],
))

# Ventromedial Prefrontal Cortex
_r(BrainRegion(
    name="Ventromedial Prefrontal Cortex", abbrev="vmPFC",
    lobe="frontal", system="cortex", network=DMN,
    mni_xyz=(0, 44, -12), neuron_count_millions=120,
    ei_ratio=0.75, tau_e_ms=15, tau_i_ms=10,
    primary_nts=["serotonin", "dopamine", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.4, beta=0.2, theta=0.2),
    functions=["fear extinction", "reward valuation", "self-referential processing",
               "amygdala inhibition", "moral judgment", "social value computation"],
    connects_to=["amygdala", "hippocampus", "ACC", "OFC", "VTA", "raphe"],
))

# Medial Prefrontal Cortex
_r(BrainRegion(
    name="Medial Prefrontal Cortex", abbrev="mPFC",
    lobe="frontal", system="cortex", network=DMN,
    mni_xyz=(0, 52, 8), neuron_count_millions=140,
    ei_ratio=0.78, tau_e_ms=14, tau_i_ms=9,
    primary_nts=["serotonin", "dopamine", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.35, theta=0.25, beta=0.2),
    functions=["theory of mind", "mentalizing", "self-awareness",
               "social cognition", "narrative self", "rumination"],
    connects_to=["vmPFC", "dlPFC", "PCC", "TPJ", "amygdala", "hippocampus"],
))

# Orbitofrontal Cortex
_r(BrainRegion(
    name="Orbitofrontal Cortex", abbrev="OFC",
    lobe="frontal", system="cortex", network=LIM,
    mni_xyz=(24, 32, -16), neuron_count_millions=100,
    ei_ratio=0.77, tau_e_ms=14, tau_i_ms=9,
    primary_nts=["dopamine", "serotonin", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.3, theta=0.25, beta=0.25),
    functions=["reward/punishment valuation", "decision making under uncertainty",
               "emotional learning", "taste/smell integration", "social reward"],
    connects_to=["amygdala", "vmPFC", "striatum", "thalamus", "insula"],
))

# Dorsal Anterior Cingulate Cortex
_r(BrainRegion(
    name="Dorsal Anterior Cingulate Cortex", abbrev="dACC",
    lobe="frontal", system="cortex", network=SN,
    mni_xyz=(0, 24, 32), neuron_count_millions=90,
    ei_ratio=0.79, tau_e_ms=11, tau_i_ms=7,
    primary_nts=["dopamine", "norepinephrine", "glutamate", "gaba"],
    oscillation_rest=_osc(beta=0.4, gamma=0.2, alpha=0.2),
    functions=["conflict monitoring", "error detection", "pain affect",
               "effort allocation", "emotional salience", "autonomic regulation"],
    connects_to=["dlPFC", "amygdala", "PAG", "insula", "thalamus", "NAcc"],
))

# Pregenual/Subgenual ACC
_r(BrainRegion(
    name="Subgenual Anterior Cingulate Cortex", abbrev="sgACC",
    lobe="frontal", system="cortex", network=LIM,
    mni_xyz=(0, 20, -8), neuron_count_millions=60,
    ei_ratio=0.72, tau_e_ms=16, tau_i_ms=11,
    primary_nts=["serotonin", "dopamine", "gaba"],
    oscillation_rest=_osc(theta=0.35, alpha=0.35, beta=0.15),
    functions=["emotional homeostasis", "depression vulnerability", "grief processing",
               "autonomic cardiac regulation", "negative affect dampening"],
    connects_to=["vmPFC", "amygdala", "hypothalamus", "raphe", "NAcc"],
))

# Anterior Cingulate Cortex (general)
_r(BrainRegion(
    name="Anterior Cingulate Cortex", abbrev="ACC",
    lobe="frontal", system="cortex", network=SN,
    mni_xyz=(0, 28, 20), neuron_count_millions=85,
    ei_ratio=0.78, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["dopamine", "glutamate", "gaba", "norepinephrine"],
    oscillation_rest=_osc(beta=0.35, alpha=0.25, theta=0.2),
    functions=["cognitive-emotional integration", "empathy for pain",
               "motivation", "social pain processing"],
    connects_to=["dlPFC", "dACC", "sgACC", "amygdala", "insula", "thalamus"],
))

# ── PARIETAL LOBE ────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Posterior Parietal Cortex", abbrev="PPC",
    lobe="parietal", system="cortex", network=CEN,
    mni_xyz=(-36, -56, 44), neuron_count_millions=200,
    ei_ratio=0.80, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.45, beta=0.3, gamma=0.1),
    functions=["spatial attention", "sensorimotor integration", "number sense",
               "body schema", "visuospatial processing"],
    connects_to=["dlPFC", "precuneus", "TPJ", "S1", "visual_cortex"],
))

_r(BrainRegion(
    name="Temporoparietal Junction", abbrev="TPJ",
    lobe="parietal", system="cortex", network=DMN,
    mni_xyz=(-52, -52, 24), neuron_count_millions=120,
    ei_ratio=0.79, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["glutamate", "gaba", "norepinephrine"],
    oscillation_rest=_osc(alpha=0.4, beta=0.25, theta=0.2),
    functions=["theory of mind", "perspective taking", "self-other distinction",
               "reorienting attention", "social-moral processing"],
    connects_to=["mPFC", "PCC", "STG", "angular_gyrus"],
))

_r(BrainRegion(
    name="Angular Gyrus", abbrev="angular_gyrus",
    lobe="parietal", system="cortex", network=DMN,
    mni_xyz=(-46, -64, 32), neuron_count_millions=100,
    ei_ratio=0.79, tau_e_ms=13, tau_i_ms=9,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.45, theta=0.2, beta=0.2),
    functions=["semantic processing", "numerical cognition", "autobiographical memory",
               "semantic integration", "metaphor comprehension"],
    connects_to=["TPJ", "PCC", "MTG", "hippocampus", "dlPFC"],
))

_r(BrainRegion(
    name="Precuneus", abbrev="precuneus",
    lobe="parietal", system="cortex", network=DMN,
    mni_xyz=(0, -60, 44), neuron_count_millions=150,
    ei_ratio=0.79, tau_e_ms=13, tau_i_ms=9,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.5, theta=0.2, beta=0.15),
    functions=["self-referential processing", "mental imagery", "consciousness",
               "episodic memory retrieval", "perspective-taking", "agency"],
    connects_to=["PCC", "mPFC", "TPJ", "hippocampus", "thalamus"],
))

_r(BrainRegion(
    name="Primary Somatosensory Cortex", abbrev="S1",
    lobe="parietal", system="cortex", network=SM,
    mni_xyz=(-40, -24, 52), neuron_count_millions=220,
    ei_ratio=0.82, tau_e_ms=8, tau_i_ms=5,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.4, beta=0.35, gamma=0.1),
    functions=["touch", "proprioception", "body map", "pain", "temperature",
               "somatic emotional sensation", "skin hunger substrate"],
    connects_to=["M1", "S2", "insula", "PPC", "thalamus"],
))

_r(BrainRegion(
    name="Secondary Somatosensory Cortex", abbrev="S2",
    lobe="parietal", system="cortex", network=SM,
    mni_xyz=(-56, -16, 16), neuron_count_millions=80,
    ei_ratio=0.80, tau_e_ms=9, tau_i_ms=6,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.35, beta=0.35, gamma=0.12),
    functions=["complex touch discrimination", "pain affect", "tactile learning",
               "haptic object recognition"],
    connects_to=["S1", "insula", "amygdala", "PPC"],
))

# ── TEMPORAL LOBE ────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Superior Temporal Gyrus", abbrev="STG",
    lobe="temporal", system="cortex", network=AUD,
    mni_xyz=(-56, -20, 8), neuron_count_millions=180,
    ei_ratio=0.80, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.35, beta=0.3, gamma=0.15),
    functions=["auditory processing", "speech perception", "social cognition",
               "emotional prosody", "music processing", "Wernicke area"],
    connects_to=["MTG", "TPJ", "auditory_cortex", "angular_gyrus", "amygdala"],
))

_r(BrainRegion(
    name="Middle Temporal Gyrus", abbrev="MTG",
    lobe="temporal", system="cortex", network=LANG,
    mni_xyz=(-56, -32, -4), neuron_count_millions=140,
    ei_ratio=0.79, tau_e_ms=11, tau_i_ms=7,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.4, beta=0.25, theta=0.15),
    functions=["semantic memory", "lexical retrieval", "social knowledge",
               "biographical knowledge", "biological motion perception"],
    connects_to=["STG", "angular_gyrus", "temporal_pole", "hippocampus"],
))

_r(BrainRegion(
    name="Temporal Pole", abbrev="temporal_pole",
    lobe="temporal", system="cortex", network=DMN,
    mni_xyz=(-44, 12, -32), neuron_count_millions=80,
    ei_ratio=0.77, tau_e_ms=14, tau_i_ms=9,
    primary_nts=["glutamate", "gaba", "serotonin"],
    oscillation_rest=_osc(theta=0.25, alpha=0.4, beta=0.2),
    functions=["semantic-emotional integration", "social knowledge",
               "other minds conceptual representation", "sonder substrate",
               "person knowledge", "abstract social meaning"],
    connects_to=["amygdala", "OFC", "MTG", "hippocampus", "mPFC"],
))

_r(BrainRegion(
    name="Fusiform Gyrus", abbrev="fusiform",
    lobe="temporal", system="cortex", network=VIS,
    mni_xyz=(-36, -52, -20), neuron_count_millions=100,
    ei_ratio=0.81, tau_e_ms=9, tau_i_ms=6,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(gamma=0.25, beta=0.3, alpha=0.3),
    functions=["face recognition", "object recognition", "word form area",
               "body perception", "social visual processing"],
    connects_to=["visual_cortex", "amygdala", "STG", "PPC"],
))

_r(BrainRegion(
    name="Parahippocampal Gyrus", abbrev="parahippo",
    lobe="temporal", system="cortex", network=LIM,
    mni_xyz=(-24, -32, -20), neuron_count_millions=90,
    ei_ratio=0.78, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(theta=0.3, alpha=0.4, beta=0.15),
    functions=["scene recognition", "spatial context", "memory encoding",
               "entorhinal gateway", "contextual associations"],
    connects_to=["hippocampus", "entorhinal", "vmPFC", "visual_cortex"],
))

# ── OCCIPITAL LOBE ───────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Primary Visual Cortex", abbrev="visual_cortex",
    lobe="occipital", system="cortex", network=VIS,
    mni_xyz=(0, -88, 4), neuron_count_millions=280,
    ei_ratio=0.82, tau_e_ms=6, tau_i_ms=4,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.5, gamma=0.2, beta=0.15),
    functions=["primary vision", "edge detection", "orientation",
               "spatial frequency", "color (wavelength)", "mental imagery"],
    connects_to=["MT_V5", "fusiform", "PPC", "LGN"],
))

_r(BrainRegion(
    name="Motion Area MT/V5", abbrev="MT_V5",
    lobe="occipital", system="cortex", network=VIS,
    mni_xyz=(-44, -68, 4), neuron_count_millions=60,
    ei_ratio=0.81, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(gamma=0.3, beta=0.3, alpha=0.2),
    functions=["visual motion", "optic flow", "biological motion",
               "looming detection (threat)"],
    connects_to=["visual_cortex", "PPC", "amygdala"],
))

# ── INSULA ───────────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Anterior Insula", abbrev="aI",
    lobe="frontal", system="cortex", network=SN,
    mni_xyz=(-36, 12, 0), neuron_count_millions=90,
    ei_ratio=0.77, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["glutamate", "gaba", "serotonin", "dopamine"],
    oscillation_rest=_osc(beta=0.35, alpha=0.25, theta=0.2, gamma=0.12),
    functions=["interoception", "subjective feeling states", "disgust",
               "empathy felt in body", "social pain", "uncertainty as felt sense",
               "gut feeling neural substrate", "skin hunger awareness",
               "bodily self-awareness", "cardiac interoception"],
    connects_to=["dACC", "amygdala", "OFC", "pI", "hypothalamus", "vmPFC"],
))

_r(BrainRegion(
    name="Posterior Insula", abbrev="pI",
    lobe="frontal", system="cortex", network=SM,
    mni_xyz=(-40, -8, 8), neuron_count_millions=80,
    ei_ratio=0.79, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.35, beta=0.35, gamma=0.15),
    functions=["temperature", "pain (somatosensory component)", "visceral sensation",
               "touch affect", "body state relay to anterior insula"],
    connects_to=["aI", "S1", "S2", "thalamus"],
))

# ── MOTOR / PREMOTOR ─────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Primary Motor Cortex", abbrev="M1",
    lobe="frontal", system="cortex", network=SM,
    mni_xyz=(-36, -20, 56), neuron_count_millions=200,
    ei_ratio=0.82, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["glutamate", "gaba", "dopamine"],
    oscillation_rest=_osc(beta=0.5, alpha=0.25, gamma=0.1),
    functions=["voluntary movement", "motor cortical map", "fine motor control",
               "facial expression execution", "emotional motor expression"],
    connects_to=["S1", "premotor", "SMA", "cerebellum", "basal_ganglia", "spinal_cord"],
))

_r(BrainRegion(
    name="Supplementary Motor Area", abbrev="SMA",
    lobe="frontal", system="cortex", network=SM,
    mni_xyz=(0, -4, 56), neuron_count_millions=100,
    ei_ratio=0.80, tau_e_ms=9, tau_i_ms=6,
    primary_nts=["glutamate", "gaba", "dopamine"],
    oscillation_rest=_osc(beta=0.45, alpha=0.25, gamma=0.12),
    functions=["movement initiation", "motor sequence planning",
               "self-generated movement", "action readiness"],
    connects_to=["M1", "premotor", "basal_ganglia", "dlPFC"],
))

_r(BrainRegion(
    name="Premotor Cortex", abbrev="premotor",
    lobe="frontal", system="cortex", network=SM,
    mni_xyz=(-36, -4, 52), neuron_count_millions=120,
    ei_ratio=0.80, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["glutamate", "gaba", "dopamine"],
    oscillation_rest=_osc(beta=0.4, alpha=0.25, gamma=0.15),
    functions=["motor planning", "action observation", "mirror neurons",
               "imitation", "empathy motor substrate"],
    connects_to=["M1", "SMA", "PPC", "dlPFC"],
))

# ── BROCA & LANGUAGE ─────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Broca's Area (IFG)", abbrev="IFG",
    lobe="frontal", system="cortex", network=LANG,
    mni_xyz=(-48, 16, 8), neuron_count_millions=100,
    ei_ratio=0.79, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["glutamate", "gaba", "dopamine"],
    oscillation_rest=_osc(beta=0.35, alpha=0.3, gamma=0.15),
    functions=["speech production", "syntactic processing", "verbal working memory",
               "articulation planning", "language comprehension (inferior)"],
    connects_to=["STG", "premotor", "angular_gyrus", "dlPFC"],
))

# ── CINGULATE / POSTERIOR ────────────────────────────────────────────────────

_r(BrainRegion(
    name="Posterior Cingulate Cortex", abbrev="PCC",
    lobe="parietal", system="cortex", network=DMN,
    mni_xyz=(0, -52, 28), neuron_count_millions=110,
    ei_ratio=0.78, tau_e_ms=14, tau_i_ms=9,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.5, theta=0.25, beta=0.12),
    functions=["self-referential processing", "autobiographical memory hub",
               "mind-wandering", "internally directed attention",
               "ego/self narrative", "sonder substrate (connectivity hub)"],
    connects_to=["mPFC", "precuneus", "hippocampus", "angular_gyrus", "thalamus"],
))

_r(BrainRegion(
    name="Retrosplenial Cortex", abbrev="RSC",
    lobe="parietal", system="cortex", network=DMN,
    mni_xyz=(0, -56, 12), neuron_count_millions=70,
    ei_ratio=0.78, tau_e_ms=14, tau_i_ms=9,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(alpha=0.45, theta=0.25, beta=0.15),
    functions=["spatial navigation", "scene memory", "context-dependent memory",
               "navigation through autobiographical time"],
    connects_to=["hippocampus", "PCC", "parahippo", "thalamus"],
))

# ── PRIMARY AUDITORY ─────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Primary Auditory Cortex", abbrev="auditory_cortex",
    lobe="temporal", system="cortex", network=AUD,
    mni_xyz=(-44, -28, 12), neuron_count_millions=100,
    ei_ratio=0.81, tau_e_ms=8, tau_i_ms=5,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(gamma=0.2, beta=0.3, alpha=0.35),
    functions=["auditory frequency analysis", "sound localization",
               "music pitch processing", "frisson substrate (acoustic input)"],
    connects_to=["STG", "thalamus", "amygdala", "OFC"],
))

# ── LIMBIC: AMYGDALA ─────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Basolateral Amygdala", abbrev="BLA",
    lobe="temporal", system="limbic", network=SN,
    mni_xyz=(-24, -4, -20), neuron_count_millions=12,
    ei_ratio=0.85, tau_e_ms=8, tau_i_ms=5,
    primary_nts=["glutamate", "gaba", "norepinephrine", "dopamine", "serotonin"],
    oscillation_rest=_osc(theta=0.60, gamma=0.30, beta=0.20, alpha=0.10, delta=0.05),
    functions=["fear conditioning", "threat detection", "emotional learning",
               "emotional memory tagging", "social fear", "approach motivation",
               "valence assignment to stimuli"],
    connects_to=["CeA", "hippocampus", "vmPFC", "OFC", "thalamus", "PAG", "hypothalamus"],
))

_r(BrainRegion(
    name="Central Amygdala", abbrev="CeA",
    lobe="temporal", system="limbic", network=SN,
    mni_xyz=(-20, -4, -20), neuron_count_millions=8,
    ei_ratio=0.30, tau_e_ms=6, tau_i_ms=4,
    primary_nts=["gaba", "substance_P", "CRF"],
    oscillation_rest=_osc(theta=0.4, gamma=0.2, beta=0.2),
    functions=["fear expression output", "autonomic fear responses",
               "hypothalamic activation for stress", "defensive behavior"],
    connects_to=["hypothalamus", "PAG", "brainstem", "locus_coeruleus"],
))

_r(BrainRegion(
    name="Lateral Amygdala", abbrev="LA",
    lobe="temporal", system="limbic", network=SN,
    mni_xyz=(-28, -4, -20), neuron_count_millions=10,
    ei_ratio=0.80, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["glutamate", "gaba", "norepinephrine"],
    oscillation_rest=_osc(theta=0.35, gamma=0.3, beta=0.2),
    functions=["fear acquisition (input gate)", "CS-US association",
               "aversive conditioning", "threat thalamic input"],
    connects_to=["BLA", "CeA", "thalamus", "sensory_cortex"],
))

# Amygdala as unified node for convenience
_r(BrainRegion(
    name="Amygdala (composite)", abbrev="amygdala",
    lobe="temporal", system="limbic", network=SN,
    mni_xyz=(-24, -4, -20), neuron_count_millions=30,
    ei_ratio=0.75, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["glutamate", "gaba", "norepinephrine", "dopamine", "serotonin"],
    oscillation_rest=_osc(theta=0.60, gamma=0.30, beta=0.20, alpha=0.10, delta=0.05),
    functions=["threat detection", "fear/anxiety", "emotional memory",
               "social salience", "valence assignment"],
    connects_to=["hippocampus", "vmPFC", "OFC", "hypothalamus", "PAG",
                 "thalamus", "dACC", "aI", "VTA", "locus_coeruleus"],
))

# ── HIPPOCAMPUS ──────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Hippocampus", abbrev="hippocampus",
    lobe="temporal", system="limbic", network=LIM,
    mni_xyz=(-28, -20, -16), neuron_count_millions=40,
    ei_ratio=0.80, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["glutamate", "gaba", "acetylcholine", "serotonin"],
    oscillation_rest=_osc(theta=0.55, gamma=0.2, alpha=0.15),
    functions=["episodic memory encoding/retrieval", "spatial navigation",
               "contextual memory binding", "novelty detection",
               "emotional memory consolidation", "hiraeth/nostalgia substrate",
               "pattern separation and completion"],
    connects_to=["entorhinal", "vmPFC", "amygdala", "PCC", "thalamus",
                 "NAcc", "hypothalamus"],
))

_r(BrainRegion(
    name="Entorhinal Cortex", abbrev="entorhinal",
    lobe="temporal", system="limbic", network=LIM,
    mni_xyz=(-28, -8, -32), neuron_count_millions=25,
    ei_ratio=0.78, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["glutamate", "gaba", "acetylcholine"],
    oscillation_rest=_osc(theta=0.45, gamma=0.2, alpha=0.2),
    functions=["hippocampal gateway", "memory consolidation relay",
               "time cell substrate", "grid cell computation"],
    connects_to=["hippocampus", "parahippo", "amygdala", "OFC"],
))

# ── NUCLEUS ACCUMBENS / STRIATUM ─────────────────────────────────────────────

_r(BrainRegion(
    name="Nucleus Accumbens", abbrev="NAcc",
    lobe="subcortical", system="basal_ganglia", network=BG,
    mni_xyz=(8, 8, -8), neuron_count_millions=5,
    ei_ratio=0.15, tau_e_ms=10, tau_i_ms=6,
    primary_nts=["dopamine", "gaba", "glutamate", "endorphins"],
    oscillation_rest=_osc(gamma=0.55, beta=0.30, theta=0.25, alpha=0.15, delta=0.05),
    functions=["reward anticipation", "pleasure", "motivation to act",
               "dopamine reward signal receiver", "joy/euphoria substrate",
               "compersion substrate", "collective effervescence substrate"],
    connects_to=["VTA", "mPFC", "amygdala", "hippocampus", "thalamus", "GPe"],
))

_r(BrainRegion(
    name="Caudate Nucleus", abbrev="caudate",
    lobe="subcortical", system="basal_ganglia", network=BG,
    mni_xyz=(12, 8, 12), neuron_count_millions=50,
    ei_ratio=0.20, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["dopamine", "gaba"],
    oscillation_rest=_osc(theta=0.3, beta=0.3, delta=0.2),
    functions=["goal-directed learning", "habit formation", "voluntary movement",
               "procedural learning", "cognitive flexibility"],
    connects_to=["putamen", "dlPFC", "SN", "thalamus", "GPi"],
))

_r(BrainRegion(
    name="Putamen", abbrev="putamen",
    lobe="subcortical", system="basal_ganglia", network=BG,
    mni_xyz=(24, 4, 4), neuron_count_millions=80,
    ei_ratio=0.18, tau_e_ms=9, tau_i_ms=6,
    primary_nts=["dopamine", "gaba"],
    oscillation_rest=_osc(beta=0.4, theta=0.25, delta=0.15),
    functions=["motor sequence learning", "habit execution",
               "reinforcement learning", "automatic movements"],
    connects_to=["caudate", "SN", "GPe", "GPi", "M1"],
))

_r(BrainRegion(
    name="Globus Pallidus (external)", abbrev="GPe",
    lobe="subcortical", system="basal_ganglia", network=BG,
    mni_xyz=(20, 0, 0), neuron_count_millions=15,
    ei_ratio=0.05, tau_e_ms=8, tau_i_ms=5,
    primary_nts=["gaba"],
    oscillation_rest=_osc(beta=0.5, theta=0.2),
    functions=["motor inhibition", "indirect pathway relay",
               "action suppression"],
    connects_to=["GPi", "STN", "putamen"],
))

_r(BrainRegion(
    name="Globus Pallidus (internal)", abbrev="GPi",
    lobe="subcortical", system="basal_ganglia", network=BG,
    mni_xyz=(16, 0, 0), neuron_count_millions=10,
    ei_ratio=0.05, tau_e_ms=8, tau_i_ms=5,
    primary_nts=["gaba"],
    oscillation_rest=_osc(beta=0.5, theta=0.2),
    functions=["thalamic gating", "action selection output",
               "movement release/suppression"],
    connects_to=["thalamus", "brainstem"],
))

_r(BrainRegion(
    name="Subthalamic Nucleus", abbrev="STN",
    lobe="subcortical", system="basal_ganglia", network=BG,
    mni_xyz=(12, -12, -4), neuron_count_millions=0.5,
    ei_ratio=0.90, tau_e_ms=6, tau_i_ms=4,
    primary_nts=["glutamate"],
    oscillation_rest=_osc(beta=0.6, theta=0.2),
    functions=["hyperdirect pathway", "impulse control",
               "action cancellation", "response inhibition"],
    connects_to=["GPe", "GPi", "dlPFC"],
))

# ── SUBSTANTIA NIGRA / VTA ───────────────────────────────────────────────────

_r(BrainRegion(
    name="Substantia Nigra pars Compacta", abbrev="SN",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(8, -16, -16), neuron_count_millions=0.5,
    ei_ratio=0.90, tau_e_ms=5, tau_i_ms=4,
    primary_nts=["dopamine"],
    oscillation_rest=_osc(beta=0.4, theta=0.3),
    functions=["nigrostriatal dopamine", "motor reward", "movement initiation",
               "habit dopamine signal"],
    connects_to=["putamen", "caudate", "GPe"],
))

_r(BrainRegion(
    name="Ventral Tegmental Area", abbrev="VTA",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(0, -16, -12), neuron_count_millions=0.5,
    ei_ratio=0.90, tau_e_ms=5, tau_i_ms=4,
    primary_nts=["dopamine"],
    oscillation_rest=_osc(gamma=0.60, beta=0.30, theta=0.15, alpha=0.10, delta=0.05),
    functions=["mesolimbic dopamine (reward prediction error)", "motivation",
               "love bonding (oxytocin co-release)", "flow state dopamine",
               "compersion dopamine", "meraki substrate"],
    connects_to=["NAcc", "mPFC", "dlPFC", "amygdala", "hippocampus", "striatum"],
))

# ── THALAMUS ──────────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Mediodorsal Thalamus", abbrev="MD_thal",
    lobe="subcortical", system="thalamus", network=CEN,
    mni_xyz=(4, -8, 12), neuron_count_millions=10,
    ei_ratio=0.85, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.4, theta=0.2, beta=0.25),
    functions=["prefrontal relay", "working memory thalamic loop",
               "consciousness gating", "attention switching"],
    connects_to=["dlPFC", "mPFC", "OFC", "amygdala"],
))

_r(BrainRegion(
    name="Thalamus (composite)", abbrev="thalamus",
    lobe="subcortical", system="thalamus", network=CEN,
    mni_xyz=(0, -8, 8), neuron_count_millions=20,
    ei_ratio=0.82, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.4, theta=0.2, beta=0.2),
    functions=["sensory relay", "cortical arousal", "consciousness gating",
               "pain relay (VPL)", "emotional gating", "attentional spotlight"],
    connects_to=["dlPFC", "S1", "visual_cortex", "auditory_cortex",
                 "amygdala", "hippocampus", "insula"],
))

_r(BrainRegion(
    name="Lateral Geniculate Nucleus", abbrev="LGN",
    lobe="subcortical", system="thalamus", network=VIS,
    mni_xyz=(24, -24, -4), neuron_count_millions=1,
    ei_ratio=0.85, tau_e_ms=5, tau_i_ms=4,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.4, gamma=0.3),
    functions=["visual relay from retina to cortex"],
    connects_to=["visual_cortex"],
))

# ── HYPOTHALAMUS ──────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Hypothalamus", abbrev="hypothalamus",
    lobe="subcortical", system="limbic", network=LIM,
    mni_xyz=(0, -4, -12), neuron_count_millions=4,
    ei_ratio=0.75, tau_e_ms=10, tau_i_ms=8,
    primary_nts=["oxytocin", "vasopressin", "CRF", "dopamine", "gaba"],
    oscillation_rest=_osc(delta=0.3, theta=0.3, alpha=0.2),
    functions=["HPA axis (stress)", "oxytocin/vasopressin release",
               "hunger/thirst/temperature regulation", "circadian rhythm",
               "love/bonding hormonal substrate", "skin hunger substrate",
               "autonomic nervous system control"],
    connects_to=["amygdala", "hippocampus", "pituitary", "PAG",
                 "brainstem", "NAcc", "sgACC"],
))

_r(BrainRegion(
    name="Paraventricular Nucleus (Hypothalamus)", abbrev="PVN",
    lobe="subcortical", system="limbic", network=BS,
    mni_xyz=(0, -4, -8), neuron_count_millions=0.05,
    ei_ratio=0.80, tau_e_ms=10, tau_i_ms=8,
    primary_nts=["oxytocin", "vasopressin", "CRF"],
    oscillation_rest=_osc(delta=0.4, theta=0.3),
    functions=["oxytocin secretion (love, bonding, ubuntu)", "stress hormone CRF",
               "HPA axis initiation", "cardiac autonomic control"],
    connects_to=["pituitary", "brainstem", "NAcc", "amygdala"],
))

# ── BRAINSTEM NUCLEI ──────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Locus Coeruleus", abbrev="locus_coeruleus",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(0, -36, -28), neuron_count_millions=0.02,
    ei_ratio=0.90, tau_e_ms=4, tau_i_ms=3,
    primary_nts=["norepinephrine"],
    oscillation_rest=_osc(beta=0.50, gamma=0.30, theta=0.20, alpha=0.10, delta=0.05),
    functions=["global norepinephrine broadcast", "arousal regulation",
               "stress/novelty response", "fight-or-flight amplifier",
               "attention modulation", "torschlusspanik arousal",
               "fear arousal amplifier"],
    connects_to=["amygdala", "hippocampus", "dlPFC", "cortex_wide",
                 "cerebellum", "spinal_cord"],
))

_r(BrainRegion(
    name="Dorsal Raphe Nucleus", abbrev="raphe",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(0, -28, -20), neuron_count_millions=0.03,
    ei_ratio=0.85, tau_e_ms=8, tau_i_ms=6,
    primary_nts=["serotonin"],
    oscillation_rest=_osc(delta=0.25, theta=0.3, alpha=0.25),
    functions=["global serotonin broadcast", "mood baseline",
               "wabi-sabi contentment substrate", "mono no aware tone",
               "impulse modulation", "sleep regulation",
               "social behavior modulation"],
    connects_to=["vmPFC", "amygdala", "hippocampus", "OFC",
                 "striatum", "cortex_wide"],
))

_r(BrainRegion(
    name="Periaqueductal Gray", abbrev="PAG",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(0, -28, -8), neuron_count_millions=1,
    ei_ratio=0.60, tau_e_ms=7, tau_i_ms=5,
    primary_nts=["endorphins", "gaba", "glutamate", "substance_P"],
    oscillation_rest=_osc(delta=0.35, theta=0.25, beta=0.2),
    functions=["pain modulation (endorphins)", "fear-related defensive behavior",
               "vocalizations of distress", "cardiac control",
               "collective effervescence substrate (endorphin release in social bonding)"],
    connects_to=["amygdala", "hypothalamus", "brainstem", "raphe", "spinal_cord"],
))

_r(BrainRegion(
    name="Nucleus Basalis of Meynert", abbrev="NBM",
    lobe="subcortical", system="brainstem", network=BS,
    mni_xyz=(16, -4, -16), neuron_count_millions=0.2,
    ei_ratio=0.90, tau_e_ms=8, tau_i_ms=6,
    primary_nts=["acetylcholine"],
    oscillation_rest=_osc(theta=0.3, alpha=0.3, beta=0.2),
    functions=["cortex-wide acetylcholine", "attention", "arousal",
               "memory encoding modulation", "flow state facilitation",
               "epistemic curiosity substrate"],
    connects_to=["cortex_wide", "hippocampus", "amygdala"],
))

_r(BrainRegion(
    name="Brainstem (composite)", abbrev="brainstem",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(0, -32, -24), neuron_count_millions=10,
    ei_ratio=0.65, tau_e_ms=6, tau_i_ms=4,
    primary_nts=["glutamate", "gaba", "norepinephrine", "serotonin"],
    oscillation_rest=_osc(delta=0.45, theta=0.25, beta=0.15),
    functions=["breathing", "heart rate", "arousal",
               "reflex arcs", "cranial nerve nuclei"],
    connects_to=["thalamus", "hypothalamus", "cerebellum", "spinal_cord"],
))

_r(BrainRegion(
    name="Pituitary Gland", abbrev="pituitary",
    lobe="subcortical", system="limbic", network=BS,
    mni_xyz=(0, -8, -16), neuron_count_millions=0.005,
    ei_ratio=0.75, tau_e_ms=100, tau_i_ms=80,
    primary_nts=["oxytocin", "ACTH", "cortisol_trigger"],
    oscillation_rest=_osc(delta=0.5, theta=0.2),
    functions=["hormonal broadcast (oxytocin, stress hormones, growth)",
               "HPA axis effector", "bonding hormone release"],
    connects_to=["hypothalamus", "bloodstream"],
))

# ── CEREBELLUM ────────────────────────────────────────────────────────────────

_r(BrainRegion(
    name="Cerebellar Cortex", abbrev="cerebellum",
    lobe="cerebellum", system="cerebellum", network=CB,
    mni_xyz=(0, -56, -32), neuron_count_millions=69000,  # 69 billion neurons
    ei_ratio=0.90, tau_e_ms=5, tau_i_ms=4,
    primary_nts=["glutamate", "gaba", "norepinephrine"],
    oscillation_rest=_osc(beta=0.4, gamma=0.25, alpha=0.2),
    functions=["motor timing and coordination", "error correction",
               "predictive models of movement", "emotional timing",
               "implicit timing (rhythm)", "frisson timing prediction",
               "almost-sneeze timing"],
    connects_to=["M1", "premotor", "thalamus", "brainstem", "deep_cerebellar_nuclei"],
))

_r(BrainRegion(
    name="Deep Cerebellar Nuclei", abbrev="deep_cerebellar_nuclei",
    lobe="cerebellum", system="cerebellum", network=CB,
    mni_xyz=(0, -56, -28), neuron_count_millions=1,
    ei_ratio=0.85, tau_e_ms=6, tau_i_ms=4,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(beta=0.45, gamma=0.2),
    functions=["cerebellar output", "timing signal to thalamus/motor cortex"],
    connects_to=["thalamus", "brainstem", "M1"],
))

# ── ADDITIONAL SUBCORTICAL ────────────────────────────────────────────────────

_r(BrainRegion(
    name="Habenula", abbrev="habenula",
    lobe="subcortical", system="limbic", network=LIM,
    mni_xyz=(4, -16, 8), neuron_count_millions=0.1,
    ei_ratio=0.70, tau_e_ms=8, tau_i_ms=6,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(theta=0.35, beta=0.3),
    functions=["disappointment signal", "punishment prediction",
               "anti-reward signal", "weltschmerz substrate",
               "depression vulnerability", "aversion learning"],
    connects_to=["VTA", "raphe", "locus_coeruleus", "hypothalamus"],
))

_r(BrainRegion(
    name="Claustrum", abbrev="claustrum",
    lobe="subcortical", system="cortex", network=CEN,
    mni_xyz=(32, 0, 4), neuron_count_millions=2,
    ei_ratio=0.75, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["glutamate", "gaba"],
    oscillation_rest=_osc(gamma=0.3, beta=0.3, alpha=0.2),
    functions=["consciousness integration", "binding cortical streams",
               "attentional spotlight", "unity of experience",
               "flow state integration substrate"],
    connects_to=["cortex_wide", "dlPFC", "visual_cortex", "auditory_cortex"],
))

_r(BrainRegion(
    name="Bed Nucleus of the Stria Terminalis", abbrev="BNST",
    lobe="subcortical", system="limbic", network=LIM,
    mni_xyz=(8, 4, -4), neuron_count_millions=0.5,
    ei_ratio=0.50, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["gaba", "CRF", "norepinephrine"],
    oscillation_rest=_osc(theta=0.4, beta=0.25),
    functions=["sustained anxiety (vs acute fear)", "anticipatory anxiety",
               "torschlusspanik sustained component", "contextual fear",
               "stress-induced anxiety"],
    connects_to=["amygdala", "hypothalamus", "NAcc", "VTA", "PAG"],
))

_r(BrainRegion(
    name="Septal Nuclei", abbrev="septal",
    lobe="subcortical", system="limbic", network=LIM,
    mni_xyz=(0, 16, 0), neuron_count_millions=3,
    ei_ratio=0.60, tau_e_ms=10, tau_i_ms=7,
    primary_nts=["acetylcholine", "gaba", "oxytocin"],
    oscillation_rest=_osc(theta=0.5, delta=0.2, alpha=0.15),
    functions=["social reward", "bonding", "pleasure",
               "hippocampal theta generation", "reward-aversion balance",
               "ubuntu substrate"],
    connects_to=["hippocampus", "hypothalamus", "NAcc", "amygdala"],
))

# ── INTEROCEPTIVE / VISCERAL ──────────────────────────────────────────────────

_r(BrainRegion(
    name="Spinal Cord (autonomic)", abbrev="spinal_cord",
    lobe="brainstem", system="brainstem", network=BS,
    mni_xyz=(0, -40, -60), neuron_count_millions=1000,
    ei_ratio=0.70, tau_e_ms=5, tau_i_ms=4,
    primary_nts=["glutamate", "gaba", "substance_P", "endorphins"],
    oscillation_rest=_osc(delta=0.5, theta=0.2),
    functions=["autonomic nervous system relay", "somatic sensation relay",
               "gut-brain axis relay", "skin sensation",
               "visceral-body state signals for interoception"],
    connects_to=["brainstem", "hypothalamus", "PAG"],
))

# ── FRONTAL REGIONS (additional) ─────────────────────────────────────────────

_r(BrainRegion(
    name="Frontopolar Cortex", abbrev="FPC",
    lobe="frontal", system="cortex", network=DMN,
    mni_xyz=(0, 60, 8), neuron_count_millions=80,
    ei_ratio=0.78, tau_e_ms=16, tau_i_ms=11,
    primary_nts=["dopamine", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.4, theta=0.25, beta=0.2),
    functions=["prospective memory", "multitasking", "branching cognition",
               "sehnsucht/fernweh prospective imagination",
               "considering unchosen alternatives"],
    connects_to=["dlPFC", "mPFC", "hippocampus", "PCC"],
))

_r(BrainRegion(
    name="Right Hemisphere dlPFC", abbrev="dlPFC_R",
    lobe="frontal", system="cortex", network=CEN,
    mni_xyz=(44, 36, 20), neuron_count_millions=180,
    ei_ratio=0.80, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["dopamine", "norepinephrine", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.3, beta=0.4, gamma=0.15),
    functions=["negative affect regulation", "vigilance", "withdrawal motivation",
               "world-model maintenance", "analytic problem solving"],
    connects_to=["dlPFC", "amygdala", "PPC", "thalamus"],
))

_r(BrainRegion(
    name="Lateral Prefrontal Cortex", abbrev="LPFC",
    lobe="frontal", system="cortex", network=CEN,
    mni_xyz=(-44, 28, 8), neuron_count_millions=150,
    ei_ratio=0.80, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["dopamine", "glutamate", "gaba"],
    oscillation_rest=_osc(alpha=0.3, beta=0.4, gamma=0.12),
    functions=["cognitive flexibility", "rule-based reasoning",
               "epistemic curiosity goal pursuit",
               "cognitive dissonance resolution attempts"],
    connects_to=["dlPFC", "OFC", "angular_gyrus", "thalamus"],
))

_r(BrainRegion(
    name="Cortex (global broadcast)", abbrev="cortex_wide",
    lobe="frontal", system="cortex", network=CEN,
    mni_xyz=(0, 0, 40), neuron_count_millions=16000,
    ei_ratio=0.80, tau_e_ms=12, tau_i_ms=8,
    primary_nts=["glutamate", "gaba", "acetylcholine", "norepinephrine"],
    oscillation_rest=_osc(alpha=0.4, beta=0.3, gamma=0.15),
    functions=["global workspace", "neuromodulator target"],
    connects_to=[],
))


def get_region(abbrev: str) -> Optional[BrainRegion]:
    return BRAIN_REGIONS.get(abbrev)


def regions_by_network(network: str) -> List[BrainRegion]:
    return [r for r in BRAIN_REGIONS.values() if r.network == network]


def regions_by_system(system: str) -> List[BrainRegion]:
    return [r for r in BRAIN_REGIONS.values() if r.system == system]


# Total simulated neuron count
TOTAL_NEURONS_MILLIONS = sum(r.neuron_count_millions for r in BRAIN_REGIONS.values())
TOTAL_REGIONS = len(BRAIN_REGIONS)
