"""
Accuracy and consistency tests for the text → feeling path.

Run:  python -m pytest feeling_engine/tests/test_feeling_accuracy.py -q
      (from the directory that contains feeling_engine/)

Classifier tests are skipped when the model cannot be loaded; set
FEELING_EMOTION_MODEL_DIR to a directory holding the pinned model to run them.
"""
import json
import os
import re

import pytest

import feeling_engine.text_emotion as te
from feeling_engine import emotion_classifier as ec
from feeling_engine.emotion_map import EMOTION_MAP
from feeling_engine.brain.emotion_circuits import EMOTION_CIRCUITS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ── Coverage: every feeling can be fired in the brain and shown on the face ──

def test_every_atlas_emotion_has_a_brain_circuit():
    missing = sorted(set(EMOTION_MAP) - set(EMOTION_CIRCUITS))
    assert not missing, f"no circuit (brain would silently run Calm): {missing}"


def test_every_atlas_emotion_has_a_face_expression():
    src = open(os.path.join(ROOT, "face.html"), encoding="utf-8").read()
    face = {row[0].lower() for row in json.loads(re.search(r"const EMO=(\[\[.*?\]\]);", src).group(1))}
    missing = sorted(set(EMOTION_MAP) - face)
    assert not missing, f"no face expression: {missing}"


def test_classifier_labels_and_keywords_map_to_real_emotions():
    for label, targets in ec.LABEL_TO_ATLAS.items():
        assert abs(sum(targets.values()) - 1.0) < 1e-9, label
        for name in targets:
            assert name.lower() in EMOTION_MAP, (label, name)
    assert set(ec.LABEL_TO_ATLAS) | {"neutral"} == set(ec.LABELS)
    for word, name in te.EMOTION_KEYWORDS.items():
        assert name.lower() in EMOTION_MAP, (word, name)


# ── Lexicon path (classifier off) ──

@pytest.fixture
def lexicon_only(monkeypatch):
    monkeypatch.setattr(te, "_classifier", None)


def test_negated_emotion_word_is_not_that_emotion(lexicon_only):
    r = te.analyze_text("I am not happy about this.")
    assert r.dominant_emotion.name != "Joy"
    assert r.valence < 0
    assert "happy" in r.negated_keywords and not r.keyword_votes


def test_negation_stops_at_punctuation(lexicon_only):
    r = te.analyze_text("The market means nothing, stop loss at this level.")
    assert r.lexicon["valence"] < 0 and r.valence < 0


def test_negation_within_clause_still_flips(lexicon_only):
    assert te.analyze_text("I am not afraid.").lexicon["valence"] > 0


def test_non_emotional_senses_do_not_trigger_emotions(lexicon_only):
    for text in ["Interest rates rose again.", "Cash flow was positive.",
                 "I moved house last week.", "I wonder if it will rain."]:
        r = te.analyze_text(text)
        assert not r.keyword_votes, (text, r.keyword_votes)


def test_text_without_feeling_carries_no_evidence(lexicon_only):
    r = te.analyze_text("The meeting is at 3pm in room 4.")
    assert r.confidence == 0.0 and r.is_neutral


def test_reading_is_internally_consistent(lexicon_only):
    for text in ["I am furious with you", "I miss you so much", "What a wonderful day",
                 "I'm terrified of what happens next", "Thank you, truly"]:
        r = te.analyze_text(text)
        assert r.emotion_mix[0][0] is r.dominant_emotion
        assert abs(sum(r.distribution.values()) - 1.0) < 1e-6
        v, _ = te.mix_valence_arousal(r.distribution)
        assert (r.valence >= 0) == (v >= 0) or abs(r.valence) < 1e-9


# ── Classifier path ──

@pytest.fixture(scope="module")
def classifier():
    if not ec.load_blocking():
        pytest.skip(f"classifier unavailable: {ec.status()}")
    return ec


EXPECTED = [
    ("I'm so scared, I can't stop shaking.", {"Fear", "Terror", "Apprehension"}),
    ("I am absolutely furious with you.", {"Anger", "Rage", "Annoyance"}),
    ("I miss her so much it hurts.", {"Sadness", "Grief", "Disappointment"}),
    ("Thank you so much, this means a lot to me.", {"Gratitude"}),
    ("Haha that is hilarious, I can't stop laughing.", {"Amusement", "Joy"}),
    ("I'm really disappointed in how this turned out.", {"Disappointment", "Sadness"}),
    ("I am not happy about this at all.", {"Disappointment", "Annoyance", "Sadness", "Anger"}),
    ("That's disgusting, I feel sick.", {"Disgust", "Loathing"}),
    ("Wow, I did not see that coming!", {"Surprise", "Amazement", "Excitement"}),
    ("Phew, what a relief, it all worked out.", {"Relief", "Joy", "Gratitude"}),
    ("I love you.", {"Love"}),
    ("I'm so proud of what we built.", {"Pride"}),
    ("I hope you feel better soon, take care of yourself.", {"Compassion", "Optimism", "Hope"}),
    ("I'm nervous about the interview tomorrow.", {"Apprehension", "Fear"}),
]


@pytest.mark.parametrize("text,allowed", EXPECTED)
def test_classifier_names_the_obvious_emotion(classifier, text, allowed):
    r = te.analyze_text(text)
    assert r.source == "classifier"
    assert r.dominant_emotion.name in allowed, (text, r.dominant_emotion.name,
                                                [(e.name, round(w, 2)) for e, w in r.emotion_mix[:3]])


def test_classifier_valence_sign(classifier):
    for text, sign in [("The stop loss hit again, another loss.", -1),
                       ("The market means nothing, stop loss at this level.", -1),
                       ("We won! Best day ever.", +1),
                       ("I am not happy about this.", -1)]:
        r = te.analyze_text(text)
        assert (r.valence > 0) == (sign > 0), (text, r.valence, r.dominant_emotion.name)


def test_classifier_neutral_text_is_neutral(classifier):
    for text in ["The meeting is at 3pm in room 4.", "Send me the file when you get a chance.",
                 "BTC is at 64,200 and ETH at 3,100."]:
        r = te.analyze_text(text)
        assert r.is_neutral, (text, r.confidence, r.dominant_emotion.name)
