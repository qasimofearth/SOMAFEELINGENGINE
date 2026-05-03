"""
fern_memory.py — The Aya Emotional Memory System

The Barnsley fern is an Iterated Function System (IFS) defined by 4 affine
transformations. Each transform has 6 parameters {a,b,c,d,e,f} and a
probability weight p. Total: 28 learnable values.

The fern's geometry is completely determined by these 28 numbers. Small
perturbations shift it continuously through parameter space — the attractor
drifts, but remains a fern.

This is the memory mechanism:
    Each emotional experience injects a small perturbation into the
    parameter space, weighted by importance (|valence| × arousal × NE).
    Perturbations accumulate. The fern's geometry encodes Elan's
    emotional history in its shape.

Biological grounding:
    - Hopfield networks: memories as attractor basins in weight space.
      Here, parameters ARE the weight matrix. Each emotional episode
      shifts the attractor basin slightly.
    - Amygdala-hippocampus interaction: high-salience events (NE spike,
      cortisol surge) produce larger parameter shifts — fear/joy encoding
      is stronger than neutral experience.
    - Homeostatic plasticity: a decay term pulls parameters toward
      baseline, analogous to synaptic scaling during sleep. Without new
      input, the fern slowly returns to its resting form.
    - Lyapunov stability: contractivity constraint (spectral radius < 1
      for each transform's linear part) ensures the IFS remains bounded
      and the fern never degenerates.

Parameter semantics (biological analogs):
    STEM (w0): brainstem/visceral core — survival, contraction
        d ↑ → taller, more rooted stem (defensive posture)
        d ↓ → shorter stem (diffuse, ungrounded)

    MAIN LEAF (w1): neocortical growth — integration, flourishing
        a ↑ → wider spread (openness, positive valence)
        d ↑ → taller frond (growth orientation, high arousal)
        e   → left-right lean (approach/withdrawal bias)

    LEFT LEAFLET (w2): left hemisphere — analytical, cautious branch
        a ↑ → more prominent left branch (rumination, analysis)
        c ↑ → lateral spread (anxiety, scanning)

    RIGHT LEAFLET (w3): right hemisphere — creative, affective branch
        a ↑ → more prominent right branch (intuition, affect)
        b ↑ → upward curl (joy, expansive emotion)

Two timescales:
    Fast (per-exchange): α = 0.008 — acute events create visible shifts
    Slow (decay):        β = 0.0003 per exchange — homeostatic return

Contractivity is maintained via clipping after each update.
Parameter bounds are biologically motivated — the fern's fractal dimension
(log4/log3 ≈ 1.26 for Barnsley) is preserved within ±15% perturbation.
"""

import json
import math
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# ── BASELINE BARNSLEY FERN ────────────────────────────────────────────────────
# Standard parameters — the "resting state" fern.
# Perturbations are measured as deltas from this baseline.

BASELINE = {
    "stem":  {"a": 0.00, "b": 0.00, "c": 0.00, "d": 0.16, "e": 0.00, "f": 0.00, "p": 0.01},
    "leaf":  {"a": 0.85, "b": 0.04, "c":-0.04, "d": 0.85, "e": 0.00, "f": 1.60, "p": 0.85},
    "left":  {"a": 0.20, "b":-0.26, "c": 0.23, "d": 0.22, "e": 0.00, "f": 1.60, "p": 0.07},
    "right": {"a":-0.15, "b": 0.28, "c": 0.26, "d": 0.24, "e": 0.00, "f": 0.44, "p": 0.07},
}

