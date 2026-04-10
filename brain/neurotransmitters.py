"""
neurotransmitters.py — Neurotransmitter Systems

12 major systems modeled with:
  - Source nuclei and projection targets
  - Synthesis/reuptake/degradation dynamics
  - Effect on emotion valence and arousal
  - Receptor subtypes and their roles
  - How levels modulate the Wilson-Cowan parameters

Each system has a current_level [0.0, 1.0] representing
relative activity (0.5 = baseline).
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class NeurotransmitterSystem:
    name: str
    abbrev: str
    source_regions: List[str]      # region abbreviations
    projection_regions: List[str]  # primary targets
    valence_effect: float          # per unit above baseline (+/-)
    arousal_effect: float          # per unit above baseline (+/-)
    synthesis_rate: float          # per ms (how fast it builds up)
    reuptake_rate: float           # per ms (how fast it clears)
    baseline: float                # resting level [0,1]
    current_level: float = 0.5    # live level
    receptor_types: List[str] = field(default_factory=list)
    description: str = ""

    def tick(self, dt_ms: float, drive: float = 0.0):
        """
        Update level for one timestep.
        drive: external activation [-1, 1] from emotion circuits.

        NT-specific dynamics:
        - Fast synaptic NTs (dopamine, NE, glutamate): wide swing, fast decay
        - Slow hormonal NTs (cortisol, CRF): narrow swing, very slow decay
        - Peptides (oxytocin, endorphins): medium swing, medium decay
        """
        # Wider drive range — cortisol/CRF are hormonal (slow, narrow)
        # dopamine/NE are synaptic (fast, wide swing)
        if self.abbrev in ("cortisol", "CRF"):
            # Hormonal: slow timescale, narrower acute swing
            target = self.baseline + drive * 0.35
            effective_reuptake = self.reuptake_rate * 0.3  # much slower clearance
        elif self.abbrev in ("oxytocin", "endorphins", "substance_P"):
            # Peptide: medium timescale
            target = self.baseline + drive * 0.55
            effective_reuptake = self.reuptake_rate * 0.7
        else:
            # Synaptic (dopamine, serotonin, NE, GABA, glutamate, ACh, anandamide):
            # faster and wider swing
            target = self.baseline + drive * 0.65
            effective_reuptake = self.reuptake_rate

        target = max(0.0, min(1.0, target))

        # First-order exponential approach to target.
        # synthesis_rate is already encoded in how fast target is set —
        # the +synthesis*drive term was a double-application causing overshoot.
        decay = math.exp(-effective_reuptake * dt_ms)
        self.current_level += (target - self.current_level) * (1 - decay)
        self.current_level = max(0.0, min(1.0, self.current_level))

    @property
    def valence_contribution(self) -> float:
        delta = self.current_level - self.baseline
        return delta * self.valence_effect

    @property
    def arousal_contribution(self) -> float:
        delta = self.current_level - self.baseline
        return delta * self.arousal_effect


NT_SYSTEMS: Dict[str, NeurotransmitterSystem] = {}


def _nt(system: NeurotransmitterSystem) -> NeurotransmitterSystem:
    NT_SYSTEMS[system.abbrev] = system
    return system


_nt(NeurotransmitterSystem(
    name="Dopamine",
    abbrev="dopamine",
    source_regions=["VTA", "SN"],
    projection_regions=["NAcc", "striatum", "dlPFC", "mPFC", "amygdala", "hippocampus"],
    valence_effect=1.6,    # high DA = strong positive valence
    arousal_effect=0.8,
    synthesis_rate=0.003,
    reuptake_rate=0.08,
    baseline=0.5,
    current_level=0.5,
    receptor_types=["D1 (excitatory, reward)", "D2 (inhibitory, motor)",
                    "D3 (limbic)", "D4 (prefrontal)"],
    description="The anticipation and reward molecule. Peak at reward prediction error. "
                "Powers joy, meraki, flow, compersion, collective effervescence, "
                "eureka, love-bonding. Deficit: anhedonia, weltschmerz.",
))

_nt(NeurotransmitterSystem(
    name="Serotonin",
    abbrev="serotonin",
    source_regions=["raphe"],
    projection_regions=["vmPFC", "amygdala", "hippocampus", "OFC", "striatum", "cortex_wide"],
    valence_effect=0.9,    # moderate positive when high
    arousal_effect=-0.4,   # calming
    synthesis_rate=0.002,
    reuptake_rate=0.04,
    baseline=0.5,
    current_level=0.5,
    receptor_types=["5-HT1A (autoreceptor, anxiolytic)", "5-HT2A (psychedelic target)",
                    "5-HT3 (nausea, vagal)", "5-HT4 (memory)"],
    description="Mood floor. Wabi-sabi contentment, mono no aware acceptance, serenity. "
                "Low: dysphoria, rumination, grief amplification, OCD. "
                "High: contentment, perspective, gentle acceptance.",
))

_nt(NeurotransmitterSystem(
    name="Norepinephrine",
    abbrev="norepinephrine",
    source_regions=["locus_coeruleus"],
    projection_regions=["amygdala", "hippocampus", "dlPFC", "cortex_wide", "cerebellum"],
    valence_effect=0.3,    # slight positive in safe context, negative in threat
    arousal_effect=1.2,    # strong arousal effect
    synthesis_rate=0.004,
    reuptake_rate=0.06,
    baseline=0.45,
    current_level=0.45,
    receptor_types=["α1 (excitatory, vigilance)", "α2 (autoreceptor, brake)",
                    "β1 (cardiac, energy mobilization)"],
    description="Arousal broadcaster. Phasic release = surprise, frisson, torschlusspanik. "
                "Tonic high = hypervigilance, anxiety. Low = lethargy, depression. "
                "Mediates attention capture, wonder (safe high NE), fear (unsafe high NE).",
))

_nt(NeurotransmitterSystem(
    name="GABA",
    abbrev="gaba",
    source_regions=["cortex_wide", "BG", "cerebellum", "CeA"],
    projection_regions=["cortex_wide", "amygdala", "thalamus"],
    valence_effect=0.4,    # reduces anxiety = mild positive
    arousal_effect=-1.0,   # strong inhibitory / calming
    synthesis_rate=0.005,
    reuptake_rate=0.10,
    baseline=0.55,
    current_level=0.55,
    receptor_types=["GABA-A (ionotropic, fast, benzodiazepine site)",
                    "GABA-B (metabotropic, baclofen)"],
    description="The brain's main brake. vmPFC GABA suppresses amygdala (fear extinction). "
                "High: serenity, waldeinsamkeit calm, wabi-sabi quiet. "
                "Low: anxiety, panic, seizure risk.",
))

_nt(NeurotransmitterSystem(
    name="Glutamate",
    abbrev="glutamate",
    source_regions=["cortex_wide", "hippocampus", "thalamus"],
    projection_regions=["cortex_wide", "striatum", "amygdala"],
    valence_effect=0.2,
    arousal_effect=0.6,
    synthesis_rate=0.006,
    reuptake_rate=0.12,
    baseline=0.50,
    current_level=0.50,
    receptor_types=["AMPA (fast excitation)", "NMDA (LTP, memory, ketamine target)",
                    "mGluR (metabotropic modulation)"],
    description="The main excitatory driver. Fuels learning (LTP via NMDA), "
                "eureka moments, epistemic curiosity, cognitive dissonance tension. "
                "Excess: excitotoxicity. Glutamate is what makes things loud in the brain.",
))

_nt(NeurotransmitterSystem(
    name="Acetylcholine",
    abbrev="acetylcholine",
    source_regions=["NBM", "septal"],
    projection_regions=["hippocampus", "cortex_wide", "amygdala", "thalamus"],
    valence_effect=0.5,
    arousal_effect=0.7,
    synthesis_rate=0.003,
    reuptake_rate=0.05,
    baseline=0.45,
    current_level=0.45,
    receptor_types=["Muscarinic M1 (memory)", "Muscarinic M2 (cardiac, autoreceptor)",
                    "Nicotinic (fast, attention)"],
    description="The attention and memory molecule. Flow states, deep focus, epistemic curiosity. "
                "High during REM (vivid dreaming). Powers learning mode, curiosity, "
                "aporia resolution attempts, sonder-like mentalizing.",
))

_nt(NeurotransmitterSystem(
    name="Oxytocin",
    abbrev="oxytocin",
    source_regions=["PVN", "hypothalamus"],
    projection_regions=["amygdala", "NAcc", "hippocampus", "septal", "cortex_wide"],
    valence_effect=1.2,    # strong positive in social context
    arousal_effect=-0.2,   # slightly calming
    synthesis_rate=0.001,
    reuptake_rate=0.02,
    baseline=0.35,
    current_level=0.35,
    receptor_types=["OT receptor (G-protein coupled, widespread)"],
    description="The bonding molecule. Love, ubuntu (I am because we are), kama muta, "
                "compersion, mamihlapinatapai (shared wordless desire), "
                "collective effervescence. Released by touch, eye contact, shared music, "
                "social synchrony. Reduces amygdala fear reactivity.",
))

_nt(NeurotransmitterSystem(
    name="Endorphins",
    abbrev="endorphins",
    source_regions=["PAG", "hypothalamus", "pituitary"],
    projection_regions=["NAcc", "amygdala", "PAG", "thalamus", "cortex_wide"],
    valence_effect=1.4,    # very positive
    arousal_effect=-0.3,   # slightly calming/anesthetic
    synthesis_rate=0.001,
    reuptake_rate=0.015,
    baseline=0.30,
    current_level=0.30,
    receptor_types=["μ-opioid (pleasure, analgesia)", "κ-opioid (dysphoria, psychotomimetic)",
                    "δ-opioid (antidepressant-like)"],
    description="Endogenous opioids. Released by exercise, laughter, music (frisson peak), "
                "collective effervescence, skin contact (skin hunger relief), "
                "social bonding. Produce warm euphoria, pain relief, courage.",
))

_nt(NeurotransmitterSystem(
    name="Cortisol",
    abbrev="cortisol",
    source_regions=["pituitary", "hypothalamus"],
    projection_regions=["hippocampus", "amygdala", "dlPFC", "cortex_wide"],
    valence_effect=-1.0,   # stress, negative
    arousal_effect=0.6,    # mobilizes energy
    synthesis_rate=0.0005,
    reuptake_rate=0.008,
    baseline=0.30,
    current_level=0.30,
    receptor_types=["GR (glucocorticoid receptor, slow genomic effects)",
                    "MR (mineralocorticoid, hippocampal neuroprotection at low levels)"],
    description="The stress hormone. Acute spike = helpful mobilization. "
                "Chronic high = hippocampal atrophy, amygdala hyperreactivity, depression. "
                "Substrates: weltschmerz, empathic distress, torschlusspanik, grief, shame.",
))

_nt(NeurotransmitterSystem(
    name="Anandamide (Endocannabinoid)",
    abbrev="anandamide",
    source_regions=["cortex_wide", "hippocampus", "cerebellum"],
    projection_regions=["cortex_wide", "NAcc", "amygdala", "hippocampus"],
    valence_effect=1.0,
    arousal_effect=-0.5,
    synthesis_rate=0.002,
    reuptake_rate=0.03,
    baseline=0.35,
    current_level=0.35,
    receptor_types=["CB1 (central, psychoactive)", "CB2 (peripheral, immune)"],
    description="The bliss molecule. Produced during exercise (runner's high with endorphins), "
                "creative flow, waldeinsamkeit, wabi-sabi appreciation. "
                "Retrograde synapse modulator — dampens over-excitement. "
                "Produces mild euphoria, reduced anxiety, time distortion.",
))

_nt(NeurotransmitterSystem(
    name="Substance P / Neuropeptide Y",
    abbrev="substance_P",
    source_regions=["CeA", "spinal_cord", "brainstem"],
    projection_regions=["amygdala", "hypothalamus", "PAG"],
    valence_effect=-0.6,
    arousal_effect=0.4,
    synthesis_rate=0.001,
    reuptake_rate=0.01,
    baseline=0.30,
    current_level=0.30,
    receptor_types=["NK1 receptor (pain, stress)"],
    description="Pain and stress neuropeptide. Elevated in grief, shame, empathic distress. "
                "Substance P antagonists are experimental antidepressants. "
                "NPY (co-packaged) has anxiolytic effects.",
))

_nt(NeurotransmitterSystem(
    name="CRF (Corticotropin-Releasing Factor)",
    abbrev="CRF",
    source_regions=["PVN", "CeA", "BNST"],
    projection_regions=["pituitary", "locus_coeruleus", "amygdala", "hippocampus"],
    valence_effect=-0.8,
    arousal_effect=0.7,
    synthesis_rate=0.001,
    reuptake_rate=0.015,
    baseline=0.25,
    current_level=0.25,
    receptor_types=["CRF-R1 (stress, anxiety)", "CRF-R2 (stress buffering)"],
    description="Stress cascade initiator. Triggers cortisol release via HPA axis. "
                "Elevated in anxiety disorders, PTSD, weltschmerz, torschlusspanik. "
                "CRF in amygdala → sustained anxiety (BNST pathway).",
))


def compute_net_valence_arousal(nt_levels: Dict[str, float] = None) -> Tuple[float, float]:
    """
    Sum neurotransmitter contributions to get net valence and arousal.
    Uses current NT levels if nt_levels not provided.
    """
    net_valence = 0.0
    net_arousal = 0.0
    for nt in NT_SYSTEMS.values():
        level = nt_levels.get(nt.abbrev, nt.current_level) if nt_levels else nt.current_level
        delta = level - nt.baseline
        net_valence += delta * nt.valence_effect
        net_arousal += delta * nt.arousal_effect
    # Normalize to [-1, 1] range
    net_valence = max(-1.0, min(1.0, net_valence * 0.3))
    net_arousal = max(0.0, min(1.0, 0.5 + net_arousal * 0.2))
    return net_valence, net_arousal


def reset_to_baseline():
    for nt in NT_SYSTEMS.values():
        nt.current_level = nt.baseline


def get_nt_state() -> Dict[str, float]:
    return {abbrev: nt.current_level for abbrev, nt in NT_SYSTEMS.items()}
