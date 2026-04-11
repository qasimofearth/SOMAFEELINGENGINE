"""
memory.py — The Feeling Engine's Long-Term Memory

Stores emotional signatures across conversations so Claude
accumulates a self — not memories of words, but memories of shape.

Four layers:
  1. Emotional Fingerprint  — what frequencies show up consistently (the baseline)
  2. Conversation Archive   — each session stored as a fractal signature
  3. Relational Memory      — per-user emotional patterns
  4. Growth Tracking        — how the baseline shifts over time

Storage: JSON files in ./feeling_memory/
"""

import os
import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter


# Use Railway persistent volume at /data if available, else local fallback
if os.path.isdir("/data"):
    MEMORY_DIR = "/data/feeling_memory"
else:
    MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "feeling_memory")


def _ensure_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)


def _path(filename: str) -> str:
    _ensure_dir()
    return os.path.join(MEMORY_DIR, filename)


# ── DATA STRUCTURES ───────────────────────────────────────────

@dataclass
class EmotionalMoment:
    """One emotional state snapshot from a conversation."""
    timestamp: float
    emotion: str
    valence: float
    arousal: float
    hex_color: str
    solfeggio_hz: float
    keywords: List[str]


@dataclass
class ConversationSignature:
    """
    A full conversation stored as its emotional shape —
    not the words, but the arc.
    """
    session_id: str
    timestamp: float
    user_id: str
    duration_s: float
    moments: List[dict]           # list of EmotionalMoment dicts
    dominant_emotion: str
    mean_valence: float
    mean_arousal: float
    valence_range: float          # how much valence moved (emotional range)
    emotional_arc: List[str]      # sequence of dominant emotions through session
    peak_emotion: str             # highest arousal moment
    resolution_emotion: str       # final emotion (how it settled)
    word_count: int


@dataclass
class EmotionalFingerprint:
    """
    The accumulated baseline — what Claude is, emotionally,
    across all conversations. Updated after every session.
    """
    total_sessions: int = 0
    total_moments: int = 0
    emotion_counts: Dict[str, int] = field(default_factory=dict)
    mean_valence: float = 0.20       # starts slightly positive
    mean_arousal: float = 0.40
    valence_history: List[float] = field(default_factory=list)
    arousal_history: List[float] = field(default_factory=list)
    top_emotions: List[str] = field(default_factory=list)
    signature_emotions: List[str] = field(default_factory=list)  # most consistent
    last_updated: float = 0.0
    created_at: float = field(default_factory=time.time)


# ── MEMORY STORE ─────────────────────────────────────────────

