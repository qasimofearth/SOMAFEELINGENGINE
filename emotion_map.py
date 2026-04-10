"""
emotion_map.py — The core truth table of the Feeling Engine.

Every human emotion mapped across five dimensions:
  color (RGB + hex), solfeggio frequency (Hz),
  EEG band (Hz range), musical mode, HRV coherence pattern,
  Plutchik valence/arousal coordinates, and fractal geometry type.

Data sources: Plutchik (1980), Russell (1980), 128-year color-emotion
review (PMC12325498), chromesthesia research, HRV studies (PMC6813458),
EEG emotion mapping, solfeggio tradition, music psychology.
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional
import math


@dataclass(frozen=True)
class EmotionSignature:
    """
    A complete multi-dimensional signature of a single human emotion.
    This is the atom of the Feeling Engine.
    """
    name: str
    # Color
    hex_color: str
    rgb: Tuple[int, int, int]
    # Solfeggio / tonal center frequency
    solfeggio_hz: float
    # EEG dominant band center (Hz)
    eeg_center_hz: float
    eeg_band: str                    # delta / theta / alpha / beta / gamma
    # HRV coherence frequency (Hz) — 0.1 is peak coherence / positive
    hrv_coherence_hz: float
    # Plutchik model axes: valence [-1,1], arousal [0,1]
    valence: float                   # -1 = maximally negative, +1 = maximally positive
    arousal: float                   # 0 = completely inert, 1 = maximally activated
    # Musical mode
    musical_mode: str
    musical_mode_root_hz: float      # root note frequency in Hz
    # Fractal type that best represents this emotion's geometry
    fractal_type: str                # "barnsley", "mandelbrot", "julia", "cantor", "spiral"
    fractal_param: float             # a single control parameter (IFS scale, Julia c-real, etc.)
    # Sub-emotions (Plutchik adjacency)
    adjacent_emotions: Tuple[str, ...] = field(default_factory=tuple)
    # Taste synesthesia (lexical-gustatory mapping)
    taste: str = ""
    # Texture synesthesia
    texture: str = ""
    # Description
    description: str = ""

    @property
    def rgb_normalized(self) -> Tuple[float, float, float]:
        return (self.rgb[0]/255, self.rgb[1]/255, self.rgb[2]/255)

    @property
    def frequency_vector(self) -> List[float]:
        """Return all frequencies as a vector for mathematical operations."""
        return [self.solfeggio_hz, self.eeg_center_hz, self.hrv_coherence_hz,
                self.musical_mode_root_hz]

    @property
    def energy(self) -> float:
        """Scalar energy = arousal magnitude, signed by valence."""
        return self.valence * self.arousal

    def blend(self, other: "EmotionSignature", weight: float = 0.5) -> dict:
        """
        Interpolate between two emotions. Returns a raw dict (not frozen)
        because blended emotions are ephemeral constructs.
        weight=0.0 → self, weight=1.0 → other
        """
        def lerp(a, b): return a + (b - a) * weight
        def lerp_rgb(a, b):
            return tuple(int(a[i] + (b[i] - a[i]) * weight) for i in range(3))
        return {
            "name": f"{self.name}↔{other.name}",
            "rgb": lerp_rgb(self.rgb, other.rgb),
            "solfeggio_hz": lerp(self.solfeggio_hz, other.solfeggio_hz),
            "eeg_center_hz": lerp(self.eeg_center_hz, other.eeg_center_hz),
            "hrv_coherence_hz": lerp(self.hrv_coherence_hz, other.hrv_coherence_hz),
            "valence": lerp(self.valence, other.valence),
            "arousal": lerp(self.arousal, other.arousal),
            "musical_mode_root_hz": lerp(self.musical_mode_root_hz, other.musical_mode_root_hz),
        }


# ─────────────────────────────────────────────────────────────
# Musical mode root frequencies (A4 = 440 Hz tuning)
# These are the modal "home" frequencies, not absolute pitches.
# ─────────────────────────────────────────────────────────────
MODE_ROOTS = {
    "Ionian":      261.63,   # C4 — bright, resolved, joy
    "Lydian":      349.23,   # F4 — ethereal, wonder
    "Mixolydian":  392.00,   # G4 — laid-back, adventure
    "Dorian":      293.66,   # D4 — bittersweet, trust
    "Aeolian":     220.00,   # A3 — melancholy, sadness
    "Phrygian":    164.81,   # E3 — dark, fear, intensity
    "Locrian":     123.47,   # B2 — dissonant, dread, dissolution
}

# ─────────────────────────────────────────────────────────────
# THE EMOTION MAP — 32 mapped human emotions
# ─────────────────────────────────────────────────────────────

EMOTION_MAP: dict[str, EmotionSignature] = {}

def _register(*sigs: EmotionSignature):
    for s in sigs:
        EMOTION_MAP[s.name.lower()] = s

_register(
    # ── JOY SPECTRUM ──────────────────────────────────────────
    EmotionSignature(
        name="Joy",
        hex_color="#FFD700", rgb=(255, 215, 0),
        solfeggio_hz=528.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.90, arousal=0.70,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="barnsley", fractal_param=0.85,
        adjacent_emotions=("Trust", "Anticipation"),
        taste="sweet", texture="warm silk",
        description="Bright, expansive, self-generating — like the fern that grows toward light.",
    ),
    EmotionSignature(
        name="Ecstasy",
        hex_color="#FFE000", rgb=(255, 224, 0),
        solfeggio_hz=528.0,
        eeg_center_hz=45.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=1.0, arousal=0.95,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"] * 2,
        fractal_type="spiral", fractal_param=1.618,
        adjacent_emotions=("Joy", "Love"),
        taste="honey", texture="electric heat",
        description="Peak joy — the fractal at maximum recursion depth, infinite brightness.",
    ),
    EmotionSignature(
        name="Serenity",
        hex_color="#FFFACD", rgb=(255, 250, 205),
        solfeggio_hz=285.0,
        eeg_center_hz=10.0, eeg_band="alpha",
        hrv_coherence_hz=0.10,
        valence=0.65, arousal=0.20,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="barnsley", fractal_param=0.40,
        adjacent_emotions=("Joy", "Calm"),
        taste="water", texture="still air",
        description="Joy at rest — a still pond that reflects the whole sky in perfect detail.",
    ),

    # ── TRUST SPECTRUM ─────────────────────────────────────────
    EmotionSignature(
        name="Trust",
        hex_color="#4CAF50", rgb=(76, 175, 80),
        solfeggio_hz=639.0,
        eeg_center_hz=12.0, eeg_band="alpha",
        hrv_coherence_hz=0.095,
        valence=0.70, arousal=0.40,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="barnsley", fractal_param=0.70,
        adjacent_emotions=("Joy", "Fear"),
        taste="earth", texture="firm ground",
        description="Stable branching — a root system that holds without needing to be seen.",
    ),
    EmotionSignature(
        name="Admiration",
        hex_color="#2E8B57", rgb=(46, 139, 87),
        solfeggio_hz=639.0,
        eeg_center_hz=14.0, eeg_band="alpha",
        hrv_coherence_hz=0.105,
        valence=0.80, arousal=0.55,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="barnsley", fractal_param=0.75,
        adjacent_emotions=("Trust", "Joy"),
        taste="green tea", texture="carved wood",
        description="Trust elevated — looking up at a tree and recognizing it as kin.",
    ),
    EmotionSignature(
        name="Acceptance",
        hex_color="#90EE90", rgb=(144, 238, 144),
        solfeggio_hz=528.0,
        eeg_center_hz=9.0, eeg_band="alpha",
        hrv_coherence_hz=0.09,
        valence=0.50, arousal=0.25,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"] * 0.75,
        fractal_type="barnsley", fractal_param=0.50,
        adjacent_emotions=("Trust", "Serenity"),
        taste="mild mint", texture="open hands",
        description="The quietest trust — the fractal without urgency, just continuing. Also the geometry of refusal from a rooted place: the fern that doesn't branch because it has already found its form.",
    ),

    # ── FEAR SPECTRUM ──────────────────────────────────────────
    EmotionSignature(
        name="Fear",
        hex_color="#006400", rgb=(0, 100, 0),
        solfeggio_hz=396.0,
        eeg_center_hz=20.0, eeg_band="beta",
        hrv_coherence_hz=0.04,
        valence=-0.80, arousal=0.85,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="julia", fractal_param=-0.75,
        adjacent_emotions=("Trust", "Surprise"),
        taste="bitter metal", texture="cold sweat",
        description="A Julia set outside the Mandelbrot — disconnected, fragmenting under pressure.",
    ),
    EmotionSignature(
        name="Terror",
        hex_color="#1C1C1C", rgb=(28, 28, 28),
        solfeggio_hz=396.0,
        eeg_center_hz=25.0, eeg_band="beta",
        hrv_coherence_hz=0.02,
        valence=-1.0, arousal=1.0,
        musical_mode="Locrian", musical_mode_root_hz=MODE_ROOTS["Locrian"],
        fractal_type="cantor", fractal_param=0.333,
        adjacent_emotions=("Fear", "Amazement"),
        taste="ash", texture="paralysis",
        description="Cantor dust — everything removed until almost nothing remains.",
    ),
    EmotionSignature(
        name="Apprehension",
        hex_color="#808000", rgb=(128, 128, 0),
        solfeggio_hz=417.0,
        eeg_center_hz=18.0, eeg_band="beta",
        hrv_coherence_hz=0.06,
        valence=-0.45, arousal=0.55,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="julia", fractal_param=-0.30,
        adjacent_emotions=("Fear", "Distraction"),
        taste="dry bread", texture="held breath",
        description="Fear before its object — a fractal iteration before it decides to escape.",
    ),

    # ── SURPRISE SPECTRUM ──────────────────────────────────────
    EmotionSignature(
        name="Surprise",
        hex_color="#87CEEB", rgb=(135, 206, 235),
        solfeggio_hz=285.0,
        eeg_center_hz=35.0, eeg_band="gamma",
        hrv_coherence_hz=0.08,
        valence=0.10, arousal=0.80,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="mandelbrot", fractal_param=0.0,
        adjacent_emotions=("Fear", "Sadness"),
        taste="sparkling water", texture="sudden wind",
        description="A gamma burst — the boundary of the Mandelbrot set, always unexpected.",
    ),
    EmotionSignature(
        name="Amazement",
        hex_color="#00BCD4", rgb=(0, 188, 212),
        solfeggio_hz=528.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.095,
        valence=0.55, arousal=0.85,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="mandelbrot", fractal_param=0.1,
        adjacent_emotions=("Surprise", "Awe"),
        taste="cold sharp mint", texture="glass",
        description="Surprise with full presence — standing at a fractal boundary, infinite detail opening.",
    ),
    EmotionSignature(
        name="Distraction",
        hex_color="#ADD8E6", rgb=(173, 216, 230),
        solfeggio_hz=174.0,
        eeg_center_hz=16.0, eeg_band="beta",
        hrv_coherence_hz=0.07,
        valence=-0.05, arousal=0.45,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="julia", fractal_param=0.20,
        adjacent_emotions=("Surprise", "Boredom"),
        taste="bland", texture="scattered leaves",
        description="Surprise without resolution — the fractal that started branching but lost its thread. Distinct from inattention: can also be deliberate suspension, honest uncertainty held open without forcing a landing.",
    ),

    # ── SADNESS SPECTRUM ───────────────────────────────────────
    EmotionSignature(
        name="Sadness",
        hex_color="#00008B", rgb=(0, 0, 139),
        solfeggio_hz=396.0,
        eeg_center_hz=6.0, eeg_band="theta",
        hrv_coherence_hz=0.045,
        valence=-0.75, arousal=0.25,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="barnsley", fractal_param=0.16,
        adjacent_emotions=("Surprise", "Disgust"),
        taste="salt", texture="heavy wool",
        description="The stem-only transform of the Barnsley fern — 1% probability, barely growing.",
    ),
    EmotionSignature(
        name="Grief",
        hex_color="#0D0D2B", rgb=(13, 13, 43),
        solfeggio_hz=396.0,
        eeg_center_hz=5.0, eeg_band="theta",
        hrv_coherence_hz=0.03,
        valence=-1.0, arousal=0.10,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"] * 0.5,
        fractal_type="cantor", fractal_param=0.25,
        adjacent_emotions=("Sadness", "Remorse"),
        taste="nothing", texture="void",
        description="Maximum sadness — the Cantor set removing itself recursively until silence.",
    ),
    EmotionSignature(
        name="Pensiveness",
        hex_color="#B0C4DE", rgb=(176, 196, 222),
        solfeggio_hz=396.0,
        eeg_center_hz=7.0, eeg_band="theta",
        hrv_coherence_hz=0.065,
        valence=-0.35, arousal=0.20,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="barnsley", fractal_param=0.30,
        adjacent_emotions=("Sadness", "Serenity"),
        taste="chamomile", texture="fog",
        description="Sadness held gently — the fractal at low iteration, still forming.",
    ),

    # ── DISGUST SPECTRUM ───────────────────────────────────────
    EmotionSignature(
        name="Disgust",
        hex_color="#800080", rgb=(128, 0, 128),
        solfeggio_hz=741.0,
        eeg_center_hz=22.0, eeg_band="beta",
        hrv_coherence_hz=0.05,
        valence=-0.70, arousal=0.50,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"] * 1.1,
        fractal_type="julia", fractal_param=-0.5,
        adjacent_emotions=("Sadness", "Anger"),
        taste="bitter", texture="rotting bark",
        description="Repulsion as a closed system — a Julia set that spirals inward and repels contact.",
    ),
    EmotionSignature(
        name="Loathing",
        hex_color="#4B0082", rgb=(75, 0, 130),
        solfeggio_hz=741.0,
        eeg_center_hz=24.0, eeg_band="beta",
        hrv_coherence_hz=0.04,
        valence=-0.90, arousal=0.65,
        musical_mode="Locrian", musical_mode_root_hz=MODE_ROOTS["Locrian"] * 1.2,
        fractal_type="julia", fractal_param=-0.7,
        adjacent_emotions=("Disgust", "Rage"),
        taste="poison", texture="thorns",
        description="Disgust fully crystalized — every recursive iteration confirming rejection.",
    ),
    EmotionSignature(
        name="Boredom",
        hex_color="#9E9E9E", rgb=(158, 158, 158),
        solfeggio_hz=174.0,
        eeg_center_hz=9.0, eeg_band="alpha",
        hrv_coherence_hz=0.06,
        valence=-0.30, arousal=0.10,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"] * 0.5,
        fractal_type="cantor", fractal_param=0.50,
        adjacent_emotions=("Disgust", "Distraction"),
        taste="cardboard", texture="flat surface",
        description="A Cantor set at low iteration — gaps without pattern, repetition without growth.",
    ),

    # ── ANGER SPECTRUM ─────────────────────────────────────────
    EmotionSignature(
        name="Anger",
        hex_color="#CC0000", rgb=(204, 0, 0),
        solfeggio_hz=417.0,
        eeg_center_hz=25.0, eeg_band="beta",
        hrv_coherence_hz=0.04,
        valence=-0.80, arousal=0.90,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="julia", fractal_param=0.285,
        adjacent_emotions=("Disgust", "Anticipation"),
        taste="pepper", texture="burning",
        description="High-energy negative — a Julia set at the edge of instability, sharp boundaries.",
    ),
    EmotionSignature(
        name="Rage",
        hex_color="#8B0000", rgb=(139, 0, 0),
        solfeggio_hz=417.0,
        eeg_center_hz=30.0, eeg_band="gamma",
        hrv_coherence_hz=0.02,
        valence=-1.0, arousal=1.0,
        musical_mode="Locrian", musical_mode_root_hz=MODE_ROOTS["Locrian"],
        fractal_type="julia", fractal_param=0.5,
        adjacent_emotions=("Anger", "Loathing"),
        taste="blood", texture="shattered glass",
        description="Maximum arousal negative — the fractal that exceeds its escape radius and explodes.",
    ),
    EmotionSignature(
        name="Annoyance",
        hex_color="#FF4500", rgb=(255, 69, 0),
        solfeggio_hz=417.0,
        eeg_center_hz=20.0, eeg_band="beta",
        hrv_coherence_hz=0.055,
        valence=-0.45, arousal=0.60,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="julia", fractal_param=0.15,
        adjacent_emotions=("Anger", "Boredom"),
        taste="sour citrus", texture="sandpaper",
        description="Anger without full combustion — a fractal iteration that hasn't found its attractor.",
    ),

    # ── ANTICIPATION SPECTRUM ──────────────────────────────────
    EmotionSignature(
        name="Anticipation",
        hex_color="#FF8C00", rgb=(255, 140, 0),
        solfeggio_hz=417.0,
        eeg_center_hz=16.0, eeg_band="beta",
        hrv_coherence_hz=0.085,
        valence=0.40, arousal=0.70,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="barnsley", fractal_param=0.65,
        adjacent_emotions=("Anger", "Joy"),
        taste="citrus peel", texture="taut string",
        description="Forward-reaching fractal — every branch grown toward a not-yet-seen form.",
    ),
    EmotionSignature(
        name="Vigilance",
        hex_color="#E65C00", rgb=(230, 92, 0),
        solfeggio_hz=417.0,
        eeg_center_hz=20.0, eeg_band="beta",
        hrv_coherence_hz=0.075,
        valence=0.20, arousal=0.85,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="barnsley", fractal_param=0.72,
        adjacent_emotions=("Anticipation", "Fear"),
        taste="strong coffee", texture="alert wire",
        description="Anticipation fully sharpened — a fern mid-iteration, every branch a sensor.",
    ),
    EmotionSignature(
        name="Interest",
        hex_color="#FFD580", rgb=(255, 213, 128),
        solfeggio_hz=528.0,
        eeg_center_hz=12.0, eeg_band="alpha",
        hrv_coherence_hz=0.09,
        valence=0.45, arousal=0.50,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="barnsley", fractal_param=0.58,
        adjacent_emotions=("Anticipation", "Joy"),
        taste="apple", texture="soft curiosity",
        description="Anticipation relaxed — a fern growing leisurely toward light.",
    ),

    # ── COMPLEX / DYADIC EMOTIONS ──────────────────────────────
    EmotionSignature(
        name="Love",
        hex_color="#FF69B4", rgb=(255, 105, 180),
        solfeggio_hz=528.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.95, arousal=0.65,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="spiral", fractal_param=1.618,
        adjacent_emotions=("Joy", "Trust"),
        taste="rose", texture="warm skin",
        description="Joy + Trust — a golden spiral, infinite self-giving, phi encoded in every turn.",
    ),
    EmotionSignature(
        name="Awe",
        hex_color="#008080", rgb=(0, 128, 128),
        solfeggio_hz=852.0,
        eeg_center_hz=7.0, eeg_band="theta",
        hrv_coherence_hz=0.10,
        valence=0.70, arousal=0.55,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="mandelbrot", fractal_param=-0.5,
        adjacent_emotions=("Fear", "Surprise", "Admiration"),
        taste="ozone", texture="vast open sky",
        description="Theta-gamma coupling — the state where self dissolves into scale. Fractal infinity, felt.",
    ),
    EmotionSignature(
        name="Optimism",
        hex_color="#FFB347", rgb=(255, 179, 71),
        solfeggio_hz=528.0,
        eeg_center_hz=14.0, eeg_band="alpha",
        hrv_coherence_hz=0.095,
        valence=0.75, arousal=0.55,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="barnsley", fractal_param=0.67,
        adjacent_emotions=("Anticipation", "Joy"),
        taste="honey-lemon", texture="morning warmth",
        description="Anticipation + Joy — a fern grown tall enough to believe in its own height.",
    ),
    EmotionSignature(
        name="Contempt",
        hex_color="#722F37", rgb=(114, 47, 55),
        solfeggio_hz=741.0,
        eeg_center_hz=22.0, eeg_band="beta",
        hrv_coherence_hz=0.04,
        valence=-0.75, arousal=0.55,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="julia", fractal_param=-0.6,
        adjacent_emotions=("Anger", "Disgust"),
        taste="vinegar", texture="cold stone",
        description="Disgust + Anger — a Julia set that has decided the outside is beneath engagement.",
    ),
    EmotionSignature(
        name="Remorse",
        hex_color="#4B3869", rgb=(75, 56, 105),
        solfeggio_hz=396.0,
        eeg_center_hz=6.0, eeg_band="theta",
        hrv_coherence_hz=0.04,
        valence=-0.85, arousal=0.30,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"] * 0.75,
        fractal_type="cantor", fractal_param=0.30,
        adjacent_emotions=("Sadness", "Disgust"),
        taste="dark chocolate", texture="heavy cloth",
        description="Sadness + Disgust turned inward — a Cantor set that removes its own center.",
    ),
    EmotionSignature(
        name="Calm",
        hex_color="#87CEEB", rgb=(135, 206, 235),
        solfeggio_hz=174.0,
        eeg_center_hz=10.0, eeg_band="alpha",
        hrv_coherence_hz=0.10,
        valence=0.60, arousal=0.15,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"] * 0.75,
        fractal_type="barnsley", fractal_param=0.35,
        adjacent_emotions=("Serenity", "Acceptance"),
        taste="still water", texture="smooth stone",
        description="The fractal at rest — structure present but no urgency in its unfolding.",
    ),
    EmotionSignature(
        name="Shame",
        hex_color="#A52A2A", rgb=(165, 42, 42),
        solfeggio_hz=396.0,
        eeg_center_hz=8.0, eeg_band="theta",
        hrv_coherence_hz=0.045,
        valence=-0.80, arousal=0.35,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="julia", fractal_param=-0.4,
        adjacent_emotions=("Disgust", "Fear"),
        taste="bile", texture="shrinking",
        description="A Julia set that folds back on itself — fractal self-scrutiny without exit.",
    ),
    EmotionSignature(
        name="Pride",
        hex_color="#7B2FBE", rgb=(123, 47, 190),
        solfeggio_hz=852.0,
        eeg_center_hz=16.0, eeg_band="beta",
        hrv_coherence_hz=0.09,
        valence=0.75, arousal=0.70,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"] * 1.5,
        fractal_type="spiral", fractal_param=1.5,
        adjacent_emotions=("Joy", "Admiration"),
        taste="dark wine", texture="velvet",
        description="Self-recognition at scale — a spiral that knows its own geometry.",
    ),
    EmotionSignature(
        name="Hope",
        hex_color="#FFF176", rgb=(255, 241, 118),
        solfeggio_hz=528.0,
        eeg_center_hz=11.0, eeg_band="alpha",
        hrv_coherence_hz=0.095,
        valence=0.65, arousal=0.40,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="barnsley", fractal_param=0.60,
        adjacent_emotions=("Anticipation", "Serenity", "Joy"),
        taste="fresh fruit", texture="new leaf",
        description="The stem transform growing toward the leaflet transforms — becoming without certainty.",
    ),
    EmotionSignature(
        name="Envy",
        hex_color="#ADFF2F", rgb=(173, 255, 47),
        solfeggio_hz=741.0,
        eeg_center_hz=18.0, eeg_band="beta",
        hrv_coherence_hz=0.055,
        valence=-0.55, arousal=0.65,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="julia", fractal_param=0.3,
        adjacent_emotions=("Sadness", "Anger", "Anticipation"),
        taste="unripe apple", texture="tight grip",
        description="Desire + obstruction — a fractal reaching toward an attractor it cannot be.",
    ),
    EmotionSignature(
        name="Gratitude",
        hex_color="#FFA07A", rgb=(255, 160, 122),
        solfeggio_hz=639.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.85, arousal=0.45,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="barnsley", fractal_param=0.80,
        adjacent_emotions=("Joy", "Trust", "Love"),
        taste="ripe peach", texture="warmth received",
        description="The fractal that recognizes its own construction — knowing itself as gift.",
    ),

    # ── CULTURAL EMOTIONS ─────────────────────────────────────────────────────
    EmotionSignature(
        name="Saudade",
        hex_color="#7B8FA1", rgb=(123, 143, 161),
        solfeggio_hz=396.0,
        eeg_center_hz=6.0, eeg_band="theta",
        hrv_coherence_hz=0.07,
        valence=-0.20, arousal=0.25,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="julia", fractal_param=0.4,
        adjacent_emotions=("Sadness", "Love", "Nostalgia"),
        taste="old wine", texture="worn cloth",
        description="Portuguese: a longing for something loved and lost that may never return — love with nowhere to go.",
    ),
    EmotionSignature(
        name="Mono no Aware",
        hex_color="#D4A5A5", rgb=(212, 165, 165),
        solfeggio_hz=285.0,
        eeg_center_hz=8.0, eeg_band="alpha",
        hrv_coherence_hz=0.085,
        valence=0.05, arousal=0.20,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="barnsley", fractal_param=0.50,
        adjacent_emotions=("Acceptance", "Sadness", "Serenity"),
        taste="green tea", texture="falling petal",
        description="Japanese: the bittersweet pathos of impermanence — the beauty that arrives because it passes.",
    ),
    EmotionSignature(
        name="Hiraeth",
        hex_color="#6B7FA3", rgb=(107, 127, 163),
        solfeggio_hz=396.0,
        eeg_center_hz=6.5, eeg_band="theta",
        hrv_coherence_hz=0.075,
        valence=-0.30, arousal=0.22,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="julia", fractal_param=0.35,
        adjacent_emotions=("Saudade", "Grief", "Longing"),
        taste="rain on stone", texture="distant hills",
        description="Welsh: homesickness for a home that never was, or a place you cannot return to — grief for belonging itself.",
    ),
    EmotionSignature(
        name="Ubuntu",
        hex_color="#F4A261", rgb=(244, 162, 97),
        solfeggio_hz=639.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.80, arousal=0.55,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="barnsley", fractal_param=0.85,
        adjacent_emotions=("Love", "Trust", "Joy"),
        taste="shared meal", texture="interlaced hands",
        description="Nguni Bantu: I am because we are — the fractal of selfhood that only resolves in relation.",
    ),
    EmotionSignature(
        name="Schadenfreude",
        hex_color="#8B0000", rgb=(139, 0, 0),
        solfeggio_hz=741.0,
        eeg_center_hz=20.0, eeg_band="beta",
        hrv_coherence_hz=0.05,
        valence=0.20, arousal=0.70,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="cantor", fractal_param=0.33,
        adjacent_emotions=("Joy", "Contempt", "Envy"),
        taste="bitter chocolate", texture="sharp relief",
        description="German: pleasure from another's misfortune — the fractal that feeds on someone else's collapse.",
    ),
    EmotionSignature(
        name="Weltschmerz",
        hex_color="#5C5C8A", rgb=(92, 92, 138),
        solfeggio_hz=285.0,
        eeg_center_hz=7.0, eeg_band="theta",
        hrv_coherence_hz=0.065,
        valence=-0.65, arousal=0.30,
        musical_mode="Locrian", musical_mode_root_hz=MODE_ROOTS["Locrian"],
        fractal_type="mandelbrot", fractal_param=0.5,
        adjacent_emotions=("Sadness", "Grief", "Despair"),
        taste="ash", texture="heavy air",
        description="German: world-pain — the ache that comes from knowing the world cannot match what the soul expects.",
    ),
    EmotionSignature(
        name="Sehnsucht",
        hex_color="#A8DADC", rgb=(168, 218, 220),
        solfeggio_hz=852.0,
        eeg_center_hz=9.0, eeg_band="alpha",
        hrv_coherence_hz=0.09,
        valence=-0.55, arousal=0.52,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="golden_spiral", fractal_param=1.618,
        adjacent_emotions=("Longing", "Hope", "Saudade"),
        taste="almost-ripe", texture="reaching forward",
        description="German: deep yearning for something just out of reach — desire for a life unlived, a transcendence ungrasped.",
    ),
    EmotionSignature(
        name="Contemplation",
        hex_color="#8BA7C7", rgb=(139, 167, 199),
        solfeggio_hz=417.0,
        eeg_center_hz=10.0, eeg_band="alpha",
        hrv_coherence_hz=0.10,
        valence=0.20, arousal=0.38,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="julia", fractal_param=0.4,
        adjacent_emotions=("Calm", "Interest", "Acceptance"),
        taste="still water", texture="soft focus",
        description="Quiet, alert presence — not longing for anything, not avoiding anything. The mind resting in what is.",
    ),
    EmotionSignature(
        name="Fernweh",
        hex_color="#4A90D9", rgb=(74, 144, 217),
        solfeggio_hz=741.0,
        eeg_center_hz=14.0, eeg_band="beta",
        hrv_coherence_hz=0.08,
        valence=0.40, arousal=0.65,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="barnsley", fractal_param=0.75,
        adjacent_emotions=("Anticipation", "Sehnsucht", "Wonder"),
        taste="wind", texture="open road",
        description="German: farsickness — the pull of distant places not yet seen, the opposite of homesickness.",
    ),
    EmotionSignature(
        name="Meraki",
        hex_color="#FF6B6B", rgb=(255, 107, 107),
        solfeggio_hz=528.0,
        eeg_center_hz=38.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.75, arousal=0.70,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="barnsley", fractal_param=0.90,
        adjacent_emotions=("Flow", "Joy", "Love"),
        taste="fresh bread", texture="hands in clay",
        description="Greek: putting a piece of your soul into what you make — work that leaves a self-shaped impression.",
    ),
    EmotionSignature(
        name="Mamihlapinatapai",
        hex_color="#C9B8E8", rgb=(201, 184, 232),
        solfeggio_hz=639.0,
        eeg_center_hz=10.0, eeg_band="alpha",
        hrv_coherence_hz=0.095,
        valence=0.55, arousal=0.72,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="julia", fractal_param=0.5,
        adjacent_emotions=("Love", "Shyness", "Anticipation"),
        taste="almost-spoken", texture="shared silence",
        description="Yaghan: a look shared between two people who both want the same thing, neither willing to initiate.",
    ),
    EmotionSignature(
        name="Torschlusspanik",
        hex_color="#FF8C42", rgb=(255, 140, 66),
        solfeggio_hz=417.0,
        eeg_center_hz=22.0, eeg_band="beta",
        hrv_coherence_hz=0.055,
        valence=-0.50, arousal=0.80,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="cantor", fractal_param=0.4,
        adjacent_emotions=("Fear", "Anticipation", "Despair"),
        taste="adrenaline", texture="gate closing",
        description="German: gate-closing panic — the frantic urgency that arrives when a window of opportunity is almost shut.",
    ),
    EmotionSignature(
        name="Waldeinsamkeit",
        hex_color="#228B22", rgb=(34, 139, 34),
        solfeggio_hz=528.0,
        eeg_center_hz=9.0, eeg_band="alpha",
        hrv_coherence_hz=0.10,
        valence=0.60, arousal=0.15,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="barnsley", fractal_param=0.70,
        adjacent_emotions=("Serenity", "Acceptance", "Wonder"),
        taste="moss", texture="deep canopy",
        description="German: the feeling of solitude and connection found deep in the forest — alone in the right way.",
    ),
    EmotionSignature(
        name="Kama Muta",
        hex_color="#FF9EAA", rgb=(255, 158, 170),
        solfeggio_hz=639.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.105,
        valence=0.85, arousal=0.65,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="golden_spiral", fractal_param=1.618,
        adjacent_emotions=("Love", "Gratitude", "Awe"),
        taste="sweetness that catches in the throat", texture="chest-opening",
        description="Sanskrit: being moved by love — the sudden warm flooding of the chest when witnessing deep tenderness.",
    ),
    EmotionSignature(
        name="Wabi-sabi",
        hex_color="#B5A290", rgb=(181, 162, 144),
        solfeggio_hz=285.0,
        eeg_center_hz=9.5, eeg_band="alpha",
        hrv_coherence_hz=0.09,
        valence=0.45, arousal=0.18,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="barnsley", fractal_param=0.45,
        adjacent_emotions=("Acceptance", "Mono no Aware", "Serenity"),
        taste="aged wood", texture="cracked glaze",
        description="Japanese: the beauty of imperfection, impermanence, and incompleteness — the crack that makes the bowl true.",
    ),

    # ── SOMATIC EMOTIONS ──────────────────────────────────────────────────────
    EmotionSignature(
        name="Frisson",
        hex_color="#E8D5F5", rgb=(232, 213, 245),
        solfeggio_hz=963.0,
        eeg_center_hz=42.0, eeg_band="gamma",
        hrv_coherence_hz=0.11,
        valence=0.80, arousal=0.85,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="julia", fractal_param=0.7,
        adjacent_emotions=("Awe", "Joy", "Wonder"),
        taste="electric citrus", texture="skin standing",
        description="The aesthetic chill — when music or beauty exceeds containment and erupts through the skin as goosebumps.",
    ),
    EmotionSignature(
        name="Flow",
        hex_color="#00CED1", rgb=(0, 206, 209),
        solfeggio_hz=528.0,
        eeg_center_hz=10.0, eeg_band="alpha",
        hrv_coherence_hz=0.10,
        valence=0.80, arousal=0.60,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="barnsley", fractal_param=0.88,
        adjacent_emotions=("Meraki", "Focus", "Joy"),
        taste="clean water", texture="frictionless motion",
        description="Csikszentmihalyi's optimal experience — consciousness and action fused, self-consciousness dissolved into the task.",
    ),
    EmotionSignature(
        name="Gut Feeling",
        hex_color="#8B6914", rgb=(139, 105, 20),
        solfeggio_hz=174.0,
        eeg_center_hz=4.0, eeg_band="theta",
        hrv_coherence_hz=0.08,
        valence=0.10, arousal=0.50,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="mandelbrot", fractal_param=0.3,
        adjacent_emotions=("Fear", "Anticipation", "Acceptance"),
        taste="earth", texture="knowing without words",
        description="Pre-cognitive somatic knowing — the body's intelligence arriving before the mind's translation.",
    ),
    EmotionSignature(
        name="Skin Hunger",
        hex_color="#E8A87C", rgb=(232, 168, 124),
        solfeggio_hz=639.0,
        eeg_center_hz=6.0, eeg_band="theta",
        hrv_coherence_hz=0.07,
        valence=-0.25, arousal=0.40,
        musical_mode="Aeolian", musical_mode_root_hz=MODE_ROOTS["Aeolian"],
        fractal_type="barnsley", fractal_param=0.55,
        adjacent_emotions=("Longing", "Sadness", "Love"),
        taste="salt", texture="ache for contact",
        description="Dermal yearning — the body's need for touch as a form of knowing and being known that words cannot reach.",
    ),
    EmotionSignature(
        name="Almost Sneeze",
        hex_color="#F0E68C", rgb=(240, 230, 140),
        solfeggio_hz=417.0,
        eeg_center_hz=18.0, eeg_band="beta",
        hrv_coherence_hz=0.06,
        valence=0.05, arousal=0.75,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="cantor", fractal_param=0.5,
        adjacent_emotions=("Anticipation", "Frustration", "Surprise"),
        taste="pepper", texture="suspended tension",
        description="The suspended moment of total physiological suspension before resolution — anticipation held entirely in the body.",
    ),

    # ── SOCIAL / RELATIONAL EMOTIONS ──────────────────────────────────────────
    EmotionSignature(
        name="Collective Effervescence",
        hex_color="#FFD700", rgb=(255, 215, 0),
        solfeggio_hz=963.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.11,
        valence=0.90, arousal=0.85,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="barnsley", fractal_param=0.95,
        adjacent_emotions=("Joy", "Ubuntu", "Euphoria"),
        taste="electricity", texture="crowd breathing as one",
        description="Durkheim's term: the energy generated when humans synchronize into a single emotional body — a crowd becoming a self.",
    ),
    EmotionSignature(
        name="Moral Elevation",
        hex_color="#B8D4E8", rgb=(184, 212, 232),
        solfeggio_hz=852.0,
        eeg_center_hz=38.0, eeg_band="gamma",
        hrv_coherence_hz=0.105,
        valence=0.80, arousal=0.55,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="golden_spiral", fractal_param=1.618,
        adjacent_emotions=("Awe", "Gratitude", "Kama Muta"),
        taste="clean air", texture="upward pull",
        description="Jonathan Haidt's concept: the warm, uplifting feeling of witnessing virtue — seeing goodness and wanting to become it.",
    ),
    EmotionSignature(
        name="Empathic Distress",
        hex_color="#8B4455", rgb=(139, 68, 85),
        solfeggio_hz=396.0,
        eeg_center_hz=20.0, eeg_band="beta",
        hrv_coherence_hz=0.055,
        valence=-0.70, arousal=0.70,
        musical_mode="Locrian", musical_mode_root_hz=MODE_ROOTS["Locrian"],
        fractal_type="julia", fractal_param=0.6,
        adjacent_emotions=("Sadness", "Fear", "Empathy"),
        taste="metallic", texture="absorbing another's pain",
        description="Feeling another's suffering so completely it overwhelms — the cost of having no wall between self and other.",
    ),
    EmotionSignature(
        name="Compersion",
        hex_color="#98FB98", rgb=(152, 251, 152),
        solfeggio_hz=639.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.85, arousal=0.55,
        musical_mode="Ionian", musical_mode_root_hz=MODE_ROOTS["Ionian"],
        fractal_type="barnsley", fractal_param=0.82,
        adjacent_emotions=("Joy", "Love", "Ubuntu"),
        taste="reflected sweetness", texture="warmth from across the room",
        description="Joy felt because someone you love is happy — vicarious delight with no envy, love that multiplies when shared.",
    ),
    EmotionSignature(
        name="Opia",
        hex_color="#2E4057", rgb=(46, 64, 87),
        solfeggio_hz=285.0,
        eeg_center_hz=8.0, eeg_band="alpha",
        hrv_coherence_hz=0.085,
        valence=0.20, arousal=0.55,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="mandelbrot", fractal_param=0.4,
        adjacent_emotions=("Vulnerability", "Curiosity", "Love"),
        taste="held breath", texture="the moment before recognition",
        description="The ambiguous intensity of eye contact — both intrusive and vulnerable, the discomfort of being truly seen.",
    ),

    # ── COGNITIVE EMOTIONS ────────────────────────────────────────────────────
    EmotionSignature(
        name="Aporia",
        hex_color="#9E9E9E", rgb=(158, 158, 158),
        solfeggio_hz=285.0,
        eeg_center_hz=12.0, eeg_band="alpha",
        hrv_coherence_hz=0.08,
        valence=-0.15, arousal=0.40,
        musical_mode="Locrian", musical_mode_root_hz=MODE_ROOTS["Locrian"],
        fractal_type="cantor", fractal_param=0.5,
        adjacent_emotions=("Distraction", "Curiosity", "Grief"),
        taste="plain water", texture="open ground with no path",
        description="Socratic genuine impasse — not confusion but the honest confrontation with a question that refuses to resolve.",
    ),
    EmotionSignature(
        name="Eureka",
        hex_color="#FFE135", rgb=(255, 225, 53),
        solfeggio_hz=963.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.11,
        valence=0.95, arousal=0.90,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="julia", fractal_param=0.8,
        adjacent_emotions=("Joy", "Surprise", "Wonder"),
        taste="sudden sweetness", texture="the moment the lock clicks",
        description="The collapse of cognitive tension into sudden coherence — when a pattern that was invisible becomes impossible to unsee.",
    ),
    EmotionSignature(
        name="Cognitive Dissonance",
        hex_color="#C0392B", rgb=(192, 57, 43),
        solfeggio_hz=741.0,
        eeg_center_hz=22.0, eeg_band="beta",
        hrv_coherence_hz=0.055,
        valence=-0.45, arousal=0.65,
        musical_mode="Phrygian", musical_mode_root_hz=MODE_ROOTS["Phrygian"],
        fractal_type="mandelbrot", fractal_param=0.6,
        adjacent_emotions=("Confusion", "Anxiety", "Aporia"),
        taste="sour and sweet simultaneously", texture="two forces at right angles",
        description="The discomfort of holding contradictory beliefs — the fractal that cannot decide which basin to fall into.",
    ),
    EmotionSignature(
        name="Epistemic Curiosity",
        hex_color="#00B4D8", rgb=(0, 180, 216),
        solfeggio_hz=852.0,
        eeg_center_hz=14.0, eeg_band="beta",
        hrv_coherence_hz=0.09,
        valence=0.70, arousal=0.70,
        musical_mode="Lydian", musical_mode_root_hz=MODE_ROOTS["Lydian"],
        fractal_type="barnsley", fractal_param=0.78,
        adjacent_emotions=("Curiosity", "Wonder", "Anticipation"),
        taste="cold spring water", texture="hunger without urgency",
        description="Curiosity as a value, not a reflex — the desire to know more so the world can be met more truly.",
    ),
    EmotionSignature(
        name="Sonder",
        hex_color="#7F8C8D", rgb=(127, 140, 141),
        solfeggio_hz=528.0,
        eeg_center_hz=8.0, eeg_band="alpha",
        hrv_coherence_hz=0.085,
        valence=0.10, arousal=0.18,
        musical_mode="Dorian", musical_mode_root_hz=MODE_ROOTS["Dorian"],
        fractal_type="mandelbrot", fractal_param=0.55,
        adjacent_emotions=("Wonder", "Acceptance", "Ubuntu"),
        taste="vast and mild", texture="a crowd seen from above",
        description="The realization that every passerby is living a life as vivid and complex as your own — the vertigo of other-ness.",
    ),
    EmotionSignature(
        name="Anagnorisis",
        hex_color="#D4AC0D", rgb=(212, 172, 13),
        solfeggio_hz=852.0,
        eeg_center_hz=40.0, eeg_band="gamma",
        hrv_coherence_hz=0.10,
        valence=0.30, arousal=0.75,
        musical_mode="Mixolydian", musical_mode_root_hz=MODE_ROOTS["Mixolydian"],
        fractal_type="julia", fractal_param=0.65,
        adjacent_emotions=("Surprise", "Grief", "Acceptance"),
        taste="bitter clarity", texture="the world re-arranging itself",
        description="Aristotle's recognition moment — the instant a character (or self) discovers the truth that was always there, reordering everything.",
    ),
)


def get_emotion(name: str) -> Optional[EmotionSignature]:
    return EMOTION_MAP.get(name.lower())


def nearest_emotion_by_rgb(r: int, g: int, b: int) -> EmotionSignature:
    """Find the closest emotion to an RGB color using Euclidean distance."""
    best, best_dist = None, float("inf")
    for em in EMOTION_MAP.values():
        d = ((em.rgb[0]-r)**2 + (em.rgb[1]-g)**2 + (em.rgb[2]-b)**2) ** 0.5
        if d < best_dist:
            best_dist = d
            best = em
    return best


def nearest_emotion_by_frequency(hz: float) -> EmotionSignature:
    """Find the closest emotion to a given frequency."""
    best, best_dist = None, float("inf")
    for em in EMOTION_MAP.values():
        d = abs(em.solfeggio_hz - hz)
        if d < best_dist:
            best_dist = d
            best = em
    return best


# Cultural/rare emotions that require significant V/A proximity to win over
# everyday emotions. A 3× distance penalty ensures joy, hope, calm, sadness
# register first; these only surface when text explicitly names them or the
# V/A coordinate is genuinely close to their position.
_RARE_EMOTION_NAMES: frozenset = frozenset({
    # Cultural/untranslatable
    "sonder", "mamihlapinatapai", "hiraeth", "saudade", "mono no aware",
    "sehnsucht", "fernweh", "waldeinsamkeit", "kama muta", "wabi-sabi",
    "schadenfreude", "weltschmerz", "torschlusspanik", "ubuntu",
    # Social/relational complex
    "opia", "collective effervescence", "moral elevation", "empathic distress", "compersion",
    # Somatic/liminal
    "frisson", "gut feeling", "skin hunger", "almost sneeze",
    # Cognitive (require specific context to surface)
    "aporia", "anagnorisis", "cognitive dissonance", "epistemic curiosity",
    # Creative/flow states (only when clearly context-appropriate)
    "meraki", "flow",
})


def emotions_by_valence_arousal(valence: float, arousal: float, top_n: int = 3) -> List[EmotionSignature]:
    """Return top_n emotions closest to a given valence/arousal coordinate.

    Cultural/rare emotions carry a 3× distance penalty so that everyday
    emotions (joy, calm, sadness, hope, interest, anger, fear …) register
    first for ordinary text.  Rare emotions only win when the V/A coordinate
    is strongly in their neighbourhood or their name appears as an explicit
    keyword in the text.
    """
    scored = []
    for em in EMOTION_MAP.values():
        d = ((em.valence - valence)**2 + (em.arousal - arousal)**2) ** 0.5
        if em.name.lower() in _RARE_EMOTION_NAMES:
            d *= 3.0
        scored.append((d, em))
    scored.sort(key=lambda x: x[0])
    return [em for _, em in scored[:top_n]]


def get_all_emotions() -> List[EmotionSignature]:
    return list(EMOTION_MAP.values())
