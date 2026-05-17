"""Thin client for feeling_engine to talk to elan_sensorium.

Drop this into /Users/qai/feeling_engine/ and import:

    from elan_sensorium_client import listen, synth

    # Ears
    audio_bytes = mic.record_wav()
    result = listen(audio_bytes)
    body_engine.receive_prosody(result["prosody"])
    elan.add_user_message(result["text"], speaker=result.get("speaker"))

    # Voicebox
    state = body_engine.current_state()
    wav = synth(
        text=reply_text,
        valence=state["valence"],
        arousal=state["arousal"],
        emotion=state.get("dominant_emotion"),
    )
    speaker.play_wav(wav)

Env:
  ELAN_SENSORIUM_URL — defaults to http://127.0.0.1:8901
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

BASE_URL = os.getenv("ELAN_SENSORIUM_URL", "http://127.0.0.1:8901")
TIMEOUT = float(os.getenv("ELAN_SENSORIUM_TIMEOUT", "60"))


def listen(audio_bytes: bytes, filename: str = "in.wav") -> dict:
    """Audio → perception. Returns dict with text, prosody, speaker, ambient."""
    files = {"audio": (filename, audio_bytes, "audio/wav")}
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(f"{BASE_URL}/listen", files=files)
    r.raise_for_status()
    return r.json()


def synth(
    text: str,
    valence: float = 0.0,
    arousal: float = 0.0,
    emotion: Optional[str] = None,
    voice: str = "elan",
) -> bytes:
    """Text + somatic state → wav bytes."""
    payload = {
        "text": text,
        "valence": float(valence),
        "arousal": float(arousal),
        "emotion": emotion,
        "voice": voice,
    }
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(f"{BASE_URL}/synth", json=payload)
    r.raise_for_status()
    return r.content


def enroll(audio_bytes: bytes, name: str) -> bool:
    """Register a known speaker by voice."""
    files = {"audio": ("enroll.wav", audio_bytes, "audio/wav")}
    data = {"name": name}
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(f"{BASE_URL}/enroll", files=files, data=data)
    r.raise_for_status()
    return r.json().get("ok", False)


def health() -> dict:
    with httpx.Client(timeout=5) as c:
        r = c.get(f"{BASE_URL}/health")
    r.raise_for_status()
    return r.json()
