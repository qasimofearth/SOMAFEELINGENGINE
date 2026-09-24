"""
Elan's felt state (server.EmotionalStateTracker): consistency, continuity, evidence.

Run:  python -m pytest feeling_engine/tests/test_tracker_consistency.py -q
Needs the server's dependencies (Python 3.10+).
"""
import random

import pytest

import feeling_engine.text_emotion as te
from feeling_engine.emotion_map import EMOTION_MAP

S = pytest.importorskip("feeling_engine.server")

TEXTS = [
    "I am absolutely furious with you.", "I miss her so much it hurts.",
    "Haha that is hilarious.", "The meeting is at 3pm.", "I'm terrified.",
    "Thank you so much.", "Phew, what a relief.", "I'm really disappointed.",
    "BTC is at 64,200.", "I love this.", "That's disgusting.", "Wow!",
]
NT_STATES = [None, {"dopamine": 0.8, "cortisol": 0.2},
             {"dopamine": 0.3, "cortisol": 0.7, "serotonin": 0.3}]


def _check_state(state):
    # The named feeling is the top of the blend the face renders.
    assert state["mix"][0]["name"] == state["emotion"]
    assert abs(sum(m["weight"] for m in state["mix"]) - 1.0) < 0.01
    assert state["emotion"].lower() in EMOTION_MAP
    # Valence/arousal are those of the blend, so they agree with it.
    assert -1.0 <= state["valence"] <= 1.0 and 0.0 <= state["arousal"] <= 1.0


def test_state_is_consistent_through_any_sequence():
    rng = random.Random(3)
    tr = S.EmotionalStateTracker()
    for _ in range(60):
        r = te.analyze_text(rng.choice(TEXTS))
        _check_state(tr.update(r, nt_levels=rng.choice(NT_STATES)))


def test_text_without_feeling_leaves_state_unchanged():
    tr = S.EmotionalStateTracker()
    tr.update(te.analyze_text("I am absolutely furious with you."))
    before = dict(tr.mix)
    r = te.analyze_text("The meeting is at 3pm in room 4.")
    r.confidence = 0.0          # force zero evidence regardless of reader
    tr.update(r)
    assert set(tr.mix) == set(before)
    assert all(abs(tr.mix[k] - before[k]) < 1e-3 for k in before)   # only time passes


def test_charged_text_moves_state_quickly():
    tr = S.EmotionalStateTracker()
    for _ in range(3):
        state = tr.update(te.analyze_text("I am absolutely furious with you, this is outrageous."))
    assert EMOTION_MAP[state["emotion"].lower()].valence < 0, state["emotion"]


def test_state_persists_across_replies():
    assert S.get_elan_tracker() is S.get_elan_tracker()
    tr = S.get_elan_tracker()
    tr.update(te.analyze_text("I'm terrified of what happens next."))
    assert S.get_elan_tracker().current_emotion == tr.current_emotion


def test_snapshot_does_not_apply_the_reading():
    tr = S.EmotionalStateTracker()
    tr.update(te.analyze_text("Thank you so much."))
    before = dict(tr.mix)
    tr.snapshot(te.analyze_text("I hate this, it's awful."))
    assert set(tr.mix) == set(before)
    assert all(abs(tr.mix[k] - before[k]) < 1e-3 for k in before)   # only time passes


def test_state_relaxes_toward_rest_over_time(monkeypatch):
    tr = S.EmotionalStateTracker()
    for _ in range(3):
        tr.update(te.analyze_text("I am absolutely furious with you, this is outrageous."))
    assert EMOTION_MAP[tr.current_emotion.lower()].valence < 0
    t0 = tr._last_t
    monkeypatch.setattr(S.time, "time", lambda: t0 + 4 * S.EmotionalStateTracker.HALF_LIFE_S)
    state = tr.snapshot()
    assert state["emotion"].lower() in S.EmotionalStateTracker.REST, state["emotion"]
    _check_state(state)


def test_compare_model_starts_from_elans_state():
    tr = S.EmotionalStateTracker()
    tr.update(te.analyze_text("I'm terrified of what happens next."))
    other = tr.clone()
    assert other.mix == tr.mix and other is not tr
    other.update(te.analyze_text("Thank you so much."))
    assert other.mix != tr.mix


def test_reply_history_is_per_reply():
    tr = S.EmotionalStateTracker()
    tr.update(te.analyze_text("I'm terrified."))
    tr.begin_reply()
    assert tr.reply_history == []
    tr.update(te.analyze_text("Thank you so much."))
    assert len(tr.reply_history) == 1 and len(tr.history) == 2
