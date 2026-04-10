"""
fractal.py — The Aya Fractal Engine

Implements the recursive structure of the Feeling Engine using the Barnsley
fern IFS (Iterated Function System) — the direct mathematical analogue of
the Aya Adinkra symbol (Ghana fern symbol of endurance and self-renewal).

Also implements: Mandelbrot set, Julia sets, Cantor set, and golden spiral —
each used as the geometric home of different emotional families.

The Aya recursion is the engine's heartbeat:
  each emotion IS a transformation, and the engine applies those
  transformations recursively, exactly as the fern builds itself —
  same rule, different scales, infinite depth.
"""

import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional
import numpy as np


# ──────────────────────────────────────────────────────────────
# AYA / BARNSLEY FERN — IFS Core
# ──────────────────────────────────────────────────────────────

@dataclass
class AffineTransform:
    """One branch of the fern — one recursive rule."""
    a: float; b: float; c: float; d: float; e: float; f: float
    probability: float
    name: str = ""

    def apply(self, x: float, y: float) -> Tuple[float, float]:
        return (self.a*x + self.b*y + self.e,
                self.c*x + self.d*y + self.f)


# The Barnsley fern — mathematical twin of the Aya symbol
AYA_TRANSFORMS = [
    AffineTransform(0, 0, 0, 0.16, 0, 0, 0.01, "stem"),          # 1% — the trunk
    AffineTransform(0.85, 0.04, -0.04, 0.85, 0, 1.60, 0.85, "leaf"),   # 85% — leaflets
    AffineTransform(0.20, -0.26, 0.23, 0.22, 0, 1.60, 0.07, "left"),   # 7% — left sub-frond
    AffineTransform(-0.15, 0.28, 0.26, 0.24, 0, 0.44, 0.07, "right"),  # 7% — right sub-frond
]


