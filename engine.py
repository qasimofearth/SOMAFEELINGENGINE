"""
engine.py — The Feeling Engine Core

This is the recursive heart. Given an emotion (or a color, or a frequency,
or an image), the engine:

  1. Resolves it to an EmotionSignature
  2. Builds a recursive fractal emotion tree (Aya IFS structure)
  3. Translates through the synesthetic layer (color, sound, shape)
  4. Generates a frequency spectrum (the concert)
  5. Optionally synthesizes audio and renders fractal visuals

The recursion is the key truth: emotion is not a point, it's a structure.
Every feeling contains sub-feelings, which contain sub-sub-feelings,
exactly as every fern frond contains a smaller fern.
"""

import os
import math
from typing import Optional, List, Tuple, Union
import numpy as np

from .emotion_map import (
    EmotionSignature, EMOTION_MAP, get_emotion,
    nearest_emotion_by_rgb, nearest_emotion_by_frequency,
    emotions_by_valence_arousal, get_all_emotions,
)
from .fractal import (
    build_emotion_tree, tree_to_frequency_spectrum,
    emotion_modulated_transforms, barnsley_fern_points,
    EmotionNode, AYA_TRANSFORMS,
)
from .synesthesia import SynestheticReading, image_colors_to_emotions
from .concert import EmotionConcert


# ──────────────────────────────────────────────────────────────
# FEELING ENGINE
# ──────────────────────────────────────────────────────────────

