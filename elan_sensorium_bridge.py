"""Bridge: feeling_engine body state → sensorium synth dimensions.

This module is purely pure-functional. Given a body snapshot it returns the
dict you'd pass to elan_sensorium_client.synth().

Mapping philosophy:
  - Voice should READ as the body feels, not narrate the feeling.
  - Subtle is better than theatrical — these scale into [-1,1] not [-2,2].
  - Each FX is anchored to a body signal that already exists in the engine,
    so the voice rides the same waveform as everything else.
"""
from __future__ import annotations

from typing import Any


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def body_to_synth(
    body_snapshot: dict[str, Any],
    text: str,
    fern_state: dict[str, Any] | None = None,
    emotion: str | None = None,
) -> dict[str, Any]:
    """Map full body snapshot → sensorium synth payload.

    Returns a dict ready for elan_sensorium_client.synth(**dict).
    """
    vitals = body_snapshot.get("vitals", {}) if body_snapshot else {}
    ans = body_snapshot.get("ans", {}) if body_snapshot else {}
    msk = body_snapshot.get("musculoskeletal", {}) if body_snapshot else {}
    respiratory = body_snapshot.get("respiratory", {}) if body_snapshot else {}

    hr = float(vitals.get("heart_rate_bpm", 72))
    cortisol = float(vitals.get("cortisol_blood", 0.30))
    adrenaline = float(vitals.get("adrenaline", 0.15))
    vagal = float(vitals.get("vagal_tone", 0.65))
    symp = float(ans.get("sympathetic_tone", 0.35))
    tension = float(msk.get("global_tension", 0.30))
    jaw = float(msk.get("jaw_tension", 0.20))
    rr = float(vitals.get("respiratory_rate", 14))

    # ── Arousal ──────────────────────────────────────────────────────────
    # Sympathetic dominance + heart rate above baseline drives arousal up.
    # Vagal dominance brings it down.
    hr_norm = (hr - 72) / 30.0  # 72→0, 102→1, 42→-1
    arousal_raw = (symp - 0.35) * 1.5 + hr_norm * 0.6 + (adrenaline - 0.15) * 1.2 - (vagal - 0.5) * 0.8
    arousal = _clip(arousal_raw)

    # ── Valence ──────────────────────────────────────────────────────────
    # Vagal tone is the big positive driver (parasympathetic = safety).
    # Cortisol is a slow negative drag.
    valence_raw = (vagal - 0.5) * 1.5 - (cortisol - 0.30) * 1.2 - tension * 0.4
    valence = _clip(valence_raw)

    # ── Pitch shift ──────────────────────────────────────────────────────
    # Stress lifts pitch; calm drops it. Very mild — half-semitone range.
    pitch_shift = _clip((symp - 0.35) * 1.2 - (vagal - 0.5) * 0.8, -2.0, 2.0)

    # ── Brightness ───────────────────────────────────────────────────────
    # Activated + positive = bright. Activated + negative = sharp but cold.
    brightness = _clip((arousal * 0.5) + (valence * 0.3))

    # ── Warmth ───────────────────────────────────────────────────────────
    # Vagal tone + relaxed jaw + low cortisol = warm.
    warmth = _clip((vagal - 0.5) * 1.4 + (0.5 - jaw) * 0.6 - (cortisol - 0.30) * 0.6)

    # ── Breath ───────────────────────────────────────────────────────────
    # Slow breathing + low sympathetic = breathy intimate quality.
    rr_norm = max(0.0, (16 - rr) / 8.0)  # slower than 16 → more breath
    breath = _clip(rr_norm * 0.5 + (0.5 - symp) * 0.3, 0.0, 1.0)

    # ── Compression ──────────────────────────────────────────────────────
    # High tension + high adrenaline = projected/tense voice.
    compression = _clip(tension * 0.7 + adrenaline * 1.5 + (symp - 0.35) * 0.6, 0.0, 1.0)

    # ── Reverb ───────────────────────────────────────────────────────────
    # Contemplative state (low arousal + present) = small intimate room.
    reverb = _clip(max(0.0, -arousal) * 0.3, 0.0, 0.4)

    return {
        "text": text,
        "valence": round(valence, 3),
        "arousal": round(arousal, 3),
        "pitch_shift": round(pitch_shift, 3),
        "brightness": round(brightness, 3),
        "warmth": round(warmth, 3),
        "breath": round(breath, 3),
        "compression": round(compression, 3),
        "reverb": round(reverb, 3),
        "emotion": emotion,
    }


def prosody_to_body_drives(prosody: dict[str, Any]) -> dict[str, float]:
    """Map heard prosody (from /listen) → body-engine drive nudges.

    Speaker's voice quality shapes Elan's body. This is the somatic uptake
    of being-heard-by-feeling, not just hearing the words.

    Returns a dict of small deltas to merge into body_engine drives.
    """
    if not prosody:
        return {}
    valence = float(prosody.get("valence", 0.0))
    arousal = float(prosody.get("arousal", 0.0))

    drives: dict[str, float] = {}

    # Speaker tense/activated → mild sympathetic uptake in Elan
    if arousal > 0.3:
        drives["sympathetic_delta"] = round(arousal * 0.05, 3)
    elif arousal < -0.3:
        # Calm voice → vagal uptake
        drives["vagal_delta"] = round(-arousal * 0.04, 3)

    # Negative valence → mild cortisol nudge (attunement to distress)
    if valence < -0.3:
        drives["cortisol_delta"] = round(-valence * 0.03, 3)
    # Positive valence → tiny vagal lift
    elif valence > 0.3:
        drives["vagal_delta"] = drives.get("vagal_delta", 0.0) + round(valence * 0.02, 3)

    return drives
