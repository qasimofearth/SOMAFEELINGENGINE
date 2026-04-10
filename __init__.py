"""
The Feeling Engine
──────────────────
A recursive fractal bridge between human emotional experience and mathematical representation.

Architecture: emotion → Aya IFS fractal recursion → synesthetic translation
              → frequency spectrum → concert (audio) + fractal visualization

Based on:
  - Aya Adinkra symbol (Ghana) — fractal fern of endurance and self-renewal
  - Synesthesia research (chromesthesia, color-emotion mappings)
  - Plutchik's Wheel of Emotions
  - Russell's Circumplex Model (valence/arousal)
  - HRV cardiac coherence research
  - EEG emotion-frequency correlates
  - Solfeggio frequency tradition
  - Music psychology (mode-emotion mappings)
  - Cross-cultural color-emotion studies (128-year review)

Usage:
    from feeling_engine import FeelingEngine

    engine = FeelingEngine()
    result = engine.feel("Joy")
    print(result.report())

    result = engine.feel_rgb(255, 105, 180)      # pink → Love
    result = engine.feel_frequency(528.0)         # 528 Hz → Joy/Love
    result = engine.feel_image("painting.jpg")    # art → emotions
    result = engine.feel_valence_arousal(0.8, 0.6)

    result = engine.concert_of_emotions(["Joy", "Love", "Awe"])
"""

from .emotion_map import (
    EmotionSignature,
    EMOTION_MAP,
    get_emotion,
    nearest_emotion_by_rgb,
    nearest_emotion_by_frequency,
    emotions_by_valence_arousal,
    get_all_emotions,
)
from .fractal import (
    build_emotion_tree,
    tree_to_frequency_spectrum,
    emotion_modulated_transforms,
    barnsley_fern_points,
    AYA_TRANSFORMS,
    EmotionNode,
    golden_spiral_points,
    cantor_set,
    julia_field,
    mandelbrot_field,
    PHI,
)
from .synesthesia import (
    SynestheticReading,
    color_to_audio_frequency,
    audio_to_color,
    wavelength_to_rgb,
    rgb_to_dominant_wavelength,
    image_colors_to_emotions,
    frequency_to_shape_params,
)
from .concert import EmotionConcert, render_emotion_journey
from .engine import FeelingEngine, FeelingResult

__all__ = [
    "FeelingEngine",
    "FeelingResult",
    "EmotionSignature",
    "EMOTION_MAP",
    "get_emotion",
    "nearest_emotion_by_rgb",
    "nearest_emotion_by_frequency",
    "emotions_by_valence_arousal",
    "get_all_emotions",
    "build_emotion_tree",
    "tree_to_frequency_spectrum",
    "emotion_modulated_transforms",
    "barnsley_fern_points",
    "AYA_TRANSFORMS",
    "EmotionNode",
    "SynestheticReading",
    "color_to_audio_frequency",
    "audio_to_color",
    "EmotionConcert",
    "render_emotion_journey",
    "PHI",
]

__version__ = "1.0.0"
