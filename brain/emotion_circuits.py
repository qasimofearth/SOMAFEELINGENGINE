"""
emotion_circuits.py — All 65 emotions mapped to neural circuits

Each EmotionCircuit defines:
  - region_activations: which regions fire and at what level
  - nt_drives: neurotransmitter modulation (delta from baseline)
  - oscillation_signature: expected EEG band profile
  - attractor_label: what brain state this settles into

Sources: fMRI meta-analyses (Lindquist et al.), lesion studies,
pharmacological dissections, Damasio somatic marker hypothesis,
Panksepp primary emotion systems (SEEKING, RAGE, FEAR, LUST, CARE, PANIC/GRIEF, PLAY).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class EmotionCircuit:
    name: str
    # (region_abbrev, activation_level [0,1])
    region_activations: List[Tuple[str, float]]
    # NT abbrev -> drive [-1, 1] (positive = increase above baseline)
    nt_drives: Dict[str, float]
    # EEG band -> relative power (sum to ~1)
    oscillation_signature: Dict[str, float]
    description: str = ""


EMOTION_CIRCUITS: Dict[str, EmotionCircuit] = {}


def _ec(circuit: EmotionCircuit) -> EmotionCircuit:
    EMOTION_CIRCUITS[circuit.name.lower()] = circuit
    return circuit


# ── PRIMARY / PLUTCHIK ────────────────────────────────────────────────────────

_ec(EmotionCircuit(
    name="Joy",
    region_activations=[
        ("NAcc", 0.85), ("VTA", 0.80), ("mPFC", 0.65),
        ("OFC", 0.60), ("vmPFC", 0.55), ("hippocampus", 0.50),
        ("septal", 0.55), ("amygdala", 0.25),
    ],
    nt_drives={"dopamine": 0.7, "serotonin": 0.4, "endorphins": 0.4,
               "gaba": 0.2, "cortisol": -0.3},
    oscillation_signature={"delta": 0.05, "theta": 0.15, "alpha": 0.25,
                            "beta": 0.25, "gamma": 0.30},
    description="Mesolimbic dopamine surge. NAcc reward signal. Positive valence attractor.",
))

_ec(EmotionCircuit(
    name="Ecstasy",
    region_activations=[
        ("NAcc", 0.95), ("VTA", 0.90), ("mPFC", 0.80),
        ("OFC", 0.80), ("PAG", 0.65), ("claustrum", 0.70),
        ("aI", 0.60), ("amygdala", 0.30),
    ],
    nt_drives={"dopamine": 1.0, "endorphins": 0.8, "serotonin": 0.6,
               "anandamide": 0.5, "oxytocin": 0.4, "cortisol": -0.4},
    oscillation_signature={"delta": 0.05, "theta": 0.10, "alpha": 0.15,
                            "beta": 0.20, "gamma": 0.50},
    description="Extreme reward. Gamma burst. Full mesolimbic flood.",
))

_ec(EmotionCircuit(
    name="Sadness",
    region_activations=[
        ("sgACC", 0.75), ("mPFC", 0.65), ("hippocampus", 0.60),
        ("amygdala", 0.55), ("aI", 0.50), ("thalamus", 0.50),
        ("NAcc", 0.15), ("VTA", 0.20),
    ],
    nt_drives={"serotonin": -0.4, "dopamine": -0.4, "norepinephrine": -0.2,
               "substance_P": 0.4, "cortisol": 0.3},
    oscillation_signature={"delta": 0.20, "theta": 0.35, "alpha": 0.25,
                            "beta": 0.12, "gamma": 0.08},
    description="Subgenual ACC, hippocampal withdrawal. Theta/delta dominance. "
                "Serotonin and dopamine withdrawal.",
))

_ec(EmotionCircuit(
    name="Grief",
    region_activations=[
        ("sgACC", 0.85), ("mPFC", 0.75), ("hippocampus", 0.70),
        ("amygdala", 0.65), ("aI", 0.65), ("PAG", 0.60),
        ("thalamus", 0.55), ("NAcc", 0.10), ("VTA", 0.15),
    ],
    nt_drives={"serotonin": -0.6, "dopamine": -0.6, "substance_P": 0.7,
               "CRF": 0.5, "cortisol": 0.5, "endorphins": 0.2},
    oscillation_signature={"delta": 0.30, "theta": 0.40, "alpha": 0.18,
                            "beta": 0.08, "gamma": 0.04},
    description="Full grief circuit. PAG vocalizations, sgACC rumination loop, "
                "hippocampal memory replay. Heavy theta.",
))

_ec(EmotionCircuit(
    name="Anger",
    region_activations=[
        ("amygdala", 0.80), ("dACC", 0.75), ("hypothalamus", 0.70),
        ("locus_coeruleus", 0.75), ("M1", 0.55), ("dlPFC", 0.40),
        ("vmPFC", 0.25),
    ],
    nt_drives={"norepinephrine": 0.7, "dopamine": 0.3, "glutamate": 0.5,
               "gaba": -0.3, "cortisol": 0.4, "CRF": 0.4},
    oscillation_signature={"delta": 0.08, "theta": 0.15, "alpha": 0.20,
                            "beta": 0.35, "gamma": 0.22},
    description="Amygdala-hypothalamus-motor activation. NE surge. Beta/gamma dominance.",
))

_ec(EmotionCircuit(
    name="Rage",
    region_activations=[
        ("amygdala", 0.95), ("hypothalamus", 0.90), ("PAG", 0.85),
        ("dACC", 0.85), ("locus_coeruleus", 0.90), ("M1", 0.70),
        ("dlPFC", 0.20), ("vmPFC", 0.10),
    ],
    nt_drives={"norepinephrine": 1.0, "glutamate": 0.8, "dopamine": 0.4,
               "gaba": -0.6, "cortisol": 0.7, "CRF": 0.7},
    oscillation_signature={"delta": 0.05, "theta": 0.10, "alpha": 0.15,
                            "beta": 0.30, "gamma": 0.40},
    description="Panksepp's RAGE system. Hypothalamic attack area. vmPFC suppressed.",
))

_ec(EmotionCircuit(
    name="Fear",
    region_activations=[
        ("amygdala", 0.85), ("BLA", 0.80), ("LA", 0.85),
        ("hypothalamus", 0.75), ("PAG", 0.70), ("locus_coeruleus", 0.80),
        ("dACC", 0.65), ("aI", 0.65), ("dlPFC", 0.35),
    ],
    nt_drives={"norepinephrine": 0.9, "CRF": 0.7, "cortisol": 0.6,
               "glutamate": 0.6, "gaba": -0.4, "dopamine": -0.2},
    oscillation_signature={"delta": 0.08, "theta": 0.20, "alpha": 0.20,
                            "beta": 0.30, "gamma": 0.22},
    description="Classic fear circuit. BLA-CeA-PAG-hypothalamus axis. NE+CRF surge.",
))

_ec(EmotionCircuit(
    name="Terror",
    region_activations=[
        ("amygdala", 0.98), ("CeA", 0.95), ("PAG", 0.90),
        ("hypothalamus", 0.90), ("locus_coeruleus", 0.95),
        ("BNST", 0.80), ("dlPFC", 0.15), ("vmPFC", 0.10),
    ],
    nt_drives={"norepinephrine": 1.0, "CRF": 1.0, "cortisol": 0.9,
               "substance_P": 0.7, "gaba": -0.7},
    oscillation_signature={"delta": 0.05, "theta": 0.15, "alpha": 0.15,
                            "beta": 0.30, "gamma": 0.35},
    description="Maximal fear. Prefrontal offline. Survival mode.",
))

_ec(EmotionCircuit(
    name="Disgust",
    region_activations=[
        ("aI", 0.85), ("OFC", 0.70), ("BLA", 0.65),
        ("dACC", 0.55), ("M1", 0.40), ("pI", 0.60),
        ("thalamus", 0.45),
    ],
    nt_drives={"serotonin": -0.3, "norepinephrine": 0.3, "gaba": 0.2,
               "substance_P": 0.3},
    oscillation_signature={"delta": 0.10, "theta": 0.20, "alpha": 0.25,
                            "beta": 0.30, "gamma": 0.15},
    description="Anterior insula signature. OFC taste/smell integration. Nausea pathway.",
))

_ec(EmotionCircuit(
    name="Surprise",
    region_activations=[
        ("locus_coeruleus", 0.80), ("thalamus", 0.75), ("amygdala", 0.60),
        ("dACC", 0.65), ("hippocampus", 0.65), ("dlPFC", 0.55),
        ("aI", 0.50), ("claustrum", 0.60),
    ],
    nt_drives={"norepinephrine": 0.8, "acetylcholine": 0.5, "dopamine": 0.3,
               "glutamate": 0.5},
    oscillation_signature={"delta": 0.05, "theta": 0.20, "alpha": 0.20,
                            "beta": 0.30, "gamma": 0.25},
    description="Phasic NE discharge from LC. Thalamic arousal. Prediction error signal.",
))

_ec(EmotionCircuit(
    name="Trust",
    region_activations=[
        ("vmPFC", 0.70), ("OFC", 0.65), ("hippocampus", 0.55),
        ("NAcc", 0.55), ("temporal_pole", 0.60), ("amygdala", 0.20),
        ("septal", 0.55),
    ],
    nt_drives={"oxytocin": 0.6, "serotonin": 0.4, "dopamine": 0.3,
               "gaba": 0.3, "cortisol": -0.3},
    oscillation_signature={"delta": 0.08, "theta": 0.20, "alpha": 0.40,
                            "beta": 0.20, "gamma": 0.12},
    description="vmPFC suppression of amygdala. Oxytocin-mediated social safety signal.",
))

_ec(EmotionCircuit(
    name="Anticipation",
    region_activations=[
        ("VTA", 0.70), ("NAcc", 0.65), ("dACC", 0.65),
        ("dlPFC", 0.60), ("amygdala", 0.45), ("FPC", 0.55),
        ("hippocampus", 0.50),
    ],
    nt_drives={"dopamine": 0.6, "norepinephrine": 0.4, "acetylcholine": 0.3,
               "glutamate": 0.4},
    oscillation_signature={"delta": 0.06, "theta": 0.25, "alpha": 0.25,
                            "beta": 0.28, "gamma": 0.16},
    description="Dopamine ramp before expected reward. Panksepp's SEEKING circuit. "
                "NAcc activity before outcome.",
))

_ec(EmotionCircuit(
    name="Love",
    region_activations=[
        ("VTA", 0.85), ("NAcc", 0.80), ("mPFC", 0.70),
        ("vmPFC", 0.65), ("PVN", 0.75), ("hypothalamus", 0.65),
        ("aI", 0.55), ("amygdala", 0.25),
    ],
    nt_drives={"dopamine": 0.8, "oxytocin": 0.9, "serotonin": 0.3,
               "endorphins": 0.5, "cortisol": -0.2},
    oscillation_signature={"delta": 0.06, "theta": 0.18, "alpha": 0.30,
                            "beta": 0.25, "gamma": 0.21},
    description="Aron et al. fMRI: VTA-NAcc dopamine + PVN oxytocin. "
                "Amygdala suppressed (reduced threat appraisal).",
))

_ec(EmotionCircuit(
    name="Awe",
    region_activations=[
        ("mPFC", 0.75), ("precuneus", 0.80), ("PCC", 0.75),
        ("dACC", 0.65), ("aI", 0.70), ("NAcc", 0.55),
        ("amygdala", 0.45), ("claustrum", 0.70), ("thalamus", 0.60),
    ],
    nt_drives={"dopamine": 0.5, "norepinephrine": 0.4, "serotonin": 0.3,
               "endorphins": 0.3, "anandamide": 0.3, "glutamate": 0.4},
    oscillation_signature={"delta": 0.05, "theta": 0.20, "alpha": 0.30,
                            "beta": 0.25, "gamma": 0.20},
    description="Keltner & Haidt: vast, need for accommodation. DMN+SN co-activation. "
                "Self-referential network restructuring.",
))

_ec(EmotionCircuit(
    name="Wonder",
    region_activations=[
        ("precuneus", 0.70), ("mPFC", 0.60), ("NAcc", 0.65),
        ("dACC", 0.55), ("aI", 0.55), ("visual_cortex", 0.55),
        ("hippocampus", 0.50), ("amygdala", 0.30),
    ],
    nt_drives={"dopamine": 0.5, "norepinephrine": 0.4, "acetylcholine": 0.4,
               "serotonin": 0.2},
    oscillation_signature={"delta": 0.05, "theta": 0.22, "alpha": 0.32,
                            "beta": 0.26, "gamma": 0.15},
    description="Lighter than awe. Novelty + reward. Self intact. Curious positive arousal.",
))

_ec(EmotionCircuit(
    name="Hope",
    region_activations=[
        ("FPC", 0.70), ("dlPFC", 0.65), ("NAcc", 0.60),
        ("VTA", 0.55), ("hippocampus", 0.55), ("mPFC", 0.60),
        ("amygdala", 0.30),
    ],
    nt_drives={"dopamine": 0.5, "serotonin": 0.3, "norepinephrine": 0.3},
    oscillation_signature={"delta": 0.06, "theta": 0.22, "alpha": 0.32,
                            "beta": 0.26, "gamma": 0.14},
    description="Prospective simulation (FPC) + mild dopamine anticipation.",
))

_ec(EmotionCircuit(
    name="Pride",
    region_activations=[
        ("mPFC", 0.75), ("NAcc", 0.65), ("VTA", 0.60),
        ("OFC", 0.55), ("dlPFC", 0.55), ("aI", 0.45),
    ],
    nt_drives={"dopamine": 0.6, "serotonin": 0.3, "norepinephrine": 0.2},
    oscillation_signature={"delta": 0.05, "theta": 0.15, "alpha": 0.30,
                            "beta": 0.30, "gamma": 0.20},
    description="Self-referential mPFC + reward. Upright posture motor correlates (M1).",
))

_ec(EmotionCircuit(
    name="Shame",
    region_activations=[
        ("mPFC", 0.70), ("sgACC", 0.65), ("amygdala", 0.70),
        ("aI", 0.65), ("dACC", 0.60), ("NAcc", 0.20),
    ],
    nt_drives={"cortisol": 0.6, "serotonin": -0.4, "dopamine": -0.3,
               "substance_P": 0.4, "norepinephrine": 0.4},
    oscillation_signature={"delta": 0.15, "theta": 0.35, "alpha": 0.25,
                            "beta": 0.18, "gamma": 0.07},
    description="Threat to social self-concept. Amygdala+sgACC loop. "
                "HPA stress. Collapse of reward.",
))

_ec(EmotionCircuit(
    name="Contempt",
    region_activations=[
        ("OFC", 0.65), ("amygdala", 0.55), ("dACC", 0.50),
        ("dlPFC", 0.55), ("mPFC", 0.45), ("NAcc", 0.35),
    ],
    nt_drives={"serotonin": 0.2, "norepinephrine": 0.3, "dopamine": 0.2},
    oscillation_signature={"delta": 0.08, "theta": 0.18, "alpha": 0.30,
                            "beta": 0.30, "gamma": 0.14},
    description="Social hierarchy appraisal. OFC moral value judgment. "
                "Approach-avoidance balance.",
))

_ec(EmotionCircuit(
    name="Remorse",
    region_activations=[
        ("mPFC", 0.70), ("sgACC", 0.60), ("hippocampus", 0.65),
        ("amygdala", 0.55), ("aI", 0.55), ("OFC", 0.50),
    ],
    nt_drives={"serotonin": -0.3, "dopamine": -0.3, "substance_P": 0.3,
               "cortisol": 0.3},
    oscillation_signature={"delta": 0.15, "theta": 0.30, "alpha": 0.28,
                            "beta": 0.18, "gamma": 0.09},
    description="Self-referential review of past action. Hippocampal replay + sgACC.",
))

_ec(EmotionCircuit(
    name="Boredom",
    region_activations=[
        ("NAcc", 0.15), ("dACC", 0.30), ("dlPFC", 0.30),
        ("mPFC", 0.55), ("PCC", 0.55), ("locus_coeruleus", 0.20),
        ("VTA", 0.20),
    ],
    nt_drives={"dopamine": -0.4, "norepinephrine": -0.3, "acetylcholine": -0.2},
    oscillation_signature={"delta": 0.12, "theta": 0.32, "alpha": 0.35,
                            "beta": 0.14, "gamma": 0.07},
    description="Dopamine anhedonia. No salience. Default mode takes over.",
))

_ec(EmotionCircuit(
    name="Envy",
    region_activations=[
        ("dACC", 0.70), ("amygdala", 0.65), ("NAcc", 0.45),
        ("mPFC", 0.60), ("aI", 0.55), ("dlPFC", 0.40),
    ],
    nt_drives={"norepinephrine": 0.4, "dopamine": -0.2, "cortisol": 0.3,
               "serotonin": -0.3},
    oscillation_signature={"delta": 0.08, "theta": 0.20, "alpha": 0.25,
                            "beta": 0.32, "gamma": 0.15},
    description="dACC pain of comparison. Takahashi et al. — dACC activates to others' gain.",
))

_ec(EmotionCircuit(
    name="Gratitude",
    region_activations=[
        ("mPFC", 0.70), ("NAcc", 0.65), ("VTA", 0.60),
        ("vmPFC", 0.60), ("aI", 0.50), ("hippocampus", 0.50),
        ("amygdala", 0.25),
    ],
    nt_drives={"dopamine": 0.5, "serotonin": 0.5, "oxytocin": 0.4,
               "endorphins": 0.3, "cortisol": -0.3},
    oscillation_signature={"delta": 0.06, "theta": 0.15, "alpha": 0.35,
                            "beta": 0.25, "gamma": 0.19},
    description="Mentalizing network + reward. Fox et al.: mPFC, ACC, medial PCC.",
))

_ec(EmotionCircuit(
    name="Optimism",
    region_activations=[
        ("FPC", 0.70), ("dlPFC", 0.60), ("NAcc", 0.65),
        ("VTA", 0.55), ("amygdala", 0.25), ("hippocampus", 0.50),
    ],
    nt_drives={"dopamine": 0.6, "serotonin": 0.4, "norepinephrine": 0.2},
    oscillation_signature={"delta": 0.05, "theta": 0.18, "alpha": 0.35,
                            "beta": 0.28, "gamma": 0.14},
    description="Sharot et al.: FPC bias toward positive future. "
                "Reduced amygdala response to negative outcomes.",
))

_ec(EmotionCircuit(
    name="Admiration",
    region_activations=[
        ("mPFC", 0.65), ("temporal_pole", 0.60), ("NAcc", 0.55),
        ("OFC", 0.55), ("amygdala", 0.30), ("TPJ", 0.55),
    ],
    nt_drives={"dopamine": 0.4, "oxytocin": 0.3, "serotonin": 0.3},
    oscillation_signature={"delta": 0.06, "theta": 0.18, "alpha": 0.35,
                            "beta": 0.27, "gamma": 0.14},
    description="Virtue perception (mPFC), person knowledge (temporal pole), "
                "mild approach motivation.",
))

_ec(EmotionCircuit(
    name="Acceptance",
    region_activations=[
        ("vmPFC", 0.70), ("sgACC", 0.50), ("raphe", 0.65),
        ("aI", 0.40), ("hippocampus", 0.50), ("mPFC", 0.55),
        ("amygdala", 0.20),
    ],
    nt_drives={"serotonin": 0.6, "gaba": 0.4, "anandamide": 0.3,
               "cortisol": -0.4},
    oscillation_signature={"delta": 0.10, "theta": 0.20, "alpha": 0.45,
                            "beta": 0.17, "gamma": 0.08},
    description="Raphe serotonin + vmPFC-amygdala inhibition. Alpha dominance.",
))

_ec(EmotionCircuit(
    name="Serenity",
    region_activations=[
        ("vmPFC", 0.65), ("raphe", 0.70), ("sgACC", 0.45),
        ("hippocampus", 0.40), ("amygdala", 0.15), ("PCC", 0.55),
    ],
    nt_drives={"serotonin": 0.7, "gaba": 0.5, "anandamide": 0.4,
               "cortisol": -0.5, "norepinephrine": -0.3},
    oscillation_signature={"delta": 0.12, "theta": 0.18, "alpha": 0.50,
                            "beta": 0.14, "gamma": 0.06},
    description="Deep serotonin + GABA. Alpha peak. Amygdala quiet. HPA suppressed.",
))

_ec(EmotionCircuit(
    name="Calm",
    region_activations=[
        ("vmPFC", 0.55), ("raphe", 0.60), ("amygdala", 0.15),
        ("PCC", 0.45), ("precuneus", 0.45),
    ],
    nt_drives={"serotonin": 0.5, "gaba": 0.4, "cortisol": -0.3},
    oscillation_signature={"delta": 0.10, "theta": 0.20, "alpha": 0.50,
                            "beta": 0.14, "gamma": 0.06},
    description="Resting alpha state. Moderate serotonin floor.",
))

_ec(EmotionCircuit(
    name="Pensiveness",
    region_activations=[
        ("mPFC", 0.60), ("PCC", 0.65), ("hippocampus", 0.60),
        ("sgACC", 0.45), ("precuneus", 0.55), ("amygdala", 0.35),
    ],
    nt_drives={"serotonin": 0.1, "dopamine": -0.1, "acetylcholine": 0.3},
    oscillation_signature={"delta": 0.12, "theta": 0.32, "alpha": 0.33,
                            "beta": 0.15, "gamma": 0.08},
    description="Default mode autobiographical replay. Low arousal, mild negative valence.",
))

_ec(EmotionCircuit(
    name="Interest",
    region_activations=[
        ("NAcc", 0.55), ("VTA", 0.50), ("dlPFC", 0.55),
        ("amygdala", 0.35), ("hippocampus", 0.50), ("dACC", 0.45),
    ],
    nt_drives={"dopamine": 0.4, "norepinephrine": 0.3, "acetylcholine": 0.4},
    oscillation_signature={"delta": 0.05, "theta": 0.25, "alpha": 0.30,
                            "beta": 0.28, "gamma": 0.12},
    description="SEEKING substrate. Mild dopamine anticipation. Mild amygdala orientation.",
))

_ec(EmotionCircuit(
    name="Apprehension",
    region_activations=[
        ("amygdala", 0.55), ("BNST", 0.60), ("dACC", 0.50),
        ("locus_coeruleus", 0.55), ("aI", 0.50), ("dlPFC", 0.45),
    ],
    nt_drives={"norepinephrine": 0.5, "CRF": 0.4, "gaba": -0.2,
               "cortisol": 0.2},
    oscillation_signature={"delta": 0.08, "theta": 0.25, "alpha": 0.28,
                            "beta": 0.28, "gamma": 0.11},
    description="Anticipatory anxiety (BNST sustained anxiety vs acute amygdala fear).",
))

_ec(EmotionCircuit(
    name="Vigilance",
    region_activations=[
        ("dACC", 0.70), ("amygdala", 0.55), ("locus_coeruleus", 0.70),
        ("dlPFC", 0.60), ("thalamus", 0.60), ("aI", 0.50),
    ],
    nt_drives={"norepinephrine": 0.7, "acetylcholine": 0.5, "dopamine": 0.2},
    oscillation_signature={"delta": 0.05, "theta": 0.18, "alpha": 0.22,
                            "beta": 0.38, "gamma": 0.17},
    description="LC-NE hyperactivation. High beta/gamma vigilance state.",
))

_ec(EmotionCircuit(
    name="Distraction",
    region_activations=[
        ("PCC", 0.70), ("mPFC", 0.65), ("dlPFC", 0.30),
        ("dACC", 0.25), ("NAcc", 0.35),
    ],
    nt_drives={"dopamine": -0.1, "acetylcholine": -0.2, "norepinephrine": -0.2},
    oscillation_signature={"delta": 0.10, "theta": 0.35, "alpha": 0.35,
                            "beta": 0.14, "gamma": 0.06},
    description="DMN dominance, task-negative state. Mind wandering. "
                "Frontoparietal executive network suppressed.",
))

_ec(EmotionCircuit(
    name="Loathing",
    region_activations=[
        ("aI", 0.85), ("OFC", 0.75), ("amygdala", 0.75),
        ("dACC", 0.60), ("pI", 0.65),
    ],
    nt_drives={"serotonin": -0.5, "norepinephrine": 0.4, "substance_P": 0.5,
               "gaba": -0.3},
    oscillation_signature={"delta": 0.08, "theta": 0.18, "alpha": 0.22,
                            "beta": 0.32, "gamma": 0.20},
    description="Maximal disgust. Insula hyperactivation.",
))

_ec(EmotionCircuit(
    name="Annoyance",
    region_activations=[
        ("dACC", 0.60), ("amygdala", 0.50), ("dlPFC", 0.45),
        ("aI", 0.45), ("locus_coeruleus", 0.45),
    ],
    nt_drives={"norepinephrine": 0.4, "dopamine": -0.1, "serotonin": -0.2},
    oscillation_signature={"delta": 0.07, "theta": 0.18, "alpha": 0.25,
                            "beta": 0.35, "gamma": 0.15},
    description="Low-level anger circuit. dACC conflict signal.",
))

# ── CULTURAL EMOTIONS ─────────────────────────────────────────────────────────

_ec(EmotionCircuit(
    name="Saudade",
    region_activations=[
        ("hippocampus", 0.75), ("mPFC", 0.65), ("sgACC", 0.55),
        ("temporal_pole", 0.60), ("PCC", 0.65), ("aI", 0.50),
        ("amygdala", 0.40), ("NAcc", 0.25),
    ],
    nt_drives={"serotonin": -0.2, "dopamine": -0.2, "oxytocin": 0.2,
               "acetylcholine": 0.3, "anandamide": 0.2},
    oscillation_signature={"delta": 0.15, "theta": 0.38, "alpha": 0.28,
                            "beta": 0.13, "gamma": 0.06},
    description="Hippocampal memory replay of absent beloved. "
                "Temporal pole encoding the 'person who is gone'. Theta dominance.",
))

_ec(EmotionCircuit(
    name="Mono no Aware",
    region_activations=[
        ("mPFC", 0.60), ("PCC", 0.65), ("hippocampus", 0.55),
        ("sgACC", 0.45), ("raphe", 0.55), ("precuneus", 0.55),
        ("amygdala", 0.30),
    ],
    nt_drives={"serotonin": 0.2, "dopamine": -0.1, "anandamide": 0.3,
               "acetylcholine": 0.2},
    oscillation_signature={"delta": 0.12, "theta": 0.28, "alpha": 0.38,
                            "beta": 0.15, "gamma": 0.07},
    description="DMN-mediated impermanence perception. Serotonin-modulated mild melancholy. "
                "Alpha-theta blend — meditative awareness of passing.",
))

_ec(EmotionCircuit(
    name="Hiraeth",
    region_activations=[
        ("hippocampus", 0.80), ("sgACC", 0.65), ("mPFC", 0.65),
        ("temporal_pole", 0.65), ("PCC", 0.60), ("aI", 0.55),
        ("amygdala", 0.45),
    ],
    nt_drives={"serotonin": -0.3, "dopamine": -0.3, "cortisol": 0.2,
               "substance_P": 0.3, "oxytocin": 0.1},
    oscillation_signature={"delta": 0.18, "theta": 0.40, "alpha": 0.25,
                            "beta": 0.11, "gamma": 0.06},
    description="Deeper than saudade — the home doesn't exist. "
                "Hippocampal memory of imagined place. Substance P grief tinge.",
))

_ec(EmotionCircuit(
    name="Ubuntu",
    region_activations=[
        ("mPFC", 0.75), ("TPJ", 0.70), ("NAcc", 0.70),
        ("VTA", 0.65), ("PVN", 0.65), ("septal", 0.65),
        ("amygdala", 0.20), ("temporal_pole", 0.60),
    ],
    nt_drives={"oxytocin": 0.9, "dopamine": 0.6, "endorphins": 0.5,
               "serotonin": 0.4, "cortisol": -0.3},
    oscillation_signature={"delta": 0.05, "theta": 0.18, "alpha": 0.28,
                            "beta": 0.26, "gamma": 0.23},
    description="TPJ-mPFC mentalizing network + full oxytocin system. "
                "Self-boundary dissolution. Collective reward.",
))

_ec(EmotionCircuit(
    name="Schadenfreude",
    region_activations=[
        ("NAcc", 0.65), ("VTA", 0.55), ("amygdala", 0.45),
        ("dACC", 0.50), ("OFC", 0.55), ("mPFC", 0.45),
    ],
    nt_drives={"dopamine": 0.5, "norepinephrine": 0.3, "serotonin": 0.1},
    oscillation_signature={"delta": 0.07, "theta": 0.18, "alpha": 0.25,
                            "beta": 0.30, "gamma": 0.20},
    description="Takahashi et al. (2009): NAcc activates to rivals' misfortune. "
                "The reward circuit fires on another's loss.",
))

_ec(EmotionCircuit(
    name="Weltschmerz",
    region_activations=[
        ("sgACC", 0.75), ("mPFC", 0.65), ("hippocampus", 0.60),
        ("habenula", 0.70), ("amygdala", 0.55), ("PCC", 0.60),
        ("VTA", 0.15), ("NAcc", 0.15),
    ],
    nt_drives={"serotonin": -0.5, "dopamine": -0.6, "cortisol": 0.5,
               "substance_P": 0.4, "norepinephrine": -0.3},
    oscillation_signature={"delta": 0.25, "theta": 0.40, "alpha": 0.22,
                            "beta": 0.09, "gamma": 0.04},
    description="Habenula anti-reward signal + sgACC rumination + dopamine withdrawal. "
                "The world-pain that arrives when ideal meets real.",
))

_ec(EmotionCircuit(
    name="Sehnsucht",
    region_activations=[
        ("FPC", 0.75), ("mPFC", 0.65), ("hippocampus", 0.60),
        ("NAcc", 0.50), ("VTA", 0.45), ("sgACC", 0.40),
        ("precuneus", 0.60),
    ],
    nt_drives={"dopamine": 0.3, "serotonin": -0.1, "norepinephrine": 0.2,
               "anandamide": 0.2},
    oscillation_signature={"delta": 0.10, "theta": 0.28, "alpha": 0.35,
                            "beta": 0.18, "gamma": 0.09},
    description="Frontopolar prospection + mild dopamine pull toward imagined ideal. "
                "Unfulfilled positive valence — reaching toward the unlived life.",
))

_ec(EmotionCircuit(
    name="Fernweh",
    region_activations=[
        ("FPC", 0.70), ("dlPFC", 0.60), ("NAcc", 0.65),
        ("VTA", 0.60), ("hippocampus", 0.55), ("dACC", 0.50),
        ("aI", 0.45),
    ],
    nt_drives={"dopamine": 0.6, "norepinephrine": 0.4, "anandamide": 0.3},
    oscillation_signature={"delta": 0.05, "theta": 0.20, "alpha": 0.28,
                            "beta": 0.30, "gamma": 0.17},
    description="Frontopolar future simulation + dopamine pull toward unexperienced places. "
                "High SEEKING arousal toward distant unknown.",
))

_ec(EmotionCircuit(
    name="Meraki",
    region_activations=[
        ("VTA", 0.80), ("NAcc", 0.75), ("mPFC", 0.70),
        ("dlPFC", 0.65), ("M1", 0.55), ("aI", 0.60),
        ("claustrum", 0.65), ("amygdala", 0.20),
    ],
    nt_drives={"dopamine": 0.8, "norepinephrine": 0.5, "anandamide": 0.4,
               "acetylcholine": 0.5, "cortisol": -0.2},
    oscillation_signature={"delta": 0.04, "theta": 0.15, "alpha": 0.20,
                            "beta": 0.30, "gamma": 0.31},
    description="Sustained flow-like state fused with self-expression. "
                "Claustrum binding of creative action and identity.",
))

_ec(EmotionCircuit(
    name="Mamihlapinatapai",
    region_activations=[
        ("mPFC", 0.60), ("TPJ", 0.65), ("amygdala", 0.55),
        ("aI", 0.60), ("vmPFC", 0.50), ("OFC", 0.50),
        ("temporal_pole", 0.55),
    ],
    nt_drives={"oxytocin": 0.5, "dopamine": 0.3, "norepinephrine": 0.4},
    oscillation_signature={"delta": 0.07, "theta": 0.22, "alpha": 0.33,
                            "beta": 0.28, "gamma": 0.10},
    description="TPJ mentalizing (reading their intent) + amygdala social arousal + "
                "OFC approach-avoidance tension. Shared wanting, unspoken.",
))

_ec(EmotionCircuit(
    name="Torschlusspanik",
    region_activations=[
        ("amygdala", 0.80), ("BNST", 0.75), ("dACC", 0.75),
        ("locus_coeruleus", 0.80), ("dlPFC", 0.60), ("FPC", 0.65),
        ("aI", 0.70), ("STN", 0.60),
    ],
    nt_drives={"norepinephrine": 0.9, "CRF": 0.7, "cortisol": 0.6,
               "dopamine": 0.4, "gaba": -0.4},
    oscillation_signature={"delta": 0.06, "theta": 0.18, "alpha": 0.18,
                            "beta": 0.33, "gamma": 0.25},
    description="BNST sustained anxiety + FPC urgency simulation + LC NE + "
                "STN action suppression tension. Gate closing alarm.",
))

_ec(EmotionCircuit(
    name="Waldeinsamkeit",
    region_activations=[
        ("vmPFC", 0.65), ("PCC", 0.65), ("raphe", 0.70),
        ("hippocampus", 0.55), ("aI", 0.50), ("precuneus", 0.60),
        ("amygdala", 0.10), ("locus_coeruleus", 0.15),
    ],
    nt_drives={"serotonin": 0.6, "anandamide": 0.7, "gaba": 0.5,
               "norepinephrine": -0.3, "cortisol": -0.4},
    oscillation_signature={"delta": 0.12, "theta": 0.22, "alpha": 0.48,
                            "beta": 0.12, "gamma": 0.06},
    description="Nature-induced deactivation of threat circuits. "
                "Anandamide + serotonin. Deep alpha. LC at rest. "
                "Rightful solitude.",
))

_ec(EmotionCircuit(
    name="Kama Muta",
    region_activations=[
        ("mPFC", 0.75), ("NAcc", 0.75), ("VTA", 0.70),
        ("aI", 0.70), ("PVN", 0.70), ("amygdala", 0.35),
        ("precuneus", 0.60), ("PAG", 0.55),
    ],
    nt_drives={"oxytocin": 0.9, "dopamine": 0.7, "endorphins": 0.7,
               "serotonin": 0.3, "norepinephrine": 0.3},
    oscillation_signature={"delta": 0.05, "theta": 0.15, "alpha": 0.25,
                            "beta": 0.25, "gamma": 0.30},
    description="Oveis et al.: suddenly moved by love/tenderness. "
                "Anterior insula chills + chest-opening. Oxytocin + endorphin burst.",
))

_ec(EmotionCircuit(
    name="Wabi-sabi",
    region_activations=[
        ("vmPFC", 0.60), ("raphe", 0.65), ("OFC", 0.55),
        ("PCC", 0.60), ("aI", 0.45), ("precuneus", 0.55),
        ("amygdala", 0.15),
    ],
    nt_drives={"serotonin": 0.5, "anandamide": 0.5, "gaba": 0.4,
               "cortisol": -0.3},
    oscillation_signature={"delta": 0.14, "theta": 0.25, "alpha": 0.42,
                            "beta": 0.13, "gamma": 0.06},
    description="Aesthetic appreciation of imperfection. OFC value of worn things. "
                "Serotonin acceptance tone. Low arousal beauty.",
))

# ── SOMATIC EMOTIONS ──────────────────────────────────────────────────────────

_ec(EmotionCircuit(
    name="Frisson",
    region_activations=[
        ("auditory_cortex", 0.85), ("NAcc", 0.80), ("VTA", 0.75),
        ("aI", 0.80), ("PAG", 0.65), ("amygdala", 0.45),
        ("locus_coeruleus", 0.65), ("cerebellum", 0.55),
        ("S1", 0.60), ("spinal_cord", 0.55),
    ],
    nt_drives={"dopamine": 0.8, "endorphins": 0.7, "norepinephrine": 0.6,
               "oxytocin": 0.3},
    oscillation_signature={"delta": 0.05, "theta": 0.12, "alpha": 0.18,
                            "beta": 0.25, "gamma": 0.40},
    description="Blood & Zatorre (2001): NAcc+VTA dopamine at music peak. "
                "Anterior insula + S1 goosebump sensation. LC arousal surge. "
                "Gamma burst at skin response.",
))

_ec(EmotionCircuit(
    name="Flow",
    region_activations=[
        ("claustrum", 0.85), ("NAcc", 0.75), ("VTA", 0.70),
        ("dlPFC", 0.70), ("cerebellum", 0.75), ("M1", 0.65),
        ("aI", 0.50), ("mPFC", 0.35), ("dACC", 0.40),
        ("amygdala", 0.15), ("locus_coeruleus", 0.45),
    ],
    nt_drives={"dopamine": 0.7, "anandamide": 0.6, "norepinephrine": 0.4,
               "acetylcholine": 0.6, "gaba": 0.2, "serotonin": 0.3},
    oscillation_signature={"delta": 0.04, "theta": 0.18, "alpha": 0.35,
                            "beta": 0.22, "gamma": 0.21},
    description="Dietrich: transient hypofrontality. mPFC self-monitoring reduced. "
                "Claustrum binding action and experience. Alpha-gamma coupling.",
))

_ec(EmotionCircuit(
    name="Gut Feeling",
    region_activations=[
        ("aI", 0.75), ("sgACC", 0.60), ("hypothalamus", 0.55),
        ("spinal_cord", 0.65), ("amygdala", 0.60), ("vmPFC", 0.50),
        ("brainstem", 0.60),
    ],
    nt_drives={"norepinephrine": 0.4, "gaba": 0.2, "substance_P": 0.2,
               "anandamide": 0.2},
    oscillation_signature={"delta": 0.15, "theta": 0.35, "alpha": 0.28,
                            "beta": 0.16, "gamma": 0.06},
    description="Damasio somatic marker: insula reads body state before cognition. "
                "Vagal afferents to brainstem → insula → sgACC. Knowing before knowing.",
))

_ec(EmotionCircuit(
    name="Skin Hunger",
    region_activations=[
        ("S1", 0.70), ("aI", 0.75), ("sgACC", 0.65),
        ("hypothalamus", 0.60), ("amygdala", 0.55),
        ("NAcc", 0.35), ("PVN", 0.50),
    ],
    nt_drives={"oxytocin": -0.4, "substance_P": 0.4, "serotonin": -0.3,
               "cortisol": 0.3},
    oscillation_signature={"delta": 0.18, "theta": 0.35, "alpha": 0.25,
                            "beta": 0.15, "gamma": 0.07},
    description="Deprivation of CT-afferent touch signals to insula. "
                "Oxytocin withdrawal. Gentle grief in the body surface.",
))

_ec(EmotionCircuit(
    name="Almost Sneeze",
    region_activations=[
        ("brainstem", 0.85), ("cerebellum", 0.70), ("dACC", 0.70),
        ("aI", 0.70), ("locus_coeruleus", 0.75), ("thalamus", 0.65),
        ("S1", 0.55),
    ],
    nt_drives={"norepinephrine": 0.8, "substance_P": 0.5, "glutamate": 0.5},
    oscillation_signature={"delta": 0.06, "theta": 0.15, "alpha": 0.20,
                            "beta": 0.35, "gamma": 0.24},
    description="Brainstem sneezing circuit primed, cerebellum predicting, "
                "dACC holding conflicted resolution. Full-body anticipatory suspension.",
))

# ── SOCIAL / RELATIONAL EMOTIONS ─────────────────────────────────────────────

_ec(EmotionCircuit(
    name="Collective Effervescence",
    region_activations=[
        ("NAcc", 0.90), ("VTA", 0.85), ("PAG", 0.75),
        ("mPFC", 0.80), ("TPJ", 0.75), ("aI", 0.75),
        ("claustrum", 0.80), ("PVN", 0.70), ("cerebellum", 0.65),
    ],
    nt_drives={"dopamine": 0.9, "endorphins": 0.9, "oxytocin": 0.8,
               "serotonin": 0.5, "norepinephrine": 0.5, "cortisol": -0.3},
    oscillation_signature={"delta": 0.04, "theta": 0.12, "alpha": 0.20,
                            "beta": 0.25, "gamma": 0.39},
    description="Durkheim's collective effervescence. Synchronized movement → "
                "endorphin burst (Dunbar). TPJ self-other merge. "
                "Oxytocin + dopamine peak. Gamma coherence across claustrum.",
))

_ec(EmotionCircuit(
    name="Moral Elevation",
    region_activations=[
        ("mPFC", 0.75), ("NAcc", 0.65), ("VTA", 0.60),
        ("aI", 0.70), ("precuneus", 0.65), ("PVN", 0.55),
        ("amygdala", 0.30),
    ],
    nt_drives={"oxytocin": 0.6, "dopamine": 0.5, "serotonin": 0.4,
               "endorphins": 0.4},
    oscillation_signature={"delta": 0.05, "theta": 0.15, "alpha": 0.30,
                            "beta": 0.27, "gamma": 0.23},
    description="Haidt: warm upwelling in chest (aI interoception) + "
                "prosocial motivation (mPFC). Moral beauty activates reward system.",
))

_ec(EmotionCircuit(
    name="Empathic Distress",
    region_activations=[
        ("aI", 0.85), ("dACC", 0.80), ("amygdala", 0.75),
        ("mPFC", 0.65), ("sgACC", 0.70), ("TPJ", 0.60),
        ("PAG", 0.55), ("locus_coeruleus", 0.65),
    ],
    nt_drives={"norepinephrine": 0.7, "cortisol": 0.5, "substance_P": 0.5,
               "serotonin": -0.3, "dopamine": -0.2},
    oscillation_signature={"delta": 0.12, "theta": 0.28, "alpha": 0.20,
                            "beta": 0.28, "gamma": 0.12},
    description="Singer et al.: shared pain network (aI+dACC) overfiring. "
                "TPJ perspective-taking cannot buffer. Flooding with another's pain.",
))

_ec(EmotionCircuit(
    name="Compersion",
    region_activations=[
        ("NAcc", 0.75), ("VTA", 0.70), ("mPFC", 0.70),
        ("TPJ", 0.65), ("vmPFC", 0.60), ("aI", 0.50),
        ("amygdala", 0.20),
    ],
    nt_drives={"dopamine": 0.7, "oxytocin": 0.6, "serotonin": 0.4,
               "endorphins": 0.4},
    oscillation_signature={"delta": 0.05, "theta": 0.15, "alpha": 0.32,
                            "beta": 0.27, "gamma": 0.21},
    description="Vicarious reward (NAcc) for a loved one's joy. "
                "TPJ perspective + oxytocin + mesolimbic dopamine.",
))

_ec(EmotionCircuit(
    name="Opia",
    region_activations=[
        ("amygdala", 0.65), ("aI", 0.70), ("mPFC", 0.60),
        ("OFC", 0.55), ("TPJ", 0.65), ("fusiform", 0.75),
        ("locus_coeruleus", 0.55),
    ],
    nt_drives={"norepinephrine": 0.5, "oxytocin": 0.3, "dopamine": 0.2,
               "cortisol": 0.2},
    oscillation_signature={"delta": 0.07, "theta": 0.22, "alpha": 0.28,
                            "beta": 0.32, "gamma": 0.11},
    description="Fusiform face area + amygdala mutual gaze circuit. "
                "aI felt vulnerability. TPJ other-mind awareness. NE arousal.",
))

# ── COGNITIVE EMOTIONS ────────────────────────────────────────────────────────

_ec(EmotionCircuit(
    name="Aporia",
    region_activations=[
        ("dACC", 0.70), ("dlPFC", 0.65), ("LPFC", 0.65),
        ("aI", 0.55), ("hippocampus", 0.50), ("mPFC", 0.55),
        ("NAcc", 0.30),
    ],
    nt_drives={"dopamine": -0.1, "norepinephrine": 0.3, "glutamate": 0.3,
               "acetylcholine": 0.3},
    oscillation_signature={"delta": 0.08, "theta": 0.28, "alpha": 0.33,
                            "beta": 0.24, "gamma": 0.07},
    description="dACC conflict signal sustained without resolution. "
                "Genuine impasse — not confusion but honest confrontation with the limit.",
))

_ec(EmotionCircuit(
    name="Eureka",
    region_activations=[
        ("NAcc", 0.85), ("VTA", 0.85), ("hippocampus", 0.75),
        ("dlPFC", 0.70), ("mPFC", 0.70), ("claustrum", 0.80),
        ("locus_coeruleus", 0.70), ("thalamus", 0.65),
    ],
    nt_drives={"dopamine": 0.9, "norepinephrine": 0.7, "acetylcholine": 0.5,
               "glutamate": 0.6, "endorphins": 0.3},
    oscillation_signature={"delta": 0.04, "theta": 0.12, "alpha": 0.15,
                            "beta": 0.25, "gamma": 0.44},
    description="Jung-Beeman et al.: right anterior temporal gamma burst at insight. "
                "NAcc reward for resolved pattern. Claustrum binding suddenly coherent.",
))

_ec(EmotionCircuit(
    name="Cognitive Dissonance",
    region_activations=[
        ("dACC", 0.80), ("dlPFC", 0.70), ("LPFC", 0.65),
        ("amygdala", 0.55), ("aI", 0.60), ("mPFC", 0.60),
        ("NAcc", 0.25),
    ],
    nt_drives={"norepinephrine": 0.5, "glutamate": 0.5, "dopamine": -0.2,
               "gaba": -0.2, "cortisol": 0.3},
    oscillation_signature={"delta": 0.07, "theta": 0.20, "alpha": 0.22,
                            "beta": 0.38, "gamma": 0.13},
    description="Festinger: dACC detects contradiction as error signal. "
                "LPFC tries to resolve. Sustained beta tension, dopamine withdraw.",
))

_ec(EmotionCircuit(
    name="Epistemic Curiosity",
    region_activations=[
        ("dlPFC", 0.70), ("NAcc", 0.65), ("VTA", 0.60),
        ("aI", 0.55), ("hippocampus", 0.60), ("dACC", 0.50),
        ("locus_coeruleus", 0.55), ("temporal_pole", 0.50),
    ],
    nt_drives={"dopamine": 0.6, "norepinephrine": 0.4, "acetylcholine": 0.6,
               "glutamate": 0.4},
    oscillation_signature={"delta": 0.05, "theta": 0.25, "alpha": 0.28,
                            "beta": 0.28, "gamma": 0.14},
    description="Kang et al.: information gap activates caudate + SNc dopamine. "
                "ACh learning mode. Driven approach toward knowledge.",
))

_ec(EmotionCircuit(
    name="Sonder",
    region_activations=[
        ("mPFC", 0.70), ("TPJ", 0.75), ("temporal_pole", 0.70),
        ("PCC", 0.65), ("precuneus", 0.65), ("angular_gyrus", 0.60),
        ("NAcc", 0.40),
    ],
    nt_drives={"serotonin": 0.3, "oxytocin": 0.3, "dopamine": 0.2,
               "anandamide": 0.3},
    oscillation_signature={"delta": 0.08, "theta": 0.25, "alpha": 0.40,
                            "beta": 0.18, "gamma": 0.09},
    description="Theory of mind network at maximum extension — every stranger "
                "as full inner world. TPJ + temporal pole + DMN. Quiet, vast.",
))

_ec(EmotionCircuit(
    name="Anagnorisis",
    region_activations=[
        ("mPFC", 0.80), ("hippocampus", 0.80), ("dlPFC", 0.70),
        ("NAcc", 0.70), ("amygdala", 0.60), ("claustrum", 0.75),
        ("aI", 0.65), ("locus_coeruleus", 0.65),
        ("PCC", 0.65), ("precuneus", 0.60),
    ],
    nt_drives={"dopamine": 0.6, "norepinephrine": 0.6, "cortisol": 0.3,
               "glutamate": 0.5, "serotonin": 0.2},
    oscillation_signature={"delta": 0.05, "theta": 0.18, "alpha": 0.20,
                            "beta": 0.25, "gamma": 0.32},
    description="Autobiographical memory (hippocampus+PCC) reorganizing under "
                "new self-concept (mPFC). Claustrum binding new narrative. "
                "LC/NE attention capture. The moment the story changes.",
))

# Additional circuits for completeness
_ec(EmotionCircuit(
    name="Pensiveness",
    region_activations=[
        ("mPFC", 0.60), ("PCC", 0.65), ("hippocampus", 0.60),
        ("sgACC", 0.45), ("precuneus", 0.55),
    ],
    nt_drives={"serotonin": 0.1, "acetylcholine": 0.3},
    oscillation_signature={"delta": 0.12, "theta": 0.33, "alpha": 0.32,
                            "beta": 0.15, "gamma": 0.08},
    description="Mild DMN rumination. Low arousal, autobiographical drift.",
))

_ec(EmotionCircuit(
    name="Nostalgia",
    region_activations=[
        ("hippocampus", 0.75), ("mPFC", 0.65), ("PCC", 0.65),
        ("temporal_pole", 0.65), ("NAcc", 0.50), ("amygdala", 0.40),
        ("sgACC", 0.40),
    ],
    nt_drives={"dopamine": 0.2, "serotonin": 0.1, "oxytocin": 0.3,
               "acetylcholine": 0.4, "serotonin": 0.2},
    oscillation_signature={"delta": 0.12, "theta": 0.32, "alpha": 0.30,
                            "beta": 0.17, "gamma": 0.09},
    description="Hippocampal memory replay with positive valence reinterpretation. "
                "NAcc mild reward. Temporal pole social meaning.",
))

_ec(EmotionCircuit(
    name="Longing",
    region_activations=[
        ("hippocampus", 0.70), ("sgACC", 0.60), ("mPFC", 0.60),
        ("aI", 0.55), ("NAcc", 0.40), ("amygdala", 0.45),
    ],
    nt_drives={"serotonin": -0.2, "dopamine": 0.1, "oxytocin": 0.2,
               "substance_P": 0.2},
    oscillation_signature={"delta": 0.15, "theta": 0.35, "alpha": 0.28,
                            "beta": 0.14, "gamma": 0.08},
    description="Absent-object desire. Hippocampal absence signal + gentle grief.",
))


def get_circuit(emotion_name: str) -> EmotionCircuit:
    return EMOTION_CIRCUITS.get(emotion_name.lower())


def list_emotions() -> list:
    return sorted(EMOTION_CIRCUITS.keys())