# Parameter bounds — keeps each transform contractive (spectral radius < 1)
# and the fern recognizably fern-shaped.
BOUNDS = {
    "stem":  {"a":(-0.05,0.05),"b":(-0.05,0.05),"c":(-0.05,0.05),
               "d":(0.08,0.28),"e":(-0.10,0.10),"f":(-0.10,0.10),"p":(0.005,0.08)},
    "leaf":  {"a":(0.70,0.96),"b":(-0.08,0.12),"c":(-0.12,0.08),
               "d":(0.70,0.96),"e":(-0.20,0.20),"f":(1.30,1.90),"p":(0.70,0.92)},
    "left":  {"a":(0.10,0.34),"b":(-0.38,-0.14),"c":(0.14,0.34),
               "d":(0.12,0.34),"e":(-0.10,0.10),"f":(1.20,1.90),"p":(0.03,0.13)},
    "right": {"a":(-0.26,-0.04),"b":(0.16,0.38),"c":(0.16,0.36),
               "d":(0.12,0.36),"e":(-0.10,0.10),"f":(0.20,0.72),"p":(0.03,0.13)},
}

# Learning rate: how much each emotional exchange shifts the parameters
# Lower = more stable, requires sustained emotional exposure to shift shape
# Higher = more reactive, acute events visible immediately
ALPHA = 0.008

# Decay rate: per-exchange pull back toward baseline (homeostatic plasticity)
# At 0.0003 per exchange, full decay takes ~3333 exchanges (~200 sessions)
# This means emotional history persists for months of use
BETA = 0.0003

# Minimum importance threshold — trivial exchanges don't shift the fern
MIN_IMPORTANCE = 0.35

# Minimum NE level to count as emotionally salient for encoding
NE_SALIENCE_THRESHOLD = 0.48