def barnsley_fern_points(
    n_points: int = 100_000,
    transforms: List[AffineTransform] = None,
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Run the chaos game on the Barnsley/Aya IFS.
    Returns (n_points, 2) array of [x, y] coordinates.
    """
    if transforms is None:
        transforms = AYA_TRANSFORMS
    if seed is not None:
        random.seed(seed)

    points = np.zeros((n_points, 2))
    x, y = 0.0, 0.0
    probs = [t.probability for t in transforms]
    cumulative = []
    acc = 0.0
    for p in probs:
        acc += p
        cumulative.append(acc)

    for i in range(n_points):
        r = random.random()
        for j, threshold in enumerate(cumulative):
            if r <= threshold:
                x, y = transforms[j].apply(x, y)
                break
        points[i] = [x, y]

    return points


def emotion_modulated_transforms(
    emotion_valence: float,
    emotion_arousal: float,
    base_transforms: List[AffineTransform] = None,
) -> List[AffineTransform]:
    """
    Modulate the Aya transforms by an emotion's valence and arousal.

    Positive valence → increases the leaflet probability (growth-oriented)
    Negative valence → increases the stem probability (inward, contracted)
    High arousal → expands the left/right sub-fronds (chaotic branching)
    Low arousal → reduces sub-frond weight (calm, ordered)
    """
    if base_transforms is None:
        base_transforms = AYA_TRANSFORMS

    # Normalize emotion axes
    v = (emotion_valence + 1) / 2   # [0,1], 1 = maximally positive
    a = emotion_arousal              # [0,1], 1 = maximally aroused

    # Redistribute probabilities
    stem_p = 0.01 + (1 - v) * 0.08          # sad/negative → more stem weight
    leaf_p = 0.50 + v * 0.40                 # positive → lush leaves
    side_p = (1 - stem_p - leaf_p) / 2 * (0.5 + a) * 1.2  # arousal → more chaotic branches

    # Re-normalize to sum=1
    total = stem_p + leaf_p + side_p * 2
    stem_p /= total
    leaf_p /= total
    side_p = (1 - stem_p - leaf_p) / 2

    # Scale factor: positive / high arousal → taller, more expanded fern
    scale = 0.70 + v * 0.30
    lean = (emotion_valence) * 0.05  # positive emotions lean slightly outward

    return [
        AffineTransform(0, 0, 0, 0.16 * scale, 0, 0, stem_p, "stem"),
        AffineTransform(0.85 + lean, 0.04, -0.04, 0.85, 0, 1.60 * scale, leaf_p, "leaf"),
        AffineTransform(0.20 + a*0.05, -0.26, 0.23, 0.22, 0, 1.60 * scale, side_p, "left"),
        AffineTransform(-0.15 - a*0.05, 0.28, 0.26, 0.24, 0, 0.44, side_p, "right"),
    ]


# ──────────────────────────────────────────────────────────────
# MANDELBROT SET
# ──────────────────────────────────────────────────────────────

def mandelbrot_escape(c: complex, max_iter: int = 256) -> int:
    """Return iteration count for escape (or max_iter if stable)."""
    z = 0j
    for i in range(max_iter):
        z = z*z + c
        if abs(z) > 2:
            return i
    return max_iter


def mandelbrot_field(
    xmin=-2.5, xmax=1.0, ymin=-1.25, ymax=1.25,
    width=400, height=300, max_iter=128
) -> np.ndarray:
    """Return a 2D array of escape times (the Mandelbrot field)."""
    field = np.zeros((height, width), dtype=np.float32)
    for iy, y in enumerate(np.linspace(ymin, ymax, height)):
        for ix, x in enumerate(np.linspace(xmin, xmax, width)):
            field[iy, ix] = mandelbrot_escape(complex(x, y), max_iter)
    return field / max_iter   # normalize to [0,1]


# ──────────────────────────────────────────────────────────────
# JULIA SET
# ──────────────────────────────────────────────────────────────

def julia_escape(z: complex, c: complex, max_iter: int = 256) -> int:
    for i in range(max_iter):
        z = z*z + c
        if abs(z) > 2:
            return i
    return max_iter


def julia_field(
    c: complex,
    xmin=-1.5, xmax=1.5, ymin=-1.5, ymax=1.5,
    width=400, height=400, max_iter=128
) -> np.ndarray:
    """Julia set field for a fixed c parameter."""
    field = np.zeros((height, width), dtype=np.float32)
    for iy, y in enumerate(np.linspace(ymin, ymax, height)):
        for ix, x in enumerate(np.linspace(xmin, xmax, width)):
            field[iy, ix] = julia_escape(complex(x, y), c, max_iter)
    return field / max_iter


# ──────────────────────────────────────────────────────────────
# CANTOR SET — Grief, Boredom, Terror
# ──────────────────────────────────────────────────────────────

def cantor_set(n_iterations: int = 7, removal_fraction: float = 1/3) -> List[Tuple[float,float]]:
    """
    Return list of line segments remaining after n_iterations of Cantor removal.
    Starts with [0, 1], removes middle fraction at each iteration.
    """
    segments = [(0.0, 1.0)]
    for _ in range(n_iterations):
        new_segs = []
        for left, right in segments:
            length = right - left
            gap_start = left + length * (0.5 - removal_fraction/2)
            gap_end   = left + length * (0.5 + removal_fraction/2)
            new_segs.append((left, gap_start))
            new_segs.append((gap_end, right))
        segments = new_segs
    return segments


# ──────────────────────────────────────────────────────────────
# GOLDEN SPIRAL — Love, Pride, Ecstasy
# ──────────────────────────────────────────────────────────────

PHI = (1 + math.sqrt(5)) / 2   # golden ratio 1.6180...

def golden_spiral_points(n_turns: float = 5.0, n_points: int = 1000) -> np.ndarray:
    """
    Parametric golden spiral: r = e^(b*theta) where b = ln(phi)/(pi/2)
    Returns (n_points, 2) array.
    """
    b = math.log(PHI) / (math.pi / 2)
    theta = np.linspace(0, n_turns * 2 * math.pi, n_points)
    r = np.exp(b * theta)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.stack([x, y], axis=1)


# ──────────────────────────────────────────────────────────────
# RECURSIVE EMOTION TREE — The Feeling Engine's Spine
# ──────────────────────────────────────────────────────────────

@dataclass
class EmotionNode:
    """One node in the recursive fractal emotion tree."""
    emotion_name: str
    depth: int
    weight: float                    # intensity of this emotion at this scale
    children: List["EmotionNode"] = None
    x: float = 0.0                   # fractal coordinate
    y: float = 0.0

    def __post_init__(self):
        if self.children is None:
            self.children = []

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def all_leaves(self) -> List["EmotionNode"]:
        if self.is_leaf:
            return [self]
        result = []
        for child in self.children:
            result.extend(child.all_leaves())
        return result

    def flatten(self) -> List["EmotionNode"]:
        result = [self]
        for child in self.children:
            result.extend(child.flatten())
        return result


def build_emotion_tree(
    emotion_name: str,
    emotion_map: dict,
    max_depth: int = 5,
    weight: float = 1.0,
    depth: int = 0,
    visited: set = None,
    x: float = 0.0,
    y: float = 0.0,
) -> EmotionNode:
    """
    Recursively build a fractal emotion tree from an initial emotion.

    Each emotion's adjacent emotions become children at the next depth level,
    weighted by the Barnsley fern probability distribution (0.85/0.07/0.07/0.01).
    This mirrors exactly how the Aya fern generates itself — the same recursive
    rule applied at each scale.

    max_depth=5 → 5 levels of recursive emotional sub-structure,
    matching the 5–8 useful recursion depths of the physical fern.
    """
    if visited is None:
        visited = set()

    node = EmotionNode(
        emotion_name=emotion_name,
        depth=depth,
        weight=weight,
        x=x, y=y,
    )

    if depth >= max_depth:
        return node

    em = emotion_map.get(emotion_name.lower())
    if em is None:
        return node

    adjacent = [a for a in em.adjacent_emotions if a.lower() not in visited]
    if not adjacent:
        return node

    visited = visited | {emotion_name.lower()}

    # Apply Aya-like weighting: first child gets 85%, rest split the remainder
    weights = []
    if len(adjacent) == 1:
        weights = [0.85]
    elif len(adjacent) == 2:
        weights = [0.85, 0.15]
    else:
        weights = [0.85] + [0.15 / (len(adjacent)-1)] * (len(adjacent)-1)

    # Apply the IFS transforms to generate child positions
    transforms_to_use = AYA_TRANSFORMS[1:]  # skip stem for sub-emotions
    for i, (adj_name, child_weight) in enumerate(zip(adjacent, weights)):
        t = transforms_to_use[i % len(transforms_to_use)]
        cx, cy = t.apply(x, y)
        child = build_emotion_tree(
            emotion_name=adj_name,
            emotion_map=emotion_map,
            max_depth=max_depth,
            weight=weight * child_weight,
            depth=depth + 1,
            visited=visited,
            x=cx, y=cy,
        )
        node.children.append(child)

    return node


def tree_to_frequency_spectrum(
    tree: EmotionNode,
    emotion_map: dict,
) -> List[Tuple[float, float]]:
    """
    Flatten an emotion tree into a list of (frequency_hz, amplitude) pairs.
    This IS the "concert" — every emotion and sub-emotion playing its frequency,
    weighted by depth and intensity.
    The fractal structure means deeper emotions play at lower amplitude,
    recreating the self-similar frequency spectrum of nature itself.
    """
    spectrum = []
    for node in tree.flatten():
        em = emotion_map.get(node.emotion_name.lower())
        if em is None:
            continue
        # Amplitude decays with depth (like IFS transform scale factors)
        amplitude = node.weight * (0.85 ** node.depth)
        # Multiple frequency channels per emotion
        for freq in em.frequency_vector:
            if freq > 0:
                spectrum.append((freq, amplitude))
    return spectrum
