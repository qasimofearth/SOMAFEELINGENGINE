"""
synesthesia.py — Cross-modal translation layer

The bridge between all sensory dimensions of emotion.
Implements the synesthetic logic: color → sound, sound → color,
emotion → all senses simultaneously.

Based on documented chromesthesia research (Scriabin, Rimsky-Korsakov,
Ward et al.), cross-cultural color-emotion studies, and
HRV/EEG correlate data.
"""

import math
import colorsys
from typing import Tuple, Optional, List, Dict
import numpy as np

from .emotion_map import EmotionSignature, get_all_emotions, nearest_emotion_by_rgb, EMOTION_MAP


# ──────────────────────────────────────────────────────────────
# COLOR ↔ FREQUENCY TRANSLATION
# ──────────────────────────────────────────────────────────────

# Visible light spectrum: ~380nm (violet) to ~740nm (red)
# Map to audio: 20 Hz – 20,000 Hz
LIGHT_MIN_NM = 380.0
LIGHT_MAX_NM = 740.0
AUDIO_MIN_HZ = 20.0
AUDIO_MAX_HZ = 20000.0


def wavelength_to_rgb(nm: float) -> Tuple[int, int, int]:
    """
    Convert a light wavelength (nm) to approximate RGB.
    Based on CIE color matching approximation.
    """
    if nm < 380 or nm > 750:
        return (0, 0, 0)

    r = g = b = 0.0

    if 380 <= nm < 440:
        r = -(nm - 440) / (440 - 380)
        b = 1.0
    elif 440 <= nm < 490:
        g = (nm - 440) / (490 - 440)
        b = 1.0
    elif 490 <= nm < 510:
        g = 1.0
        b = -(nm - 510) / (510 - 490)
    elif 510 <= nm < 580:
        r = (nm - 510) / (580 - 510)
        g = 1.0
    elif 580 <= nm < 645:
        r = 1.0
        g = -(nm - 645) / (645 - 580)
    elif 645 <= nm <= 750:
        r = 1.0

    # Intensity correction at spectrum edges
    if 380 <= nm < 420:
        factor = 0.3 + 0.7 * (nm - 380) / (420 - 380)
    elif 420 <= nm <= 700:
        factor = 1.0
    elif 700 < nm <= 750:
        factor = 0.3 + 0.7 * (750 - nm) / (750 - 700)
    else:
        factor = 0.0

    return (
        int(round(255 * (r * factor) ** 0.8)),
        int(round(255 * (g * factor) ** 0.8)),
        int(round(255 * (b * factor) ** 0.8)),
    )


def rgb_to_dominant_wavelength(r: int, g: int, b: int) -> float:
    """
    Map an RGB color to a dominant light wavelength (nm).
    Uses hue angle as primary mapping.
    """
    h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)

    # Hue [0,1] → wavelength [380, 740] nm
    # But hue is circular: red appears at both 0 and 1
    # Map: 0 (red)→700nm, 0.16(yellow)→580nm, 0.33(green)→520nm,
    #       0.5(cyan)→490nm, 0.66(blue)→450nm, 0.83(violet)→400nm
    hue_to_nm_table = [
        (0.00, 700), (0.05, 660), (0.10, 630), (0.16, 580),
        (0.25, 550), (0.33, 520), (0.42, 500), (0.50, 490),
        (0.58, 475), (0.66, 460), (0.75, 445), (0.83, 420),
        (0.90, 400), (1.00, 380),
    ]

    # Interpolate
    for i in range(len(hue_to_nm_table) - 1):
        h0, nm0 = hue_to_nm_table[i]
        h1, nm1 = hue_to_nm_table[i+1]
        if h0 <= h <= h1:
            t = (h - h0) / (h1 - h0)
            return nm0 + (nm1 - nm0) * t

    return 580.0  # default to yellow


def color_to_audio_frequency(r: int, g: int, b: int) -> float:
    """
    Synesthetic translation: color → audio frequency (Hz).
    Maps dominant wavelength linearly onto the audible spectrum,
    then octave-shifts into a musically useful range (80–2000 Hz).
    """
    nm = rgb_to_dominant_wavelength(r, g, b)
    # Map nm [380, 740] → [0, 1]
    t = (nm - LIGHT_MIN_NM) / (LIGHT_MAX_NM - LIGHT_MIN_NM)
    # Invert: violet (short λ) → high frequency; red (long λ) → low frequency
    t_inv = 1 - t
    # Map to 80–2000 Hz range (musically rich zone)
    freq = 80 * (2 ** (t_inv * 4.64))  # ~4.64 octaves from 80 to ~2000 Hz
    return round(freq, 2)


