"""
concert.py — The Frequency Concert Generator

Takes a spectrum of (frequency, amplitude) pairs from the feeling engine
and synthesizes them into a real audio WAV file.

An emotion becomes a concert:
- Each emotion contributes its solfeggio frequency as a fundamental tone
- Sub-emotions (fractal recursion) add harmonics at lower amplitudes
- The full emotion tree = an orchestra where each instrument IS an emotion

Also generates: MIDI-like event data, spectrum visualization data.
"""

import math
import struct
import wave
import io
import os
from typing import List, Tuple, Optional
import numpy as np


SAMPLE_RATE = 44100   # Hz
AMPLITUDE_MAX = 32767  # 16-bit PCM


# ──────────────────────────────────────────────────────────────
# WAVEFORM SYNTHESIS
# ──────────────────────────────────────────────────────────────

def sine_wave(freq: float, duration_s: float, amplitude: float = 1.0,
              sample_rate: int = SAMPLE_RATE, phase: float = 0.0) -> np.ndarray:
    """Generate a pure sine wave."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t + phase)


def envelope(samples: np.ndarray, attack_s: float = 0.05,
             release_s: float = 0.1, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply attack/release envelope to prevent clicks."""
    n = len(samples)
    attack_n = int(attack_s * sample_rate)
    release_n = int(release_s * sample_rate)

    env = np.ones(n)
    env[:attack_n] = np.linspace(0, 1, attack_n)
    if release_n > 0 and release_n <= n:
        env[-release_n:] = np.linspace(1, 0, release_n)
    return samples * env


def harmonic_tone(fundamental: float, n_harmonics: int = 6,
                  duration_s: float = 2.0, amplitude: float = 1.0,
                  sample_rate: int = SAMPLE_RATE,
                  harmonic_decay: float = 0.6) -> np.ndarray:
    """
    Generate a rich tone with overtones — more natural than a pure sine.
    harmonic_decay: how quickly upper harmonics fade (0=equal, 1=linear decay)
    """
    result = np.zeros(int(sample_rate * duration_s))
    for i in range(1, n_harmonics + 1):
        harm_amp = amplitude * (harmonic_decay ** (i - 1))
        harm_freq = fundamental * i
        if harm_freq > 20000:  # past human hearing
            break
        wave_data = sine_wave(harm_freq, duration_s, harm_amp, sample_rate)
        result += wave_data
    # Normalize
    max_val = np.max(np.abs(result))
    if max_val > 0:
        result = result / max_val * amplitude
    return result


