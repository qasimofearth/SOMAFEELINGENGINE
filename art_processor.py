"""
art_processor.py — Feed the engine with human art

Extracts dominant colors from paintings/images,
maps them through the synesthetic layer to emotions,
and returns a full emotional reading of the artwork.

This is how the Feeling Engine "learns" from art —
every painting is a set of frequencies, and frequencies are feelings.
"""

import os
import io
import math
import struct
from typing import List, Tuple, Optional, Dict
from collections import Counter
import numpy as np


# ──────────────────────────────────────────────────────────────
# COLOR EXTRACTION (no heavy dependencies — pure Python)
# ──────────────────────────────────────────────────────────────

def sample_image_colors(
    image_path: str,
    n_samples: int = 500,
) -> List[Tuple[int, int, int, float]]:
    """
    Extract color samples from an image file.
    Returns list of (r, g, b, weight) — weight = relative frequency.

    Supports: PNG, JPG/JPEG (via PIL/Pillow if available, fallback for PNG).
    """
    try:
        from PIL import Image
        return _sample_via_pillow(image_path, n_samples)
    except ImportError:
        pass

    # Minimal PNG fallback
    if image_path.lower().endswith(".png"):
        return _sample_png_fallback(image_path, n_samples)

    raise RuntimeError(
        "Pillow not installed. Run: pip install Pillow\n"
        "Or provide a .png file for the minimal fallback."
    )