class FeelingEngine:
    """
    The Feeling Engine.

    A recursive fractal system that bridges human emotional experience
    to mathematical/computational representation.

    Usage:
        engine = FeelingEngine()
        result = engine.feel("Joy")
        result = engine.feel_rgb(255, 105, 180)
        result = engine.feel_image("van_gogh_starry_night.jpg")
        result = engine.feel_valence_arousal(0.8, 0.6)
    """

    def __init__(self, max_depth: int = 5, output_dir: str = "./feeling_output"):
        self.max_depth = max_depth
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        os.makedirs(self.output_dir, exist_ok=True)

    # ── ENTRY POINTS ──────────────────────────────────────────

    def feel(
        self,
        emotion_name: str,
        intensity: float = 1.0,
        synthesize_audio: bool = True,
        render_fractal: bool = True,
    ) -> "FeelingResult":
        """
        Primary entry point: feel an emotion by name.
        """
        em = get_emotion(emotion_name)
        if em is None:
            available = ", ".join(sorted(EMOTION_MAP.keys()))
            raise ValueError(
                f"Unknown emotion: '{emotion_name}'\nAvailable: {available}"
            )
        return self._process(em, intensity, synthesize_audio, render_fractal)

    def feel_rgb(
        self,
        r: int, g: int, b: int,
        intensity: float = 1.0,
        synthesize_audio: bool = True,
        render_fractal: bool = True,
    ) -> "FeelingResult":
        """
        Feel an emotion from a color. The synesthetic path: color → emotion.
        """
        em = nearest_emotion_by_rgb(r, g, b)
        return self._process(em, intensity, synthesize_audio, render_fractal,
                             origin=f"RGB({r},{g},{b})")

    def feel_frequency(
        self,
        hz: float,
        intensity: float = 1.0,
        synthesize_audio: bool = True,
        render_fractal: bool = True,
    ) -> "FeelingResult":
        """
        Feel an emotion from a frequency. The synesthetic path: sound → emotion.
        """
        em = nearest_emotion_by_frequency(hz)
        return self._process(em, intensity, synthesize_audio, render_fractal,
                             origin=f"{hz:.2f} Hz")

    def feel_valence_arousal(
        self,
        valence: float,
        arousal: float,
        intensity: float = 1.0,
        synthesize_audio: bool = True,
        render_fractal: bool = True,
    ) -> "FeelingResult":
        """
        Feel from a psychophysiological coordinate (Russell's circumplex).
        valence: -1 (most negative) to +1 (most positive)
        arousal: 0 (inert) to 1 (maximally activated)
        """
        top_emotions = emotions_by_valence_arousal(valence, arousal, top_n=1)
        em = top_emotions[0] if top_emotions else list(EMOTION_MAP.values())[0]
        return self._process(em, intensity, synthesize_audio, render_fractal,
                             origin=f"valence={valence:+.2f} arousal={arousal:.2f}")

    def feel_image(
        self,
        image_path: str,
        synthesize_audio: bool = True,
        render_fractal: bool = True,
    ) -> "FeelingResult":
        """
        Feel the emotional content of a visual artwork.
        Extracts colors → maps to emotions → runs through engine.
        """
        from .art_processor import analyze_artwork, ArtReading

        reading = analyze_artwork(image_path)
        if not reading.emotion_weights:
            raise ValueError("Could not extract emotion data from image.")

        # Dominant emotion drives the fractal
        dom_em, dom_weight = reading.emotion_weights[0]

        # Build blended spectrum from all detected emotions
        spectrum = reading.frequency_spectrum()

        result = self._process(
            dom_em, dom_weight,
            synthesize_audio=synthesize_audio,
            render_fractal=render_fractal,
            origin=f"image:{os.path.basename(image_path)}",
            override_spectrum=spectrum,
        )
        result.art_reading = reading
        return result

    def concert_of_emotions(
        self,
        emotion_names: List[str],
        weights: Optional[List[float]] = None,
        duration_s: float = 12.0,
        synthesize_audio: bool = True,
    ) -> "FeelingResult":
        """
        Create a concert from multiple emotions simultaneously.
        Like a chord — all feelings sounding at once.
        """
        if weights is None:
            weights = [1.0 / len(emotion_names)] * len(emotion_names)

        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]

        combined_spectrum: List[Tuple[float, float]] = []
        primary_em = None
        primary_weight = 0.0

        for name, weight in zip(emotion_names, weights):
            em = get_emotion(name)
            if em is None:
                continue
            if weight > primary_weight:
                primary_em = em
                primary_weight = weight

            tree = build_emotion_tree(em.name, EMOTION_MAP, self.max_depth)
            spectrum = tree_to_frequency_spectrum(tree, EMOTION_MAP)
            for hz, amp in spectrum:
                combined_spectrum.append((hz, amp * weight))

        if primary_em is None:
            raise ValueError("No valid emotions provided.")

        return self._process(
            primary_em, 1.0,
            synthesize_audio=synthesize_audio,
            render_fractal=False,
            origin=f"concert:{'+'.join(emotion_names)}",
            override_spectrum=combined_spectrum,
            override_duration=duration_s,
        )

    # ── CORE PROCESSING PIPELINE ──────────────────────────────

    def _process(
        self,
        em: EmotionSignature,
        intensity: float,
        synthesize_audio: bool,
        render_fractal: bool,
        origin: str = "",
        override_spectrum: Optional[List[Tuple[float, float]]] = None,
        override_duration: Optional[float] = None,
    ) -> "FeelingResult":
        """
        The full pipeline. This IS the Feeling Engine running.
        """
        # 1. Synesthetic reading — translate emotion to all senses
        reading = SynestheticReading(em, intensity)

        # 2. Build Aya fractal emotion tree (recursive)
        tree = build_emotion_tree(em.name, EMOTION_MAP, self.max_depth)

        # 3. Derive frequency spectrum from the fractal tree
        if override_spectrum is not None:
            spectrum = override_spectrum
        else:
            spectrum = tree_to_frequency_spectrum(tree, EMOTION_MAP)

        # 4. Construct the concert
        duration = override_duration or (4.0 + intensity * 6.0)
        concert = EmotionConcert(
            spectrum=spectrum,
            duration_s=duration,
            include_binaural=True,
        )

        # 5. Modulate Aya transforms by this emotion
        transforms = emotion_modulated_transforms(em.valence, em.arousal)
        fractal_points = barnsley_fern_points(
            n_points=50_000, transforms=transforms, seed=7
        )

        # 6. Synthesize audio if requested
        audio_path = None
        if synthesize_audio:
            safe_name = em.name.lower().replace(" ", "_")
            if origin:
                safe_origin = origin[:20].replace(":", "_").replace("/", "_")
                safe_name = f"{safe_name}_{safe_origin}"
            audio_path = os.path.join(self.output_dir, f"{safe_name}.wav")
            concert.save_wav(audio_path)

        # 7. Render fractal visualization if requested
        fractal_path = None
        if render_fractal:
            fractal_path = self._render_fractal(
                em, fractal_points, tree,
                os.path.join(self.output_dir, f"aya_{em.name.lower()}.png")
            )

        return FeelingResult(
            emotion=em,
            intensity=intensity,
            origin=origin or em.name,
            synesthetic_reading=reading,
            emotion_tree=tree,
            frequency_spectrum=spectrum,
            concert=concert,
            fractal_points=fractal_points,
            audio_path=audio_path,
            fractal_path=fractal_path,
        )

    def _render_fractal(
        self,
        em: EmotionSignature,
        points: np.ndarray,
        tree: EmotionNode,
        output_path: str,
    ) -> Optional[str]:
        """Render the Aya fractal colored by the emotion, overlaid with the emotion tree."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            from matplotlib.colors import LinearSegmentedColormap

            r, g, b = em.rgb
            base_color = (r/255, g/255, b/255)

            # Build colormap from black → emotion color → white
            cmap = LinearSegmentedColormap.from_list(
                em.name,
                [(0, 0, 0), base_color, (1, 1, 1)],
            )

            fig = plt.figure(figsize=(12, 8), facecolor="#050510")
            gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=0.05)

            # LEFT — Aya Fractal
            ax_fern = fig.add_subplot(gs[0], facecolor="#050510")
            y_norm = (points[:, 1] - points[:, 1].min()) / (
                points[:, 1].max() - points[:, 1].min() + 1e-8
            )
            colors_arr = cmap(y_norm)
            colors_arr[:, 3] = 0.08 + y_norm * 0.55  # alpha by height

            ax_fern.scatter(
                points[:, 0], points[:, 1],
                c=colors_arr, s=0.15, linewidths=0, rasterized=True
            )
            ax_fern.set_xlim(-3, 3)
            ax_fern.set_ylim(-0.5, 11.5)
            ax_fern.axis("off")
            ax_fern.set_title(
                f"AYA — {em.name.upper()}",
                color="white", fontsize=16, fontweight="bold",
                pad=12, fontfamily="monospace"
            )

            # RIGHT — Emotion tree + data panel
            ax_data = fig.add_subplot(gs[1], facecolor="#080820")
            ax_data.axis("off")

            # Draw emotion tree as a mini diagram
            self._draw_tree_panel(ax_data, tree, em, base_color)

            plt.savefig(
                output_path, dpi=120, bbox_inches="tight",
                facecolor="#050510", edgecolor="none"
            )
            plt.close(fig)
            return output_path

        except ImportError:
            return None
        except Exception as e:
            print(f"  [fractal render skipped: {e}]")
            return None

    def _draw_tree_panel(self, ax, tree: EmotionNode, em: EmotionSignature, base_color):
        """Draw a visual tree of emotions on the right panel."""
        reading = SynestheticReading(em, 1.0)
        lines = [
            f"  {em.name}",
            f"  {'─'*24}",
            f"  Color    #{em.hex_color}",
            f"  Solfeggio {em.solfeggio_hz:.0f} Hz",
            f"  EEG band  {em.eeg_band} ({em.eeg_center_hz:.0f} Hz)",
            f"  HRV       {em.hrv_coherence_hz:.4f} Hz",
            f"  Mode      {em.musical_mode}",
            f"  Valence   {em.valence:+.2f}",
            f"  Arousal   {em.arousal:.2f}",
            f"  Fractal   {em.fractal_type}",
            f"  Taste     {em.taste}",
            f"  Texture   {em.texture}",
            "",
            f"  Sub-emotions:",
        ]
        for child in tree.children:
            lines.append(f"    ↳ {child.emotion_name}  (w={child.weight:.2f})")
            for grandchild in child.children:
                lines.append(f"       ↳ {grandchild.emotion_name}  (w={grandchild.weight:.3f})")

        text = "\n".join(lines)
        ax.text(
            0.05, 0.95, text,
            transform=ax.transAxes,
            fontfamily="monospace", fontsize=9,
            color="white", verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#0a0a30",
                      alpha=0.85, edgecolor=base_color, linewidth=1.5),
        )

        # Emotion description
        ax.text(
            0.05, 0.12, f'"{em.description}"',
            transform=ax.transAxes,
            fontfamily="monospace", fontsize=8,
            color="lightgray", verticalalignment="bottom",
            style="italic", wrap=True,
            bbox=dict(boxstyle="round", facecolor="#050518", alpha=0.7,
                      edgecolor="gray", linewidth=0.5),
        )


# ──────────────────────────────────────────────────────────────
# FEELING RESULT
# ──────────────────────────────────────────────────────────────

class FeelingResult:
    """
    Everything the Feeling Engine computed for one emotional input.
    """

    def __init__(
        self,
        emotion: EmotionSignature,
        intensity: float,
        origin: str,
        synesthetic_reading: SynestheticReading,
        emotion_tree: EmotionNode,
        frequency_spectrum: List[Tuple[float, float]],
        concert: EmotionConcert,
        fractal_points: np.ndarray,
        audio_path: Optional[str] = None,
        fractal_path: Optional[str] = None,
    ):
        self.emotion = emotion
        self.intensity = intensity
        self.origin = origin
        self.synesthetic_reading = synesthetic_reading
        self.emotion_tree = emotion_tree
        self.frequency_spectrum = frequency_spectrum
        self.concert = concert
        self.fractal_points = fractal_points
        self.audio_path = audio_path
        self.fractal_path = fractal_path
        self.art_reading = None  # set by feel_image()

    def report(self) -> str:
        lines = [
            "╔" + "═"*62,
            "║  FEELING ENGINE — FULL REPORT",
            "║  Origin: " + self.origin,
            "╠" + "═"*62,
            "",
            self.synesthetic_reading.describe(),
            "",
            "── Fractal Emotion Tree (" + f"depth={self._tree_depth()}" + ") ──",
            self._format_tree(self.emotion_tree),
            "",
            self.concert.spectrum_report(),
            "",
        ]
        if self.audio_path:
            lines.append(f"  Audio file    : {self.audio_path}")
        if self.fractal_path:
            lines.append(f"  Fractal image : {self.fractal_path}")
        if self.art_reading:
            lines.append("")
            lines.append(self.art_reading.describe())

        lines.append("╚" + "═"*62)
        return "\n".join(lines)

    def _tree_depth(self) -> int:
        def depth(node):
            if not node.children:
                return 0
            return 1 + max(depth(c) for c in node.children)
        return depth(self.emotion_tree)

    def _format_tree(self, node: EmotionNode, prefix: str = "", is_last: bool = True) -> str:
        connector = "└─" if is_last else "├─"
        em = EMOTION_MAP.get(node.emotion_name.lower())
        freq = f"{em.solfeggio_hz:.0f}Hz" if em else "?"
        color = em.hex_color if em else "?"
        line = f"{prefix}{connector} {node.emotion_name}  [{freq}  #{color}  w={node.weight:.3f}]"
        lines = [line]
        child_prefix = prefix + ("   " if is_last else "│  ")
        for i, child in enumerate(node.children):
            is_child_last = (i == len(node.children) - 1)
            lines.append(self._format_tree(child, child_prefix, is_child_last))
        return "\n".join(lines)