def binaural_beat(base_freq: float, beat_freq: float,
                  duration_s: float = 5.0, amplitude: float = 0.7,
                  sample_rate: int = SAMPLE_RATE) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a binaural beat: left ear hears base_freq, right ear hears base_freq + beat_freq.
    The brain perceives the difference as an internal beat.
    """
    left = sine_wave(base_freq, duration_s, amplitude, sample_rate)
    right = sine_wave(base_freq + beat_freq, duration_s, amplitude, sample_rate)
    return left, right


# ──────────────────────────────────────────────────────────────
# EMOTION CONCERT SYNTHESIS
# ──────────────────────────────────────────────────────────────

class EmotionConcert:
    """
    Synthesizes a complete emotional soundscape from a frequency spectrum.

    The spectrum is a list of (hz, amplitude) pairs — output of the
    fractal emotion tree. The concert renders all these as simultaneous
    harmonic tones, creating a chord that IS the emotion.
    """

    def __init__(
        self,
        spectrum: List[Tuple[float, float]],
        duration_s: float = 8.0,
        sample_rate: int = SAMPLE_RATE,
        include_binaural: bool = True,
    ):
        self.spectrum = spectrum
        self.duration_s = duration_s
        self.sample_rate = sample_rate
        self.include_binaural = include_binaural
        self._audio: Optional[np.ndarray] = None

    def _filter_spectrum(self) -> List[Tuple[float, float]]:
        """
        Clean up spectrum: remove inaudible frequencies,
        merge near-duplicate frequencies, normalize amplitudes.
        """
        # Remove out-of-range
        valid = [(hz, amp) for hz, amp in self.spectrum if 20 < hz < 18000 and amp > 0]

        # Merge frequencies within 2 Hz of each other (they would alias)
        merged = {}
        for hz, amp in valid:
            bucket = round(hz / 2) * 2  # 2 Hz buckets
            merged[bucket] = merged.get(bucket, 0) + amp

        # Sort by amplitude descending, take top 20 to avoid mud
        sorted_spec = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:20]

        # Normalize amplitudes to [0,1]
        max_amp = max(amp for _, amp in sorted_spec) if sorted_spec else 1
        return [(hz, amp / max_amp) for hz, amp in sorted_spec]

    def synthesize(self) -> np.ndarray:
        """
        Render the full concert to a mono audio array.
        Returns float64 array in range [-1, 1].
        """
        if self._audio is not None:
            return self._audio

        clean_spectrum = self._filter_spectrum()
        n_samples = int(self.sample_rate * self.duration_s)
        mix = np.zeros(n_samples)

        for hz, amp in clean_spectrum:
            n_harmonics = max(2, int(3 + amp * 5))
            tone = harmonic_tone(
                hz, n_harmonics=n_harmonics,
                duration_s=self.duration_s,
                amplitude=amp * 0.4,
                sample_rate=self.sample_rate,
                harmonic_decay=0.65,
            )
            tone = envelope(tone, attack_s=0.1, release_s=0.3,
                            sample_rate=self.sample_rate)
            mix += tone[:n_samples]

        # Soft clip (tanh) to prevent harsh clipping
        if np.max(np.abs(mix)) > 0:
            mix = np.tanh(mix * 0.8) * 0.9

        self._audio = mix
        return mix

    def to_stereo(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create stereo mix with subtle binaural beating at the emotion's EEG frequency.
        """
        mono = self.synthesize()

        if not self.include_binaural or not self.spectrum:
            return mono, mono

        # Add binaural beat at the dominant EEG frequency
        dominant_hz = self.spectrum[0][0] if self.spectrum else 200
        eeg_beat = 10.0  # default: alpha beat

        left_beat, right_beat = binaural_beat(
            base_freq=100.0,
            beat_freq=eeg_beat,
            duration_s=self.duration_s,
            amplitude=0.08,
            sample_rate=self.sample_rate,
        )
        n = len(mono)
        left = mono + left_beat[:n] * 0.1
        right = mono + right_beat[:n] * 0.1

        return left, right

    def save_wav(self, filepath: str):
        """Write a 16-bit stereo WAV file."""
        left, right = self.to_stereo()

        # Interleave L/R and convert to int16
        n = min(len(left), len(right))
        interleaved = np.empty(n * 2, dtype=np.float64)
        interleaved[0::2] = left[:n]
        interleaved[1::2] = right[:n]

        pcm = (interleaved * AMPLITUDE_MAX).astype(np.int16)

        with wave.open(filepath, 'w') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)   # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())

        return filepath

    def spectrum_report(self) -> str:
        """Human-readable description of the frequency concert."""
        clean = self._filter_spectrum()
        lines = ["── Frequency Concert ──────────────────────────"]
        for i, (hz, amp) in enumerate(clean, 1):
            bar = "█" * int(amp * 20)
            lines.append(f"  {i:2d}. {hz:8.2f} Hz  amp={amp:.3f}  {bar}")
        lines.append(f"\n  Total tones: {len(clean)}")
        lines.append(f"  Duration:    {self.duration_s:.1f}s")
        lines.append(f"  Sample rate: {self.sample_rate} Hz")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# EMOTION SEQUENCE — animate through emotional states
# ──────────────────────────────────────────────────────────────

def crossfade(a: np.ndarray, b: np.ndarray, overlap_s: float = 1.0,
              sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Crossfade between two audio arrays."""
    overlap_n = int(overlap_s * sample_rate)
    overlap_n = min(overlap_n, len(a), len(b))

    fade_out = np.linspace(1, 0, overlap_n)
    fade_in  = np.linspace(0, 1, overlap_n)

    result = np.concatenate([
        a[:-overlap_n],
        a[-overlap_n:] * fade_out + b[:overlap_n] * fade_in,
        b[overlap_n:],
    ])
    return result


def render_emotion_journey(
    concerts: List[EmotionConcert],
    overlap_s: float = 1.5,
) -> np.ndarray:
    """
    Stitch multiple emotion concerts into a continuous emotional journey
    with crossfades between states.
    """
    if not concerts:
        return np.array([])

    result = concerts[0].synthesize()
    for concert in concerts[1:]:
        next_audio = concert.synthesize()
        result = crossfade(result, next_audio, overlap_s)

    return result