def audio_to_color(hz: float) -> Tuple[int, int, int]:
    """
    Synesthetic translation: audio frequency → color.
    Inverts color_to_audio_frequency.
    High pitches → violet/blue; Low pitches → red/orange.
    """
    # Reverse the mapping: find t from hz
    # hz = 80 * 2^(t * 4.64) → t = log2(hz/80) / 4.64
    if hz <= 0:
        return (128, 128, 128)
    t_inv = math.log2(max(hz, 80) / 80) / 4.64
    t_inv = max(0, min(1, t_inv))
    t = 1 - t_inv
    nm = LIGHT_MIN_NM + t * (LIGHT_MAX_NM - LIGHT_MIN_NM)
    return wavelength_to_rgb(nm)


# ──────────────────────────────────────────────────────────────
# CHROMESTHESIA ENGINE — Sound → Shape mapping
# ──────────────────────────────────────────────────────────────

def frequency_to_shape_params(hz: float, amplitude: float = 1.0) -> dict:
    """
    Chromesthetic shape mapping based on documented synesthete reports:
    - High pitch → small, bright, sharp shapes
    - Low pitch → large, dark, round shapes
    - Loud → large shapes
    - Soft → small shapes
    """
    # Normalize frequency (log scale, 20Hz-20kHz)
    log_hz = math.log10(max(hz, 20))
    t = (log_hz - math.log10(20)) / (math.log10(20000) - math.log10(20))  # [0,1]

    brightness = 0.2 + t * 0.8          # high pitch → bright
    sharpness = t                         # high pitch → angular
    size = amplitude * (1 - t * 0.7)    # high pitch → smaller
    r, g, b = audio_to_color(hz)

    return {
        "frequency_hz": hz,
        "color_rgb": (r, g, b),
        "brightness": brightness,
        "sharpness": sharpness,   # 0=circle, 1=sharp angles
        "size": size,
        "shape": "triangle" if sharpness > 0.7 else "rectangle" if sharpness > 0.4 else "circle",
    }


# ──────────────────────────────────────────────────────────────
# MUSICAL NOTE / FREQUENCY TABLES
# ──────────────────────────────────────────────────────────────

# Equal temperament, A4 = 440 Hz
def midi_to_hz(midi_note: int) -> float:
    return 440.0 * (2 ** ((midi_note - 69) / 12))

def hz_to_midi(hz: float) -> float:
    return 69 + 12 * math.log2(hz / 440.0)