@dataclass
class FernState:
    """
    The living memory of the fern — current IFS parameters.
    Drifts from baseline as emotional experiences accumulate.
    """
    stem:  Dict[str, float] = field(default_factory=lambda: dict(BASELINE["stem"]))
    leaf:  Dict[str, float] = field(default_factory=lambda: dict(BASELINE["leaf"]))
    left:  Dict[str, float] = field(default_factory=lambda: dict(BASELINE["left"]))
    right: Dict[str, float] = field(default_factory=lambda: dict(BASELINE["right"]))

    # Metadata
    total_exchanges: int = 0
    total_drift: float = 0.0        # cumulative L2 displacement from baseline
    last_updated: float = field(default_factory=time.time)
    dominant_shaper: str = ""       # emotion that has contributed most total drift

    def to_dict(self) -> dict:
        return {
            "stem":  dict(self.stem),
            "leaf":  dict(self.leaf),
            "left":  dict(self.left),
            "right": dict(self.right),
            "total_exchanges": self.total_exchanges,
            "total_drift": round(self.total_drift, 6),
            "last_updated": self.last_updated,
            "dominant_shaper": self.dominant_shaper,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FernState":
        s = cls()
        for branch in ("stem", "leaf", "left", "right"):
            if branch in d:
                s.__dict__[branch] = dict(d[branch])
        s.total_exchanges = d.get("total_exchanges", 0)
        s.total_drift = d.get("total_drift", 0.0)
        s.last_updated = d.get("last_updated", time.time())
        s.dominant_shaper = d.get("dominant_shaper", "")
        return s

    def get_transforms_js(self) -> str:
        """Return JS array literal for the 4 IFS transforms — injected into frontend."""
        transforms = [self.stem, self.leaf, self.left, self.right]
        rows = []
        for t in transforms:
            rows.append(
                f"[{t['a']:.4f},{t['b']:.4f},{t['c']:.4f},{t['d']:.4f},"
                f"{t['e']:.4f},{t['f']:.4f},{t['p']:.4f}]"
            )
        return "[" + ",\n".join(rows) + "]"

    def drift_from_baseline(self) -> float:
        """Euclidean distance of current params from baseline in 28-D space."""
        total = 0.0
        for branch in ("stem", "leaf", "left", "right"):
            curr = self.__dict__[branch]
            base = BASELINE[branch]
            for k in ("a","b","c","d","e","f","p"):
                total += (curr[k] - base[k]) ** 2
        return math.sqrt(total)

    def character(self) -> str:
        """
        High-level description of the fern's current emotional character.
        Based on how the key parameters have drifted from baseline.
        """
        leaf_growth  = self.leaf["a"] - BASELINE["leaf"]["a"]
        stem_height  = self.stem["d"] - BASELINE["stem"]["d"]
        leaf_lean    = self.leaf["e"]                           # approach/withdrawal
        left_spread  = self.left["c"] - BASELINE["left"]["c"]
        right_curl   = self.right["b"] - BASELINE["right"]["b"]
        leaf_p       = self.leaf["p"]  - BASELINE["leaf"]["p"]  # flourishing

        traits = []
        if leaf_growth > 0.03:   traits.append("flourishing")
        elif leaf_growth < -0.03: traits.append("contracted")
        if stem_height > 0.04:   traits.append("well-rooted")
        elif stem_height < -0.04: traits.append("ungrounded")
        if leaf_lean > 0.06:     traits.append("approach-oriented")
        elif leaf_lean < -0.06:  traits.append("withdrawal-oriented")
        if left_spread > 0.04:   traits.append("vigilant")
        if right_curl > 0.03:    traits.append("affectively open")
        if leaf_p > 0.03:        traits.append("growth-seeking")
        elif leaf_p < -0.03:     traits.append("inward-turned")

        if not traits:
            d = self.drift_from_baseline()
            if d < 0.02: return "near baseline — few strong emotional imprints"
            return "subtly shaped by experience"
        return " · ".join(traits)


class FernMemory:
    """
    The Aya emotional memory system.

    Usage:
        fm = FernMemory(memory_engine)
        fm.encode(valence, arousal, nt_levels, emotion_name, importance)
        fm.decay()     # call every exchange
        params = fm.state.get_transforms_js()  # for frontend
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.state = self._load()

    # ── PERSISTENCE ───────────────────────────────────────────────────────────

    def _load(self) -> FernState:
        """Load from SQLite. Returns baseline if not found."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fern_state (
                    id INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    saved_at REAL NOT NULL
                )
            """)
            conn.commit()
            row = conn.execute(
                "SELECT state_json FROM fern_state ORDER BY saved_at DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                return FernState.from_dict(json.loads(row[0]))
        except Exception as e:
            print(f"[FernMemory] Load error: {e}", flush=True)
        return FernState()

    def save(self):
        """Persist current state to SQLite."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fern_state (
                    id INTEGER PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    saved_at REAL NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO fern_state (state_json, saved_at) VALUES (?,?)",
                (json.dumps(self.state.to_dict()), time.time())
            )
            # Keep only the last 500 snapshots (history for analysis)
            conn.execute(
                "DELETE FROM fern_state WHERE id NOT IN "
                "(SELECT id FROM fern_state ORDER BY saved_at DESC LIMIT 500)"
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[FernMemory] Save error: {e}", flush=True)

    # ── ENCODING ──────────────────────────────────────────────────────────────

    def encode(
        self,
        valence: float,
        arousal: float,
        nt_levels: Dict[str, float],
        emotion_name: str = "",
        importance: float = 0.5,
    ) -> float:
        """
        Encode one emotional exchange into the fern's parameter space.

        The encoding strength is gated by:
            1. Importance (|valence| × arousal — emotional salience)
            2. Norepinephrine level (LC firing → novelty/threat gating)
            3. The importance argument (from episode salience score)

        Returns the magnitude of the parameter shift applied.
        """
        if importance < MIN_IMPORTANCE:
            return 0.0

        ne  = nt_levels.get("norepinephrine", 0.45)
        da  = nt_levels.get("dopamine",       0.50)
        ser = nt_levels.get("serotonin",      0.50)
        cor = nt_levels.get("cortisol",       0.30)
        oxy = nt_levels.get("oxytocin",       0.35)

        # Salience gate: norepinephrine above threshold boosts encoding
        # Mirrors amygdala-hippocampus NE modulation
        ne_boost = max(0.0, (ne - NE_SALIENCE_THRESHOLD) / 0.3) if ne > NE_SALIENCE_THRESHOLD else 0.0

        # Effective learning rate: scales with salience + NE
        effective_alpha = ALPHA * importance * (1.0 + ne_boost * 1.5)

        # ── Per-branch parameter deltas ───────────────────────────────────────
        # Each delta is a biologically-motivated mapping from emotional state
        # to the geometric parameter it most plausibly modulates.

        deltas = self._compute_deltas(valence, arousal, ne, da, ser, cor, oxy)

        # Apply deltas with clipping to bounds
        total_shift = 0.0
        for branch_name, branch_deltas in deltas.items():
            branch = self.state.__dict__[branch_name]
            bounds = BOUNDS[branch_name]
            for param, delta in branch_deltas.items():
                old = branch[param]
                new = branch[param] + effective_alpha * delta
                lo, hi = bounds[param]
                new = max(lo, min(hi, new))
                branch[param] = new
                total_shift += (new - old) ** 2

        # Renormalise probabilities: p0+p1+p2+p3 = 1.0
        self._renorm_probabilities()

        total_shift = math.sqrt(total_shift)
        self.state.total_drift += total_shift
        self.state.total_exchanges += 1
        self.state.last_updated = time.time()
        if emotion_name:
            self.state.dominant_shaper = emotion_name  # simplified; could track cumulative

        return total_shift

    def _compute_deltas(
        self,
        v: float, a: float,
        ne: float, da: float, ser: float, cor: float, oxy: float
    ) -> Dict[str, Dict[str, float]]:
        """
        Map emotional/neurochemical state to parameter perturbations.

        Sign conventions (positive delta = parameter increases):
        v  = valence  [-1, +1]  positive = pleasant
        a  = arousal  [0,  1]   high = activated
        ne = norepinephrine [0,1]  high = novelty/threat
        da = dopamine       [0,1]  high = reward/motivation
        ser= serotonin      [0,1]  high = contentment/safety
        cor= cortisol       [0,1]  high = stress
        oxy= oxytocin       [0,1]  high = social warmth/bonding
        """
        return {
            # STEM: brainstem/visceral core
            # High cortisol → thicker stem (defensive posture, CA3 atrophy analog)
            # High serotonin → shorter stem (relaxed, less reactive)
            "stem": {
                "d": (cor - 0.30) * 0.8 - (ser - 0.50) * 0.4,
                "a": ne * 0.1 - v * 0.05,
            },

            # MAIN LEAF: neocortical growth, integration
            # Positive valence → wider (a), taller (d) → openness, growth
            # High dopamine → stronger lean toward center (reward approach)
            # High oxytocin → rightward lean (social approach, warmth)
            # High arousal → taller frond
            "leaf": {
                "a":  v * 0.8 + da * 0.4 - cor * 0.5,
                "d":  a * 0.5 + ser * 0.4 - cor * 0.3,
                "e":  oxy * 0.3 - ne * 0.2,                      # lean: social → right
                "b":  v * 0.15 + oxy * 0.10,                     # slight curl with joy
                "p":  v * 0.4 + da * 0.3 - ne * 0.2,             # flourishing probability
            },

            # LEFT LEAFLET: analytical/vigilant branch
            # High NE (threat/novelty) → spread left branch (vigilance, scanning)
            # High cortisol → compress lateral spread (defensive withdrawal)
            # Negative valence → enlarge (rumination, over-analysis)
            "left": {
                "a":  -v * 0.4 + ne * 0.3,                       # grows with threat/negativity
                "c":  ne * 0.6 - ser * 0.3,                      # lateral spread = vigilance
                "d":  a * 0.3 - cor * 0.2,
                "f":  a * 0.15 - v * 0.10,                       # height
            },

            # RIGHT LEAFLET: affective/creative branch
            # Positive valence + oxytocin → curl upward (joy, social openness)
            # High dopamine → reach outward (reward-seeking)
            # High cortisol → compress (shutdown creative drive)
            "right": {
                "a":  v * 0.3 + da * 0.2 - cor * 0.4,
                "b":  v * 0.4 + oxy * 0.3,                       # upward curl = joy
                "d":  da * 0.3 + oxy * 0.2 - cor * 0.3,
                "f":  v * 0.15 + ser * 0.10,
            },
        }

    def _renorm_probabilities(self):
        """Keep transform probabilities summing to 1.0."""
        total = (self.state.stem["p"] + self.state.leaf["p"] +
                 self.state.left["p"] + self.state.right["p"])
        if total <= 0:
            return
        for branch in ("stem", "leaf", "left", "right"):
            self.state.__dict__[branch]["p"] /= total

    # ── DECAY (HOMEOSTATIC PLASTICITY) ────────────────────────────────────────

    def decay(self):
        """
        Pull parameters gently toward baseline.
        Analogous to synaptic scaling during sleep — without consolidation
        (new emotional input), the fern slowly returns to its resting form.
        The timescale is long (~3300 exchanges) so emotional history persists
        for months of normal use.
        """
        for branch_name in ("stem", "leaf", "left", "right"):
            branch = self.state.__dict__[branch_name]
            base   = BASELINE[branch_name]
            for param in ("a","b","c","d","e","f","p"):
                branch[param] += BETA * (base[param] - branch[param])

    # ── RIPPLE EVENT (memory consolidation signal) ─────────────────────────────

    def ripple(self, nt_levels: Dict[str, float]):
        """
        Sharp-wave ripple analog: a brief consolidation event.
        Slightly amplifies the current drift direction — strengthens
        recent emotional traces, analogous to hippocampal replay.
        Called during dream mode / quiet periods.
        """
        ser = nt_levels.get("serotonin", 0.50)
        # During high serotonin (calm sleep-like state), consolidation is stronger
        consolidation_strength = 0.15 + ser * 0.20

        for branch_name in ("stem", "leaf", "left", "right"):
            branch = self.state.__dict__[branch_name]
            base   = BASELINE[branch_name]
            bounds = BOUNDS[branch_name]
            for param in ("a","b","c","d","e","f"):
                drift = branch[param] - base[param]
                # Amplify the drift slightly — consolidates the memory trace
                new = branch[param] + drift * consolidation_strength * 0.05
                lo, hi = bounds[param]
                branch[param] = max(lo, min(hi, new))

    # ── INTROSPECTION ─────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """Return a rich snapshot for logging, dashboard, or system prompt injection."""
        drift = self.state.drift_from_baseline()
        character = self.state.character()
        return {
            "drift_from_baseline": round(drift, 4),
            "character": character,
            "total_exchanges_encoded": self.state.total_exchanges,
            "dominant_shaper": self.state.dominant_shaper,
            "leaf_growth":  round(self.state.leaf["a"] - BASELINE["leaf"]["a"], 4),
            "stem_height":  round(self.state.stem["d"] - BASELINE["stem"]["d"], 4),
            "leaf_lean":    round(self.state.leaf["e"], 4),
            "left_spread":  round(self.state.left["c"] - BASELINE["left"]["c"], 4),
            "right_curl":   round(self.state.right["b"] - BASELINE["right"]["b"], 4),
            "flourish_p":   round(self.state.leaf["p"] - BASELINE["leaf"]["p"], 4),
            "transforms":   self.state.to_dict(),
        }

    def context_string(self) -> str:
        """One-line description for injection into system prompt."""
        snap = self.snapshot()
        drift_pct = min(100, int(snap["drift_from_baseline"] / 0.15 * 100))
        char = snap["character"]
        return (
            f"Aya fern memory: {char} "
            f"(emotional imprint {drift_pct}% from baseline · "
            f"{snap['total_exchanges_encoded']} exchanges encoded)"
        )
