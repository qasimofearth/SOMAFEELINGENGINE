"""
simulator.py — Wilson-Cowan Neural Population Dynamics Engine

Models each brain region as coupled excitatory/inhibitory populations.

Wilson-Cowan Equations:
  τ_e * dE/dt = -E + (1 - r_e*E) * S_e(c_ee*E - c_ei*I + P + NT_mod)
  τ_i * dI/dt = -I + (1 - r_i*I) * S_i(c_ie*E - c_ii*I + Q)

Kuramoto phase coupling with K=2.5 produces genuine inter-regional
synchrony — regions with similar natural frequencies lock phase,
creating real oscillatory dynamics rather than assigned band labels.

Drive decay: emotion drives injected via set_region_drive() decay
exponentially (τ configurable), so emotional states fade naturally
rather than being slammed on/off.

Emergent frequency: dominant oscillation frequency is derived from
activity-weighted mean of locked-phase regions — maps to solfeggio
via octave harmonic relationship.

Runs continuously in a background thread (10ms steps).
"""

import math
import cmath
import time
import random
import threading
from collections import deque
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from .regions import BRAIN_REGIONS, BrainRegion
from .neurotransmitters import NT_SYSTEMS, compute_net_valence_arousal


# ── SOLFEGGIO FREQUENCIES ─────────────────────────────────────────────────────
# Sacred frequency series — emergent brain oscillation maps to nearest via octave
SOLFEGGIO_HZ = [174.0, 285.0, 396.0, 417.0, 528.0, 639.0, 741.0, 852.0, 963.0]

# EEG band center frequencies (Hz)
BAND_CENTER_HZ = {
    "delta": 2.5,
    "theta": 6.0,
    "alpha": 10.0,
    "beta": 20.0,
    "gamma": 40.0,
}

def eeg_to_solfeggio(eeg_hz: float) -> float:
    """
    Map an EEG frequency to its corresponding solfeggio.
    Each EEG band has a harmonic character that corresponds to
    a solfeggio frequency — the mapping follows the quality of
    each oscillatory state, not strict octave arithmetic.

    delta  (0.5–4Hz)  → 174Hz  — deep foundation, below cognition
    theta  (4–8Hz)    → 396Hz  — limbic, emotional, memory
    alpha  (8–13Hz)   → 528Hz  — resting awareness, integration
    low β  (13–20Hz)  → 639Hz  — engaged, social, connected
    high β (20–30Hz)  → 741Hz  — problem-solving, expression
    gamma  (30+Hz)    → 852Hz  — binding, conscious awareness
    """
    if eeg_hz < 0.5:   return 174.0
    elif eeg_hz < 4:   return 174.0
    elif eeg_hz < 8:   return 396.0
    elif eeg_hz < 13:  return 528.0
    elif eeg_hz < 20:  return 639.0
    elif eeg_hz < 30:  return 741.0
    else:              return 852.0


# ── CROSS-FREQUENCY COUPLING ──────────────────────────────────────────────────
# The single `sync_order` scalar collapses all inter-regional relationship into
# one number. The real neural code for binding / conscious integration is richer:
#   · Phase-amplitude coupling (PAC): slow-band phase modulates fast-band amplitude
#     (theta-gamma nesting is the canonical binding / working-memory signature).
#   · Phase-locking value (PLV): sustained phase synchrony between two circuits.
# We compute both over a rolling window of the live Kuramoto phases.

_BAND_ORDER = {"delta": 0, "theta": 1, "alpha": 2, "beta": 3, "gamma": 4}

# PAC band-pairs (low phase → high amplitude). theta-gamma is the headline.
PAC_PAIRS: List[Tuple[str, str]] = [("theta", "gamma"), ("theta", "beta"), ("alpha", "gamma")]