def hz_to_note_name(hz: float) -> str:
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    midi = hz_to_midi(hz)
    note_idx = int(round(midi)) % 12
    octave = (int(round(midi)) // 12) - 1
    return f"{notes[note_idx]}{octave}"


# Scriabin's synesthetic note→color mapping (chromesthesia, documented)
SCRIABIN_COLOR_MAP = {
    "C":  (255, 0, 0),       # Red
    "G":  (255, 140, 0),     # Orange
    "D":  (255, 215, 0),     # Yellow
    "A":  (100, 200, 50),    # Green
    "E":  (200, 230, 255),   # Blue-white/pearl
    "B":  (200, 200, 230),   # Steel/blue-white
    "F#": (100, 150, 255),   # Bright blue
    "C#": (100, 0, 180),     # Violet
    "Ab": (130, 0, 130),     # Purple
    "Eb": (200, 80, 160),    # Red-violet
    "Bb": (220, 140, 200),   # Rose/flesh
    "F":  (180, 0, 50),      # Deep crimson red
}

def note_to_scriabin_color(note_name: str) -> Tuple[int, int, int]:
    """Return Scriabin's synesthetic color for a note name (e.g. 'C', 'F#')."""
    base = note_name.replace("b", "").replace("#", "")
    if "#" in note_name:
        base = note_name[:2]
    elif "b" in note_name:
        base = note_name[:2]
    else:
        base = note_name[0]
    return SCRIABIN_COLOR_MAP.get(base, (128, 128, 128))


# ──────────────────────────────────────────────────────────────
# FULL SYNESTHETIC READING — emotion → all senses
# ──────────────────────────────────────────────────────────────

class SynestheticReading:
    """
    A complete synesthetic snapshot of an emotion — all senses rendered.
    This is what a synesthete would experience given an emotional stimulus.
    """

    def __init__(self, emotion: EmotionSignature, intensity: float = 1.0):
        self.emotion = emotion
        self.intensity = max(0.0, min(1.0, intensity))

    @property
    def primary_color(self) -> Tuple[int, int, int]:
        # Modulate saturation by intensity
        h, s, v = colorsys.rgb_to_hsv(
            self.emotion.rgb[0]/255,
            self.emotion.rgb[1]/255,
            self.emotion.rgb[2]/255,
        )
        s_mod = s * self.intensity
        v_mod = max(0.15, v * (0.5 + self.intensity * 0.5))
        r, g, b = colorsys.hsv_to_rgb(h, s_mod, v_mod)
        return (int(r*255), int(g*255), int(b*255))

    @property
    def solfeggio_frequency(self) -> float:
        return self.emotion.solfeggio_hz

    @property
    def eeg_frequency(self) -> float:
        return self.emotion.eeg_center_hz

    @property
    def harmonic_series(self) -> List[float]:
        """
        Return a harmonic series built from the emotion's solfeggio frequency.
        Harmonics are the overtones of the fundamental — the 'color' of a sound.
        More positive emotions have richer harmonic content (more overtones).
        """
        fundamental = self.emotion.solfeggio_hz
        n_harmonics = max(3, int(self.intensity * 8 + (self.emotion.valence + 1) * 4))
        return [fundamental * i for i in range(1, n_harmonics + 1)]

    @property
    def synesthetic_color_from_sound(self) -> Tuple[int, int, int]:
        """What color does the emotion's sound produce synesthetically?"""
        return audio_to_color(self.emotion.solfeggio_hz)

    @property
    def shape_percept(self) -> dict:
        return frequency_to_shape_params(self.emotion.solfeggio_hz, self.intensity)

    @property
    def musical_note(self) -> str:
        return hz_to_note_name(self.emotion.musical_mode_root_hz)

    @property
    def scriabin_color(self) -> Tuple[int, int, int]:
        note = self.musical_note
        return note_to_scriabin_color(note)

    def describe(self) -> str:
        r, g, b = self.primary_color
        sr, sg, sb = self.synesthetic_color_from_sound
        note = self.musical_note
        lines = [
            f"Emotion      : {self.emotion.name}  (intensity {self.intensity:.2f})",
            f"Color        : RGB({r},{g},{b})  #{self.emotion.hex_color}",
            f"Sound color  : RGB({sr},{sg},{sb})  [synesthetic]",
            f"Solfeggio    : {self.solfeggio_frequency:.1f} Hz",
            f"EEG band     : {self.emotion.eeg_band}  center {self.eeg_frequency:.1f} Hz",
            f"HRV coherence: {self.emotion.hrv_coherence_hz:.4f} Hz",
            f"Musical mode : {self.emotion.musical_mode}  root {note}",
            f"Harmonics    : {', '.join(f'{h:.1f}Hz' for h in self.harmonic_series[:5])}...",
            f"Scriabin clr : RGB{self.scriabin_color}",
            f"Shape        : {self.shape_percept['shape']}  brightness={self.shape_percept['brightness']:.2f}",
            f"Valence/Arousal: ({self.emotion.valence:+.2f}, {self.emotion.arousal:.2f})",
            f"Taste        : {self.emotion.taste}",
            f"Texture      : {self.emotion.texture}",
            f"Description  : {self.emotion.description}",
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# IMAGE COLOR → EMOTION SYNESTHESIA
# ──────────────────────────────────────────────────────────────

def image_colors_to_emotions(
    color_palette: List[Tuple[int, int, int, float]],  # (r, g, b, weight)
    top_n: int = 5,
) -> List[Tuple[EmotionSignature, float]]:
    """
    Given a list of (r, g, b, weight) color samples from an image,
    map each to its nearest emotion and accumulate weighted scores.

    Returns a ranked list of (emotion, total_weight) pairs.
    """
    scores: Dict[str, float] = {}
    for r, g, b, weight in color_palette:
        em = nearest_emotion_by_rgb(r, g, b)
        scores[em.name] = scores.get(em.name, 0.0) + weight

    # Normalize
    total = sum(scores.values()) or 1.0
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    result = []
    for name, score in ranked[:top_n]:
        em = EMOTION_MAP.get(name.lower())
        if em:
            result.append((em, score / total))
    return result