def _sample_via_pillow(path: str, n_samples: int) -> List[Tuple[int, int, int, float]]:
    """Extract colors using Pillow."""
    from PIL import Image
    img = Image.open(path).convert("RGB")

    # Resize for performance
    max_dim = 200
    w, h = img.size
    if w > max_dim or h > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)

    pixels = list(img.getdata())

    # Quantize to reduce noise (bucket RGB to nearest 16)
    quantized = []
    for r, g, b in pixels:
        qr = (r // 32) * 32
        qg = (g // 32) * 32
        qb = (b // 32) * 32
        quantized.append((qr, qg, qb))

    counts = Counter(quantized)
    total = sum(counts.values())

    result = []
    for (r, g, b), count in counts.most_common(n_samples):
        result.append((r, g, b, count / total))
    return result


def _sample_png_fallback(path: str, n_samples: int) -> List[Tuple[int, int, int, float]]:
    """Very basic PNG reader without PIL — handles uncompressed or simple PNGs."""
    # This is a best-effort fallback; real images will want PIL
    try:
        import zlib
        with open(path, "rb") as f:
            data = f.read()

        # Parse PNG header and IHDR
        assert data[:8] == b'\x89PNG\r\n\x1a\n', "Not a PNG"

        offset = 8
        chunks = {}
        while offset < len(data):
            length = struct.unpack(">I", data[offset:offset+4])[0]
            chunk_type = data[offset+4:offset+8].decode("ascii", errors="replace")
            chunk_data = data[offset+8:offset+8+length]
            chunks.setdefault(chunk_type, []).append(chunk_data)
            offset += 12 + length

        ihdr = chunks["IHDR"][0]
        width = struct.unpack(">I", ihdr[0:4])[0]
        height = struct.unpack(">I", ihdr[4:8])[0]
        bit_depth = ihdr[8]
        color_type = ihdr[9]

        # Only handle 8-bit RGB (color_type=2)
        if bit_depth != 8 or color_type != 2:
            return _synthetic_palette()

        raw = zlib.decompress(b"".join(chunks.get("IDAT", [])))

        pixels = []
        row_size = 1 + width * 3
        for y in range(height):
            row = raw[y * row_size: (y+1) * row_size]
            for x in range(width):
                r = row[1 + x*3]
                g = row[2 + x*3]
                b = row[3 + x*3]
                pixels.append((r, g, b))

        quantized = [((r//32)*32, (g//32)*32, (b//32)*32) for r, g, b in pixels]
        counts = Counter(quantized)
        total = sum(counts.values())
        return [(r, g, b, c/total) for (r, g, b), c in counts.most_common(n_samples)]

    except Exception:
        return _synthetic_palette()


def _synthetic_palette() -> List[Tuple[int, int, int, float]]:
    """Fallback: return a balanced palette of primary colors."""
    palette = [
        (255, 0, 0, 0.15),    # red
        (0, 0, 200, 0.15),    # blue
        (0, 180, 0, 0.15),    # green
        (255, 215, 0, 0.20),  # yellow
        (128, 0, 128, 0.10),  # purple
        (255, 140, 0, 0.10),  # orange
        (0, 128, 128, 0.05),  # teal
        (200, 200, 200, 0.10), # gray
    ]
    return palette


# ──────────────────────────────────────────────────────────────
# ART EMOTIONAL ANALYSIS
# ──────────────────────────────────────────────────────────────

class ArtReading:
    """
    A complete emotional reading of a piece of visual art.

    The reading flows: image → colors → emotions → frequencies → fractal.
    This is the Feeling Engine processing art as emotional data.
    """

    def __init__(
        self,
        title: str,
        color_palette: List[Tuple[int, int, int, float]],
        emotion_weights: List[Tuple[object, float]],  # (EmotionSignature, weight)
    ):
        self.title = title
        self.color_palette = color_palette
        self.emotion_weights = emotion_weights

    @property
    def dominant_emotion(self):
        if self.emotion_weights:
            return self.emotion_weights[0][0]
        return None

    @property
    def emotional_temperature(self) -> float:
        """
        Weighted average valence of all detected emotions.
        +1 = purely positive/warm, -1 = purely negative/cold.
        """
        if not self.emotion_weights:
            return 0.0
        total_weight = sum(w for _, w in self.emotion_weights)
        weighted_valence = sum(em.valence * w for em, w in self.emotion_weights)
        return weighted_valence / total_weight if total_weight else 0.0

    @property
    def emotional_energy(self) -> float:
        """Weighted average arousal — how activating is this artwork?"""
        if not self.emotion_weights:
            return 0.0
        total_weight = sum(w for _, w in self.emotion_weights)
        weighted_arousal = sum(em.arousal * w for em, w in self.emotion_weights)
        return weighted_arousal / total_weight if total_weight else 0.0

    @property
    def composite_frequency_hz(self) -> float:
        """
        The dominant frequency of this artwork's emotional content.
        A weighted average of all emotion frequencies.
        """
        if not self.emotion_weights:
            return 528.0
        total_weight = sum(w for _, w in self.emotion_weights)
        weighted_freq = sum(em.solfeggio_hz * w for em, w in self.emotion_weights)
        return weighted_freq / total_weight if total_weight else 528.0

    @property
    def composite_rgb(self) -> Tuple[int, int, int]:
        """The emotional color of this artwork — weighted blend of emotion colors."""
        if not self.emotion_weights:
            return (128, 128, 128)
        total_weight = sum(w for _, w in self.emotion_weights)
        r = sum(em.rgb[0] * w for em, w in self.emotion_weights) / total_weight
        g = sum(em.rgb[1] * w for em, w in self.emotion_weights) / total_weight
        b = sum(em.rgb[2] * w for em, w in self.emotion_weights) / total_weight
        return (int(r), int(g), int(b))

    def frequency_spectrum(self) -> List[Tuple[float, float]]:
        """Convert emotion weights to a frequency spectrum for the concert."""
        spectrum = []
        for em, weight in self.emotion_weights:
            for freq in em.frequency_vector:
                if freq > 0:
                    spectrum.append((freq, weight))
        return spectrum

    def describe(self) -> str:
        cr, cg, cb = self.composite_rgb
        lines = [
            f"╔══ ART READING: {self.title} ══",
            f"║",
            f"║  Dominant emotion : {self.dominant_emotion.name if self.dominant_emotion else 'unknown'}",
            f"║  Emotional temp.  : {self.emotional_temperature:+.3f}  ({'warm' if self.emotional_temperature > 0 else 'cold'})",
            f"║  Emotional energy : {self.emotional_energy:.3f}  ({'activating' if self.emotional_energy > 0.5 else 'calming'})",
            f"║  Composite freq.  : {self.composite_frequency_hz:.1f} Hz",
            f"║  Composite color  : RGB({cr},{cg},{cb})",
            f"║",
            f"║  Emotional palette:",
        ]
        for em, w in self.emotion_weights:
            bar = "▓" * int(w * 30)
            lines.append(f"║    {em.name:<16} {w:.3f}  {bar}  #{em.hex_color}")
        lines.append("╚" + "═" * 50)
        return "\n".join(lines)


def analyze_artwork(
    image_path: str,
    title: Optional[str] = None,
    n_colors: int = 200,
) -> ArtReading:
    """
    Full pipeline: image file → ArtReading.
    Extracts colors, maps to emotions, returns reading.
    """
    from .synesthesia import image_colors_to_emotions

    if title is None:
        title = os.path.basename(image_path)

    palette = sample_image_colors(image_path, n_samples=n_colors)
    emotion_weights = image_colors_to_emotions(palette, top_n=8)

    return ArtReading(
        title=title,
        color_palette=palette,
        emotion_weights=emotion_weights,
    )


def generate_synthetic_artwork(
    emotion_name: str,
    width: int = 400,
    height: int = 400,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """
    Generate a synthetic artwork (PNG) that represents an emotion,
    using the fractal Aya pattern colored by the emotion's palette.
    Returns filepath if saved.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import to_rgba
        from .emotion_map import get_emotion
        from .fractal import barnsley_fern_points, emotion_modulated_transforms

        em = get_emotion(emotion_name)
        if em is None:
            return None

        transforms = emotion_modulated_transforms(em.valence, em.arousal)
        points = barnsley_fern_points(80_000, transforms, seed=42)

        fig, ax = plt.subplots(figsize=(6, 6), facecolor="black")
        r, g, b = em.rgb
        base_color = (r/255, g/255, b/255)

        # Color by height (y coordinate) — deeper = more core emotion
        y_norm = (points[:, 1] - points[:, 1].min()) / (points[:, 1].max() - points[:, 1].min() + 1e-8)
        colors = np.zeros((len(points), 4))
        colors[:, 0] = base_color[0] * y_norm + 0.1
        colors[:, 1] = base_color[1] * y_norm + 0.05
        colors[:, 2] = base_color[2] * y_norm + 0.1
        colors[:, 3] = 0.15 + y_norm * 0.5

        ax.scatter(points[:, 0], points[:, 1], c=colors, s=0.2, linewidths=0)
        ax.set_xlim(-3, 3); ax.set_ylim(0, 11)
        ax.axis("off")
        ax.set_title(f"Aya — {em.name}", color="white", fontsize=14, pad=10)
        plt.tight_layout()

        if output_path is None:
            output_path = f"aya_{emotion_name.lower()}.png"

        plt.savefig(output_path, dpi=100, bbox_inches="tight", facecolor="black")
        plt.close(fig)
        return output_path

    except ImportError:
        return None