# PLV circuits — anatomically meaningful pairs whose synchrony varies by emotion.
PLV_PAIRS: List[Tuple[str, str]] = [
    ("amygdala", "vmPFC"),      # top-down fear regulation
    ("dACC", "aI"),             # salience-network integration
    ("PCC", "mPFC"),            # default-mode (self / rumination)
    ("VTA", "NAcc"),            # reward drive
    ("hippocampus", "mPFC"),    # memory ↔ emotion
    ("amygdala", "PAG"),        # threat → defense
]
# Ordered, de-duplicated region list we snapshot each sample for PLV.
_PLV_REGIONS: List[str] = list(dict.fromkeys([r for pair in PLV_PAIRS for r in pair]))
_PLV_IDX = {r: i for i, r in enumerate(_PLV_REGIONS)}


# ── SIGMOID ───────────────────────────────────────────────────────────────────

def sigmoid(x: float) -> float:
    x = max(-20.0, min(20.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def sigmoid_gain(x: float, gain: float = 4.0, threshold: float = 0.5) -> float:
    return sigmoid(gain * (x - threshold))


# ── POPULATION STATE ──────────────────────────────────────────────────────────

@dataclass
class PopulationState:
    """Excitatory/inhibitory state for one brain region."""
    abbrev: str
    E: float = 0.1          # excitatory activity [0,1]
    I: float = 0.05         # inhibitory activity [0,1]
    phase: float = 0.0      # Kuramoto oscillator phase (radians)
    omega: float = 0.0      # natural frequency (rad/ms) — set from region oscillation
    ext_input: float = 0.0  # external drive (decays over time)
    history_E: List[float] = field(default_factory=list)

    def get_activity(self) -> float:
        """Net output firing rate (weighted E-I)."""
        return max(0.0, self.E - 0.3 * self.I)

    def record(self):
        self.history_E.append(round(self.E, 4))
        if len(self.history_E) > 500:
            self.history_E.pop(0)

    def dominant_band(self) -> str:
        """Estimate dominant EEG band from oscillator frequency."""
        hz = self.omega * 1000.0 / (2 * math.pi) if self.omega > 0 else 10.0
        if hz < 4:   return "delta"
        elif hz < 8:  return "theta"
        elif hz < 13: return "alpha"
        elif hz < 30: return "beta"
        else:         return "gamma"


# ── CONNECTIVITY ──────────────────────────────────────────────────────────────
# Sparse Kuramoto coupling graph — built once at module load from structural
# weights. Phase coupling follows anatomy: only connected regions synchronize.
# This is O(E) per step instead of O(N²) — ~150x fewer sin() calls.
# Coupling is bidirectional: even unidirectional anatomical projections
# produce mutual phase influence through local recurrent circuits.

def _build_kuramoto_graph(weights: dict) -> Dict[str, List[Tuple[str, float]]]:
    graph: Dict[str, List[Tuple[str, float]]] = {}
    seen = set()
    for (src, tgt), w in weights.items():
        pair = (min(src, tgt), max(src, tgt))
        if pair in seen:
            continue
        seen.add(pair)
        graph.setdefault(src, []).append((tgt, w))
        graph.setdefault(tgt, []).append((src, w))
    return graph


STRUCTURAL_WEIGHTS: Dict[Tuple[str, str], float] = {
    # Amygdala circuits
    ("amygdala", "vmPFC"):    0.35,
    ("amygdala", "hippocampus"): 0.55,
    ("amygdala", "hypothalamus"): 0.60,
    ("amygdala", "PAG"):      0.50,
    ("amygdala", "dACC"):     0.45,
    ("amygdala", "aI"):       0.50,
    ("amygdala", "VTA"):      0.35,
    ("amygdala", "locus_coeruleus"): 0.40,
    ("vmPFC", "amygdala"):    0.50,
    ("dlPFC", "amygdala"):    0.30,
    # Reward circuit
    ("VTA", "NAcc"):          0.80,
    ("VTA", "mPFC"):          0.55,
    ("VTA", "dlPFC"):         0.40,
    ("VTA", "amygdala"):      0.35,
    ("NAcc", "VTA"):          0.40,
    ("NAcc", "GPe"):          0.60,
    # Hippocampus
    ("hippocampus", "entorhinal"):  0.70,
    ("hippocampus", "vmPFC"):       0.50,
    ("hippocampus", "PCC"):         0.45,
    ("hippocampus", "NAcc"):        0.35,
    ("entorhinal", "hippocampus"):  0.70,
    # PFC internal
    ("dlPFC", "vmPFC"):       0.40,
    ("dlPFC", "dACC"):        0.50,
    ("dlPFC", "PPC"):         0.50,
    ("mPFC", "PCC"):          0.60,
    ("mPFC", "vmPFC"):        0.55,
    # Default Mode Network
    ("PCC", "mPFC"):          0.65,
    ("PCC", "hippocampus"):   0.50,
    ("PCC", "precuneus"):     0.60,
    ("precuneus", "PCC"):     0.60,
    ("precuneus", "mPFC"):    0.45,
    # Salience Network
    ("dACC", "aI"):           0.60,
    ("aI", "dACC"):           0.55,
    ("dACC", "amygdala"):     0.45,
    # Thalamus relays
    ("thalamus", "dlPFC"):    0.45,
    ("thalamus", "amygdala"): 0.35,
    ("thalamus", "S1"):       0.65,
    ("thalamus", "visual_cortex"): 0.70,
    ("thalamus", "auditory_cortex"): 0.65,
    # Neuromodulators → targets
    ("raphe", "vmPFC"):       0.50,
    ("raphe", "amygdala"):    0.45,
    ("locus_coeruleus", "amygdala"): 0.55,
    ("locus_coeruleus", "dlPFC"):    0.40,
    # Basal ganglia loop
    ("striatum", "GPe"):      0.60,
    ("GPe", "GPi"):           0.55,
    ("GPi", "thalamus"):      0.50,
    ("STN", "GPi"):           0.50,
    # Cerebellum
    ("cerebellum", "thalamus"):     0.55,
    ("cerebellum", "M1"):           0.50,
    # Insula
    ("aI", "vmPFC"):          0.40,
    ("aI", "amygdala"):       0.45,
    ("pI", "aI"):             0.60,
    ("S1", "aI"):             0.40,
    # Social / bonding
    ("PVN", "NAcc"):          0.35,
    ("hypothalamus", "amygdala"): 0.45,
    ("septal", "hippocampus"):    0.55,
    # Other
    ("habenula", "VTA"):      0.50,
    ("habenula", "raphe"):    0.45,
    ("BNST", "amygdala"):     0.40,
    ("OFC", "amygdala"):      0.45,
    ("temporal_pole", "amygdala"): 0.40,
}

# Built once at import — used by all BrainSimulator instances
_KURAMOTO_GRAPH: Dict[str, List[Tuple[str, float]]] = _build_kuramoto_graph(STRUCTURAL_WEIGHTS)


# ── SIMULATOR ─────────────────────────────────────────────────────────────────

class BrainSimulator:
    """
    Wilson-Cowan simulation across all brain regions.

    Runs continuously via external thread. Emotion drives are injected
    and decay exponentially. Kuramoto coupling K=2.5 produces genuine
    phase locking — regions with similar natural frequencies synchronize,
    creating real oscillatory dynamics.
    """

    def __init__(self):
        self.states: Dict[str, PopulationState] = {}
        self.dt_ms = 1.0
        self.t_ms = 0.0
        self.sync_order = 0.0
        self._lock = threading.Lock()

        # Wilson-Cowan parameters
        self.c_ee = 1.5
        self.c_ei = 2.0
        self.c_ie = 0.8
        self.c_ii = 0.8
        self.r_e  = 0.20
        self.r_i  = 0.20

        # Strong Kuramoto coupling — produces genuine phase locking
        # K=2.5: regions with similar omega will synchronize within ~500ms
        self.K_kuramoto = 2.5
        # Phase noise (rad/ms). Real cortex is noisy — deterministic coupling locks
        # perfectly (PLV≡1), which erases all relational structure. A small stochastic
        # term makes locking GRADED: strongly-coupled circuits lock more than weak ones,
        # so phase-locking becomes an informative, state-dependent signal.
        self.phase_noise = 0.06

        # Drive decay time constant (ms) — emotion drives fade over ~3 seconds
        self.drive_tau_ms = 3000.0

        # Initialize regions with real oscillation frequencies
        for abbrev, region in BRAIN_REGIONS.items():
            peak_band = max(region.oscillation_rest, key=region.oscillation_rest.get)
            omega = self._band_to_omega(peak_band)
            base_E = 0.08 + region.ei_ratio * 0.18 + random.gauss(0, 0.02)
            base_I = 0.04 + (1 - region.ei_ratio) * 0.10 + random.gauss(0, 0.01)
            self.states[abbrev] = PopulationState(
                abbrev=abbrev,
                E=max(0.0, min(0.5, base_E)),
                I=max(0.0, min(0.3, base_I)),
                phase=random.uniform(0, 2 * math.pi),
                omega=omega,
            )

        # ── coupling analyzer ──
        # omega is fixed at init, so each region's band membership is static — cache it.
        self._region_band = {ab: st.dominant_band() for ab, st in self.states.items()}

        # ── theta→gamma phase-amplitude coupling (GENERATIVE) ──
        # The canonical binding mechanism: septo-hippocampal THETA rhythmically gates
        # cortical GAMMA excitability, so gamma amplitude nests inside theta phase.
        # We anchor a few regions to theta and a few cortical regions to gamma so the
        # nesting is real and biological, not an artifact of random band assignment.
        self.K_pac = 1.3
        _THETA_SRC = ["hippocampus", "entorhinal", "septal"]
        _GAMMA_TGT = ["visual_cortex", "auditory_cortex", "dlPFC", "PPC", "S1", "aI", "mPFC"]
        for r in _THETA_SRC:
            if r in self.states:
                self.states[r].omega = self._band_to_omega("theta"); self._region_band[r] = "theta"
        for r in _GAMMA_TGT:
            if r in self.states:
                self.states[r].omega = self._band_to_omega("gamma"); self._region_band[r] = "gamma"
        self._theta_src = [r for r in _THETA_SRC if r in self.states]
        self._gamma_tgt_set = set(r for r in _GAMMA_TGT if r in self.states)

        self._coup_stride = 4          # sample every 4ms (~250Hz) — resolves gamma-band PAC
        self._coup_i = 0
        self._coup_buf = deque(maxlen=160)   # ~640ms window (≈4 theta cycles)

    def _band_to_omega(self, band: str) -> float:
        """
        Convert EEG band to angular frequency (rad/ms).
        Uses actual center frequency with small individual variation —
        this spread is what allows Kuramoto to produce partial rather
        than total synchrony, matching real brain dynamics.
        """
        hz = BAND_CENTER_HZ.get(band, 10.0)
        # ±15% individual variation so nearby-frequency regions form clusters
        hz *= (0.85 + random.uniform(0, 0.30))
        return 2 * math.pi * hz / 1000.0

    def _nt_modulation(self, region_abbrev: str) -> float:
        region = BRAIN_REGIONS.get(region_abbrev)
        if not region:
            return 0.0
        mod = 0.0
        nts = region.primary_nts
        if "dopamine" in nts:
            mod += (NT_SYSTEMS["dopamine"].current_level - 0.5) * 1.5
        if "norepinephrine" in nts:
            mod += (NT_SYSTEMS["norepinephrine"].current_level - 0.45) * 1.0
        if "serotonin" in nts:
            mod += (NT_SYSTEMS["serotonin"].current_level - 0.5) * 0.6
        if "gaba" in nts:
            mod -= (NT_SYSTEMS["gaba"].current_level - 0.55) * 1.2
        if "acetylcholine" in nts:
            mod += (NT_SYSTEMS["acetylcholine"].current_level - 0.45) * 0.8
        if "glutamate" in nts:
            mod += (NT_SYSTEMS["glutamate"].current_level - 0.5) * 0.7
        if "oxytocin" in nts:
            mod += (NT_SYSTEMS["oxytocin"].current_level - 0.35) * 0.9
        if "endorphins" in nts:
            mod += (NT_SYSTEMS["endorphins"].current_level - 0.30) * 0.8
        if "cortisol" in nts:
            mod -= (NT_SYSTEMS["cortisol"].current_level - 0.30) * 0.5
        return max(-1.2, min(1.2, mod * 0.45))

    def _inter_region_input(self, target: str) -> float:
        """
        Propagate activity through structural connectome.
        Scale 0.35 (up from 0.2) so connectivity actually matters —
        seeding one region can cascade through its projection targets.
        """
        total = 0.0
        for (src, tgt), weight in STRUCTURAL_WEIGHTS.items():
            if tgt == target and src in self.states:
                total += weight * self.states[src].get_activity()
        return total * 0.35

    def step(self, n_steps: int = 1):
        """Advance simulation by n_steps timesteps (each 1ms)."""
        with self._lock:
            for _ in range(n_steps):
                self._step_once()
                self.t_ms += self.dt_ms

    def _step_once(self):
        """Single Wilson-Cowan + Kuramoto timestep. Called under lock."""
        new_E: Dict[str, float] = {}
        new_I: Dict[str, float] = {}
        new_phase: Dict[str, float] = {}

        N = len(self.states)

        # ── theta gate: collective phase of the septo-hippocampal theta sources ──
        # A rhythmic 0..1 excitability window (once per theta cycle), scaled by how
        # strong theta actually is. Gamma targets get this added to their drive, so
        # gamma amplitude waxes and wanes with theta phase → real phase-amplitude coupling.
        theta_gate = 0.0
        if self._theta_src:
            tf = 0j
            for r in self._theta_src:
                st = self.states[r]
                tf += st.get_activity() * cmath.exp(1j * st.phase)
            if abs(tf) > 1e-9:
                theta_amp = abs(tf) / len(self._theta_src)
                # sharpened window → gamma bursts concentrate near theta peak (stronger nesting)
                theta_gate = ((0.5 + 0.5 * math.cos(cmath.phase(tf))) ** 1.6) * min(1.0, theta_amp * 2.4)

        for abbrev, state in self.states.items():
            region = BRAIN_REGIONS.get(abbrev)
            if not region:
                continue

            tau_e = region.tau_e_ms
            tau_i = region.tau_i_ms
            E, I = state.E, state.I

            ext   = state.ext_input
            inter = self._inter_region_input(abbrev)
            nt    = self._nt_modulation(abbrev)
            # theta rhythmically gates gamma-target excitability → nested gamma bursts
            pac_drive = self.K_pac * theta_gate if abbrev in self._gamma_tgt_set else 0.0

            dE = (-E + (1 - self.r_e * E) * sigmoid_gain(
                self.c_ee * E - self.c_ei * I + ext + inter + nt + pac_drive,
                gain=4.0, threshold=0.5
            )) / tau_e * self.dt_ms

            dI = (-I + (1 - self.r_i * I) * sigmoid_gain(
                self.c_ie * E - self.c_ii * I,
                gain=4.0, threshold=0.35
            )) / tau_i * self.dt_ms

            new_E[abbrev] = max(0.0, min(1.0, E + dE))
            new_I[abbrev] = max(0.0, min(1.0, I + dI))

            # Sparse Kuramoto: phase coupling only through structural connections.
            # O(degree) instead of O(N) — anatomically correct, ~150x fewer sin() calls.
            # Weights scale individual coupling strength; normalize by degree so
            # high-connectivity hubs don't dominate more than their degree warrants.
            neighbors = _KURAMOTO_GRAPH.get(abbrev, [])
            noise = random.gauss(0.0, self.phase_noise)
            if neighbors:
                sync_sum = sum(
                    w * math.sin(self.states[nb].phase - state.phase)
                    for nb, w in neighbors if nb in self.states
                )
                dphi = state.omega + (self.K_kuramoto / len(neighbors)) * sync_sum + noise
            else:
                # Isolated region: free-runs at natural frequency (still noisy)
                dphi = state.omega + noise
            new_phase[abbrev] = (state.phase + dphi * self.dt_ms) % (2 * math.pi)

        for abbrev in self.states:
            self.states[abbrev].E = new_E[abbrev]
            self.states[abbrev].I = new_I[abbrev]
            self.states[abbrev].phase = new_phase[abbrev]

        real = sum(math.cos(s.phase) for s in self.states.values()) / N
        imag = sum(math.sin(s.phase) for s in self.states.values()) / N
        self.sync_order = math.sqrt(real**2 + imag**2)

        # ── sample band-summed signals + PLV phases for the coupling analyzer ──
        self._coup_i += 1
        if self._coup_i % self._coup_stride == 0:
            bands = [0j, 0j, 0j, 0j, 0j]     # complex sum per band (for band phase)
            powers = [0.0, 0.0, 0.0, 0.0, 0.0]  # real activity envelope per band (for amplitude)
            for abbrev, st in self.states.items():
                a = st.get_activity()
                if a > 0.02:               # skip near-silent regions (also avoids the exp cost)
                    bi = _BAND_ORDER[self._region_band[abbrev]]
                    bands[bi] += a * cmath.exp(1j * st.phase)
                    powers[bi] += a
            phases = tuple(self.states[r].phase if r in self.states else 0.0 for r in _PLV_REGIONS)
            acts = tuple(self.states[r].get_activity() if r in self.states else 0.0 for r in _PLV_REGIONS)
            self._coup_buf.append((tuple(bands), tuple(powers), phases, self.sync_order, acts))

    def decay_drives(self, dt_ms: float):
        """
        Exponentially decay all external drives.
        Called by background thread every tick — emotional states
        fade naturally rather than being hard-reset.
        tau = 3000ms: drive halves every ~2 seconds, gone in ~10s.
        """
        if self.drive_tau_ms <= 0:
            return
        decay = math.exp(-dt_ms / self.drive_tau_ms)
        with self._lock:
            for state in self.states.values():
                state.ext_input *= decay

    def inject_drive(self, abbrev: str, drive: float, additive: bool = True):
        """
        Add or set a drive on a region.
        additive=True: accumulates (emotions layer on top of each other).
        additive=False: sets directly (for one-shot overrides).
        Capped at ±3.0 to prevent runaway.
        """
        with self._lock:
            if abbrev in self.states:
                if additive:
                    new = self.states[abbrev].ext_input + drive
                    self.states[abbrev].ext_input = max(-3.0, min(3.0, new))
                else:
                    self.states[abbrev].ext_input = max(-3.0, min(3.0, drive))

    def set_region_drive(self, abbrev: str, drive: float):
        """Legacy compatibility — sets drive directly."""
        self.inject_drive(abbrev, drive, additive=False)

    def clear_drives(self):
        """Reset all drives to zero."""
        with self._lock:
            for state in self.states.values():
                state.ext_input = 0.0

    def get_region_activity(self, abbrev: str) -> float:
        if abbrev in self.states:
            return self.states[abbrev].get_activity()
        return 0.0

    # ── EMERGENT FREQUENCY ────────────────────────────────────────────────────

    def get_dominant_frequency_hz(self) -> float:
        """
        Activity-weighted mean oscillation frequency of active regions.
        This is the emergent frequency of the brain state — not assigned
        from emotion label, derived from what the simulation is actually doing.
        """
        total_weight = 0.0
        weighted_omega = 0.0
        with self._lock:
            for state in self.states.values():
                activity = state.get_activity()
                if activity > 0.15:  # only regions actually firing
                    weighted_omega += state.omega * activity
                    total_weight += activity
        if total_weight < 0.01:
            return 10.0  # resting alpha
        mean_omega = weighted_omega / total_weight
        return mean_omega * 1000.0 / (2 * math.pi)

    def get_emergent_solfeggio(self) -> float:
        """
        Map emergent EEG frequency to nearest solfeggio via octave scaling.
        EEG (0.5–100Hz) and solfeggio (174–963Hz) share harmonic relationships —
        multiply up through octaves until in range, find nearest match.
        """
        eeg_hz = self.get_dominant_frequency_hz()
        return eeg_to_solfeggio(eeg_hz)

    def get_phase_coherence(self) -> dict:
        """
        Activity-weighted Kuramoto order parameter.
        With K=2.5, this will show genuine cluster formation:
        - order ~0.2: incoherent (many emotions competing)
        - order ~0.5: partial sync (one emotion dominant)
        - order ~0.8+: strong coherence (focused single state)
        """
        total_w = 0.0
        real = 0.0
        imag = 0.0
        with self._lock:
            for state in self.states.values():
                w = state.get_activity()
                real += math.cos(state.phase) * w
                imag += math.sin(state.phase) * w
                total_w += w
        if total_w < 0.01:
            return {"order": self.sync_order, "freq_hz": 10.0, "solfeggio_hz": 528.0}
        order = math.sqrt((real/total_w)**2 + (imag/total_w)**2)
        freq_hz = self.get_dominant_frequency_hz()
        return {
            "order": round(order, 4),
            "freq_hz": round(freq_hz, 2),
            "solfeggio_hz": eeg_to_solfeggio(freq_hz),
        }

    # ── CROSS-FREQUENCY COUPLING ──────────────────────────────────────────────

    @staticmethod
    def _modulation_index(phases: List[float], amps: List[float], nbins: int = 18) -> float:
        """
        Tort et al. (2010) modulation index — how strongly a low-band PHASE
        modulates a high-band AMPLITUDE. 0 = no coupling, 1 = maximal.
        KL-divergence of the mean-amplitude-per-phase-bin distribution from uniform.
        """
        if len(phases) < nbins * 2:
            return 0.0
        sums = [0.0] * nbins
        cnts = [0] * nbins
        twopi = 2 * math.pi
        for ph, a in zip(phases, amps):
            b = int((ph % twopi) / twopi * nbins) % nbins
            sums[b] += a
            cnts[b] += 1
        means = [sums[i] / cnts[i] if cnts[i] else 0.0 for i in range(nbins)]
        tot = sum(means)
        if tot <= 1e-9:
            return 0.0
        p = [m / tot for m in means]
        H = -sum(x * math.log(x) for x in p if x > 0)
        mi = (math.log(nbins) - H) / math.log(nbins)
        return max(0.0, min(1.0, mi))

    def get_coupling(self) -> dict:
        """
        Relational fingerprint of the current state — the structure the single
        `sync_order` scalar throws away:

          plv:           graded phase-locking per anatomical circuit (0..1)
          pac:           theta/alpha-phase → gamma-amplitude coupling (Tort MI)
          integration:   mean order over the window — how bound the network is
          metastability: std of the order parameter — dynamic flexibility
          binding:       criticality index — integrated AND flexible at once
                         (peaks at intermediate sync with high metastability; the
                          "edge of chaos" regime associated with conscious binding)
        """
        with self._lock:
            buf = list(self._coup_buf)
        n = len(buf)
        if n < 40:
            return {"pac": {}, "plv": {}, "binding": 0.0, "integration": 0.0,
                    "metastability": 0.0, "n": n}

        # PAC — low-band PHASE (from complex sum) modulating high-band AMPLITUDE
        # (real band power envelope, which the theta gate directly drives).
        pac = {}
        for lo, hi in PAC_PAIRS:
            li, hii = _BAND_ORDER[lo], _BAND_ORDER[hi]
            ph = [math.atan2(s[0][li].imag, s[0][li].real) for s in buf]
            am = [s[1][hii] for s in buf]
            pac[f"{lo}-{hi}"] = round(self._modulation_index(ph, am), 4)

        # Functional coupling per circuit = phase-locking GATED by co-activation.
        # (Raw PLV saturates — wired regions lock whether engaged or not. Weighting by
        #  how active both regions are is what makes fear vs reward look different.)
        coupling = {}
        for a, b in PLV_PAIRS:
            ia, ib = _PLV_IDX[a], _PLV_IDX[b]
            acc = 0j
            coact = 0.0
            for s in buf:
                acc += cmath.exp(1j * (s[2][ia] - s[2][ib]))
                coact += math.sqrt(max(0.0, s[4][ia]) * max(0.0, s[4][ib]))
            plv = abs(acc) / n
            coupling[f"{a}-{b}"] = round(plv * (coact / n), 4)   # engaged AND synchronized

        # order-parameter statistics over the window
        orders = [s[3] for s in buf]
        mean_ord = sum(orders) / n
        meta = math.sqrt(sum((o - mean_ord) ** 2 for o in orders) / n)
        integration = round(sum(coupling.values()), 4)   # total engaged-synchrony across circuits
        metastability = round(meta, 4)

        # binding / CLARITY: the real theta-gamma nesting (the binding code itself),
        # plus the edge-of-chaos flexibility term — high when the mind is genuinely
        # bound together AND alive, not locked rigid or scattered.
        pac_tg = pac.get("theta-gamma", 0.0)
        crit = 4.0 * mean_ord * (1.0 - mean_ord)
        binding = round(max(0.0, min(1.0, pac_tg * 16.0 + crit * (0.25 + 3.5 * meta))), 4)

        return {"pac": pac, "coupling": coupling, "binding": binding,
                "integration": integration, "metastability": metastability, "n": n}

    # ── SNAPSHOT / ANALYSIS ───────────────────────────────────────────────────

    def get_snapshot(self) -> Dict[str, dict]:
        with self._lock:
            return {
                abbrev: {
                    "E": round(state.E, 4),
                    "I": round(state.I, 4),
                    "activity": round(state.get_activity(), 4),
                    "phase": round(state.phase, 4),
                    "band": state.dominant_band(),
                    "drive": round(state.ext_input, 4),
                }
                for abbrev, state in self.states.items()
            }

    def get_active_regions(self, threshold: float = 0.35) -> List[Tuple[str, float]]:
        with self._lock:
            active = [
                (abbrev, state.get_activity())
                for abbrev, state in self.states.items()
                if state.get_activity() > threshold
            ]
        return sorted(active, key=lambda x: x[1], reverse=True)

    def compute_valence_arousal(self) -> Tuple[float, float]:
        def act(r): return self.get_region_activity(r)
        valence = (
            act("NAcc") * 1.5  + act("VTA") * 1.2  + act("vmPFC") * 0.8 +
            act("OFC") * 0.6   + act("septal") * 0.5 + act("raphe") * 0.4 -
            act("amygdala") * 1.0 - act("habenula") * 1.2 -
            act("sgACC") * 0.8 - act("CeA") * 0.6 - act("BNST") * 0.5
        )
        arousal = (
            act("locus_coeruleus") * 1.5 + act("dACC") * 1.0 +
            act("aI") * 0.8 + act("amygdala") * 0.7 + act("VTA") * 0.5 +
            act("BLA") * 0.6 + act("STN") * 0.4 -
            act("vmPFC") * 0.3 - act("raphe") * 0.3
        )
        nt_v, nt_a = compute_net_valence_arousal()
        valence = valence * 0.6 + nt_v * 0.4
        arousal = arousal * 0.6 + nt_a * 0.4
        valence = max(-1.0, min(1.0, valence * 0.45))
        arousal = max(0.0, min(1.0, 0.30 + arousal * 0.22))
        return round(valence, 3), round(arousal, 3)

    def get_oscillation_summary(self) -> Dict[str, float]:
        band_power = {"delta": 0.0, "theta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}
        total_weight = 0.0
        with self._lock:
            for state in self.states.values():
                activity = state.get_activity()
                if activity > 0.05:
                    band = state.dominant_band()
                    band_power[band] += activity
                    total_weight += activity
        if total_weight > 0:
            return {k: round(v / total_weight, 4) for k, v in band_power.items()}
        return {k: 0.2 for k in band_power}

    def get_network_activations(self) -> Dict[str, float]:
        from .regions import DMN, SN, CEN, SM, VIS, AUD, LANG, LIM, BG, BS, CB
        networks = {DMN: [], SN: [], CEN: [], SM: [], VIS: [], AUD: [],
                    LANG: [], LIM: [], BG: [], BS: [], CB: []}
        with self._lock:
            for abbrev, region in BRAIN_REGIONS.items():
                if region.network in networks and abbrev in self.states:
                    networks[region.network].append(self.states[abbrev].get_activity())
        return {
            net: round(sum(vals)/len(vals), 4) if vals else 0.0
            for net, vals in networks.items()
        }