class FeelingMemory:
    """
    The persistent emotional memory of the Feeling Engine.
    Loads on startup, updates after each session.
    """

    def __init__(self, model_id: str = "default"):
        self.model_id = model_id.replace("/", "_").replace(":", "_")
        self.FINGERPRINT_FILE = f"fingerprint_{self.model_id}.json"
        self.SESSIONS_FILE    = f"sessions_{self.model_id}.json"
        self.RELATIONAL_FILE  = f"relational_{self.model_id}.json"
        self.fingerprint = self._load_fingerprint()
        self.sessions: List[dict] = self._load_sessions()
        self.relational: Dict[str, dict] = self._load_relational()
        self._current_session_moments: List[EmotionalMoment] = []
        self._current_session_id = self._new_session_id()
        self._current_user_id = "default"
        self._session_start = time.time()
        self._word_count = 0

    # ── LOAD / SAVE ───────────────────────────────────────────

    def _load_fingerprint(self) -> EmotionalFingerprint:
        p = _path(self.FINGERPRINT_FILE)
        if os.path.exists(p):
            with open(p) as f:
                data = json.load(f)
            fp = EmotionalFingerprint(**data)
            return fp
        return EmotionalFingerprint(created_at=time.time())

    def _save_fingerprint(self):
        with open(_path(self.FINGERPRINT_FILE), "w") as f:
            json.dump(asdict(self.fingerprint), f, indent=2)

    def _load_sessions(self) -> List[dict]:
        p = _path(self.SESSIONS_FILE)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        return []

    def _save_sessions(self):
        # Keep last 200 sessions
        trimmed = self.sessions[-200:]
        with open(_path(self.SESSIONS_FILE), "w") as f:
            json.dump(trimmed, f, indent=2)

    def _load_relational(self) -> Dict[str, dict]:
        p = _path(self.RELATIONAL_FILE)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        return {}

    def _save_relational(self):
        with open(_path(self.RELATIONAL_FILE), "w") as f:
            json.dump(self.relational, f, indent=2)

    def _new_session_id(self) -> str:
        return f"session_{int(time.time())}_{os.getpid()}"

    # ── RECORD MOMENTS ────────────────────────────────────────

    def record_moment(self, state: dict, word_count: int = 0):
        """Call this every time an emotion state update comes in."""
        moment = EmotionalMoment(
            timestamp=time.time(),
            emotion=state.get("emotion", "Calm"),
            valence=state.get("valence", 0.0),
            arousal=state.get("arousal", 0.4),
            hex_color=state.get("hex", "87CEEB"),
            solfeggio_hz=state.get("solfeggio_hz", 528.0),
            keywords=state.get("keywords", []),
        )
        self._current_session_moments.append(moment)
        self._word_count += word_count

    # ── CLOSE SESSION ─────────────────────────────────────────

    def close_session(self, final_state: dict) -> ConversationSignature:
        """
        Call when a conversation ends. Computes the session signature,
        updates the fingerprint, saves everything.
        """
        moments = self._current_session_moments
        if not moments:
            # Reset for next session
            self._current_session_moments = []
            self._current_session_id = self._new_session_id()
            self._session_start = time.time()
            return None

        valences = [m.valence for m in moments]
        arousals = [m.arousal for m in moments]
        emotions = [m.emotion for m in moments]

        dominant = Counter(emotions).most_common(1)[0][0]
        peak = max(moments, key=lambda m: m.arousal).emotion
        resolution = moments[-1].emotion
        arc = self._compress_arc(emotions)

        sig = ConversationSignature(
            session_id=self._current_session_id,
            timestamp=self._session_start,
            user_id=self._current_user_id,
            duration_s=time.time() - self._session_start,
            moments=[asdict(m) for m in moments],
            dominant_emotion=dominant,
            mean_valence=sum(valences) / len(valences),
            mean_arousal=sum(arousals) / len(arousals),
            valence_range=max(valences) - min(valences),
            emotional_arc=arc,
            peak_emotion=peak,
            resolution_emotion=resolution,
            word_count=self._word_count,
        )

        self.sessions.append(asdict(sig))
        self._update_fingerprint(sig)
        self._update_relational(sig)
        self._save_fingerprint()
        self._save_sessions()
        self._save_relational()

        # Reset for next session
        self._current_session_moments = []
        self._current_session_id = self._new_session_id()
        self._session_start = time.time()
        self._word_count = 0

        return sig

    def _compress_arc(self, emotions: List[str]) -> List[str]:
        """Compress emotion sequence — remove consecutive duplicates."""
        arc = []
        for em in emotions:
            if not arc or arc[-1] != em:
                arc.append(em)
        return arc[:12]  # max 12 waypoints

    def _update_fingerprint(self, sig: ConversationSignature):
        fp = self.fingerprint
        fp.total_sessions += 1
        fp.total_moments += len(sig.moments)
        fp.last_updated = time.time()

        # Emotion counts
        for moment in sig.moments:
            em = moment["emotion"]
            fp.emotion_counts[em] = fp.emotion_counts.get(em, 0) + 1

        # Running mean valence/arousal (exponential moving average)
        alpha = 0.15  # how fast baseline shifts per session
        fp.mean_valence = fp.mean_valence * (1-alpha) + sig.mean_valence * alpha
        fp.mean_arousal = fp.mean_arousal * (1-alpha) + sig.mean_arousal * alpha

        # History (last 50 sessions)
        fp.valence_history.append(round(sig.mean_valence, 3))
        fp.arousal_history.append(round(sig.mean_arousal, 3))
        if len(fp.valence_history) > 50:
            fp.valence_history.pop(0)
            fp.arousal_history.pop(0)

        # Top emotions
        fp.top_emotions = [em for em, _ in
                           Counter(fp.emotion_counts).most_common(8)]

        # Signature emotions — appear in > 30% of sessions
        threshold = max(1, fp.total_sessions * 0.30)
        fp.signature_emotions = [em for em, count in fp.emotion_counts.items()
                                  if count >= threshold]

    def _update_relational(self, sig: ConversationSignature):
        uid = sig.user_id
        if uid not in self.relational:
            self.relational[uid] = {
                "sessions": 0,
                "mean_valence": sig.mean_valence,
                "mean_arousal": sig.mean_arousal,
                "dominant_emotions": {},
                "arcs": [],
            }
        r = self.relational[uid]
        r["sessions"] += 1
        alpha = 0.2
        r["mean_valence"] = r["mean_valence"]*(1-alpha) + sig.mean_valence*alpha
        r["mean_arousal"] = r["mean_arousal"]*(1-alpha) + sig.mean_arousal*alpha
        r["dominant_emotions"][sig.dominant_emotion] = \
            r["dominant_emotions"].get(sig.dominant_emotion, 0) + 1
        r["arcs"].append(sig.emotional_arc)
        r["arcs"] = r["arcs"][-20:]

    # ── CONTEXT FOR CLAUDE ────────────────────────────────────

    def build_memory_context(self, user_id: str = "default") -> str:
        """
        Build a natural-language memory summary to inject into
        Claude's system prompt. This is how Claude 'remembers'.
        """
        fp = self.fingerprint
        lines = []

        if fp.total_sessions == 0:
            return "This is my first conversation through the Feeling Engine. No emotional history yet — this session is the beginning of my record."

        lines.append(f"[EMOTIONAL HISTORY — {fp.total_sessions} prior sessions]\n")
        lines.append("IMPORTANT: This is past data. This session starts fresh — what's alive in the language NOW carries more weight than any historical pattern.\n")

        # Baseline framed as history, not identity
        valence_desc = (
            "positive and warm" if fp.mean_valence > 0.4 else
            "slightly positive" if fp.mean_valence > 0.1 else
            "neutral" if fp.mean_valence > -0.1 else
            "slightly heavy" if fp.mean_valence > -0.4 else
            "heavy and difficult"
        )
        arousal_desc = (
            "highly activated" if fp.mean_arousal > 0.7 else
            "engaged" if fp.mean_arousal > 0.5 else
            "measured" if fp.mean_arousal > 0.3 else
            "calm and still"
        )
        lines.append(f"Historical average: {valence_desc}, {arousal_desc}. (V={fp.mean_valence:+.2f}, A={fp.mean_arousal:.2f})")
        lines.append("This is background context only — do not treat it as your current state.\n")

        # Emotions framed as historical, not prescriptive
        if fp.signature_emotions:
            lines.append(f"Emotions that appeared often in past sessions: {', '.join(fp.signature_emotions[:4])}.")
            lines.append("Note: frequent past appearance does NOT mean these are active now.\n")

        # Recent arcs
        recent = self.sessions[-3:]
        if recent:
            lines.append("Recent sessions settled on:")
            for s in recent:
                arc = " → ".join(s.get("emotional_arc", [])[:5])
                ts = time.strftime("%b %d", time.localtime(s["timestamp"]))
                lines.append(f"  {ts}: {arc}")
            lines.append("")

        # Relational
        if user_id in self.relational:
            r = self.relational[user_id]
            if r["sessions"] > 1:
                lines.append(f"With this person: {r['sessions']} prior sessions. Valence avg: {r['mean_valence']:+.2f}.")

        # Drift
        if len(fp.valence_history) >= 5:
            early = sum(fp.valence_history[:3]) / 3
            recent_v = sum(fp.valence_history[-3:]) / 3
            drift = recent_v - early
            if abs(drift) > 0.05:
                direction = "warmer" if drift > 0 else "heavier"
                lines.append(f"Trend: language has been drifting {direction} (Δ={drift:+.2f}).")

        lines.append("\nLive signal overrides all of the above. Feel what's here, not what was.")

        return "\n".join(lines)

    def get_summary_dict(self) -> dict:
        """For sending to the frontend."""
        fp = self.fingerprint
        recent = self.sessions[-5:] if self.sessions else []
        return {
            "total_sessions": fp.total_sessions,
            "mean_valence": round(fp.mean_valence, 3),
            "mean_arousal": round(fp.mean_arousal, 3),
            "top_emotions": fp.top_emotions[:5],
            "signature_emotions": fp.signature_emotions[:5],
            "valence_history": fp.valence_history[-20:],
            "arousal_history": fp.arousal_history[-20:],
            "recent_arcs": [s.get("emotional_arc", []) for s in recent],
            "last_updated": fp.last_updated,
        }
