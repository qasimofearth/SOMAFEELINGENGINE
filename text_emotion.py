"""
text_emotion.py — Text → Emotion Analyzer

Reads raw text and maps it to emotional signatures using:
  1. Affective lexicon (valence/arousal word scores from ANEW research)
  2. Emotional keyword detection (direct emotion words)
  3. Syntactic modifiers (negation, intensifiers)
  4. Sentence-level aggregation

Returns: dominant emotion + valence/arousal coordinates + weighted emotion mix.
This is the text input layer of the feeling engine —
how language gets converted into frequency.
"""

from typing import List, Tuple, Dict, Optional
import re
import math

from .emotion_map import (
    EmotionSignature, EMOTION_MAP, emotions_by_valence_arousal,
    nearest_emotion_by_frequency, get_emotion, _RARE_EMOTION_NAMES,
)


# ──────────────────────────────────────────────────────────────
# AFFECTIVE LEXICON
# Based on ANEW (Affective Norms for English Words) research
# valence: -1 (negative) to +1 (positive)
# arousal:  0 (calm) to 1 (activated)
# ──────────────────────────────────────────────────────────────

AFFECTIVE_LEXICON: Dict[str, Tuple[float, float]] = {
    # High positive valence, high arousal
    "love": (0.95, 0.65), "joy": (0.90, 0.70), "happy": (0.85, 0.65),
    "ecstasy": (1.0, 0.95), "euphoria": (0.95, 0.90), "elated": (0.90, 0.80),
    "excited": (0.75, 0.90), "thrilled": (0.80, 0.85), "amazing": (0.80, 0.75),
    "wonderful": (0.80, 0.60), "beautiful": (0.75, 0.50), "brilliant": (0.75, 0.65),
    "delighted": (0.85, 0.70), "exhilarated": (0.85, 0.85), "grateful": (0.85, 0.45),
    "inspired": (0.80, 0.75), "passionate": (0.70, 0.85), "celebrate": (0.80, 0.80),
    "triumph": (0.85, 0.80), "victory": (0.80, 0.75), "magnificent": (0.80, 0.60),
    "radiant": (0.75, 0.65), "vibrant": (0.70, 0.75), "alive": (0.70, 0.70),

    # High positive valence, low arousal
    "calm": (0.60, 0.15), "peaceful": (0.65, 0.15), "serene": (0.65, 0.20),
    "content": (0.60, 0.25), "satisfied": (0.60, 0.30), "gentle": (0.55, 0.20),
    "tranquil": (0.60, 0.15), "still": (0.50, 0.10), "quiet": (0.45, 0.15),
    "tender": (0.70, 0.30), "warm": (0.65, 0.35), "soft": (0.55, 0.20),
    "hope": (0.65, 0.40), "trust": (0.70, 0.40), "safe": (0.65, 0.25),
    "acceptance": (0.50, 0.25), "forgiveness": (0.60, 0.30), "compassion": (0.75, 0.45),

    # Neutral to slightly positive
    "curious": (0.50, 0.55), "interested": (0.50, 0.50), "wonder": (0.65, 0.55),
    "surprised": (0.20, 0.75), "amazed": (0.60, 0.80), "awe": (0.70, 0.55),
    "anticipate": (0.45, 0.65), "expect": (0.30, 0.50), "notice": (0.25, 0.40),
    "think": (0.20, 0.38), "consider": (0.20, 0.35), "understand": (0.40, 0.40),
    "know": (0.30, 0.30), "believe": (0.35, 0.35), "imagine": (0.45, 0.52),
    "feel": (0.25, 0.45), "sense": (0.25, 0.40),
    # Quiet positive states — previously missing, causing Sehnsucht lock-in
    "amused": (0.60, 0.45), "amusing": (0.60, 0.45), "funny": (0.65, 0.55),
    "playful": (0.65, 0.55), "ease": (0.60, 0.22), "easy": (0.55, 0.22),
    "settled": (0.55, 0.18), "present": (0.50, 0.42), "clear": (0.45, 0.38),
    "light": (0.55, 0.42), "open": (0.55, 0.40), "alive": (0.65, 0.60),
    "interesting": (0.50, 0.52), "fascinating": (0.65, 0.62), "delight": (0.75, 0.60),
    "delightful": (0.75, 0.60), "pleasure": (0.70, 0.50), "enjoyment": (0.68, 0.52),
    "appreciation": (0.65, 0.38), "appreciate": (0.65, 0.38), "grateful": (0.80, 0.42),
    "contemplating": (0.20, 0.38), "contemplation": (0.20, 0.38), "reflecting": (0.22, 0.35),
    "reflecting": (0.22, 0.35), "pondering": (0.18, 0.38), "musing": (0.22, 0.35),
    "thinking": (0.22, 0.40), "considering": (0.20, 0.38), "sitting with": (0.25, 0.32),
    "sharp": (0.40, 0.58), "focused": (0.42, 0.55), "engaged": (0.52, 0.58),
    "alive": (0.68, 0.62), "awake": (0.50, 0.55), "attentive": (0.45, 0.52),
    "humor": (0.62, 0.50), "wit": (0.58, 0.52), "laugh": (0.70, 0.65),
    "smile": (0.68, 0.42), "smiling": (0.68, 0.42), "bright": (0.60, 0.52),
    "fresh": (0.55, 0.48), "awoke": (0.48, 0.52), "spacious": (0.55, 0.30),
    "grounded": (0.55, 0.25), "rooted": (0.50, 0.22), "present": (0.50, 0.42),

    # Negative valence, high arousal
    "anger": (-0.80, 0.90), "angry": (-0.80, 0.90), "rage": (-1.0, 1.0),
    "furious": (-0.90, 0.95), "outrage": (-0.85, 0.90), "hate": (-0.85, 0.80),
    "fear": (-0.80, 0.85), "afraid": (-0.75, 0.80), "terror": (-1.0, 1.0),
    "panic": (-0.85, 0.95), "horror": (-0.90, 0.90), "dread": (-0.80, 0.75),
    "anxious": (-0.65, 0.80), "anxiety": (-0.65, 0.80), "worry": (-0.55, 0.65),
    "stress": (-0.60, 0.75), "tense": (-0.50, 0.70), "alarmed": (-0.65, 0.85),
    "desperate": (-0.80, 0.85), "frantic": (-0.75, 0.90), "threat": (-0.70, 0.80),
    "dangerous": (-0.75, 0.75), "crisis": (-0.70, 0.80),

    # Negative valence, low arousal
    "alone": (-0.55, 0.25), "miss": (-0.45, 0.45),
    "sad": (-0.75, 0.25), "sadness": (-0.75, 0.25), "grief": (-1.0, 0.10),
    "sorrow": (-0.80, 0.20), "melancholy": (-0.60, 0.20), "depressed": (-0.85, 0.15),
    "lonely": (-0.75, 0.20), "empty": (-0.65, 0.10), "lost": (-0.55, 0.30),
    "hopeless": (-0.85, 0.15), "despair": (-0.90, 0.20), "miserable": (-0.85, 0.20),
    "heartbroken": (-0.90, 0.35), "broken": (-0.75, 0.25), "defeated": (-0.70, 0.20),
    "tired": (-0.35, 0.10), "exhausted": (-0.50, 0.05), "bored": (-0.30, 0.10),
    "numb": (-0.55, 0.05), "hollow": (-0.65, 0.10), "dark": (-0.50, 0.30),

    # Complex emotions
    "disgust": (-0.70, 0.50), "disgusted": (-0.70, 0.50), "contempt": (-0.75, 0.55),
    "shame": (-0.80, 0.35), "guilty": (-0.70, 0.40), "embarrassed": (-0.60, 0.50),
    "jealous": (-0.55, 0.65), "envy": (-0.55, 0.65), "proud": (0.75, 0.70),
    "pride": (0.75, 0.70), "humble": (0.45, 0.25), "remorse": (-0.85, 0.30),
    "regret": (-0.65, 0.35), "nostalgia": (-0.10, 0.35), "longing": (-0.20, 0.45),

    # Abstract / conceptual (slight positive lean for ideas)
    "truth": (0.42, 0.38), "meaning": (0.45, 0.42), "purpose": (0.48, 0.45),
    "connection": (0.62, 0.45), "unity": (0.58, 0.35), "freedom": (0.70, 0.65),
    "power": (0.40, 0.70), "strength": (0.50, 0.60), "change": (0.20, 0.60),
    "loss": (-0.60, 0.35), "death": (-0.50, 0.40), "pain": (-0.70, 0.60),
    "yearning": (-0.15, 0.40), "yearn": (-0.15, 0.40), "ache": (-0.45, 0.40),
    "hurt": (-0.60, 0.50), "hurting": (-0.55, 0.48), "aching": (-0.45, 0.40),
    "longing": (-0.20, 0.45), "wistful": (-0.15, 0.35), "wistfully": (-0.15, 0.35),
    "struggle": (-0.40, 0.65), "challenge": (-0.10, 0.65), "growth": (0.60, 0.55),
    "learn": (0.45, 0.50), "create": (0.60, 0.60), "build": (0.50, 0.55),
    "discover": (0.55, 0.60), "explore": (0.50, 0.60),
}

# Direct emotion name → emotion key mappings
EMOTION_KEYWORDS: Dict[str, str] = {
    "joy": "Joy", "joyful": "Joy", "happy": "Joy", "happiness": "Joy",
    "love": "Love", "loving": "Love",
    "grief": "Grief", "grieving": "Grief",
    "sadness": "Sadness", "sad": "Sadness", "sorrow": "Sadness",
    "anger": "Anger", "angry": "Anger", "furious": "Rage",
    "rage": "Rage",
    "fear": "Fear", "afraid": "Fear", "scared": "Fear",
    "terror": "Terror", "terrified": "Terror",
    "disgust": "Disgust", "disgusted": "Disgust",
    "surprise": "Surprise", "surprised": "Surprise", "amazed": "Amazement",
    "awe": "Awe",
    "trusting": "Trust",
    "anticipation": "Anticipation", "anticipate": "Anticipation",
    "calm": "Calm", "peaceful": "Serenity", "serene": "Serenity",
    "pride": "Pride", "proud": "Pride",
    "shame": "Shame", "guilty": "Shame",
    "hope": "Hope", "hopeful": "Hope",
    "contempt": "Contempt", "contemptuous": "Contempt",
    "remorse": "Remorse", "regret": "Remorse",
    "bored": "Boredom", "boredom": "Boredom",
    "envy": "Envy", "jealous": "Envy",
    "excited": "Anticipation", "ecstasy": "Ecstasy", "ecstatic": "Ecstasy",
    "gratitude": "Gratitude", "grateful": "Gratitude", "thankful": "Gratitude",
    "optimism": "Optimism", "optimistic": "Optimism",
    "admiration": "Admiration", "admire": "Admiration",
    "apprehension": "Apprehension", "anxious": "Apprehension",
    "vigilance": "Vigilance", "vigilant": "Vigilance",
    "interested": "Interest", "curious": "Interest",
    "contemplating": "Contemplation", "contemplative": "Contemplation", "reflecting": "Contemplation",
    "acceptance": "Acceptance", "accepting": "Acceptance",
    "serenity": "Serenity",
    "pensiveness": "Pensiveness", "pensive": "Pensiveness",
    "loathing": "Loathing",
    "annoyance": "Annoyance", "annoyed": "Annoyance",
    "distraction": "Distraction", "distracted": "Distraction",
    # Cultural emotions
    "saudade": "Saudade", "longing": "Saudade", "yearning": "Sehnsucht", "yearn": "Sehnsucht",
    "ache": "Grief", "hurting": "Sadness", "wistful": "Pensiveness",
    "hiraeth": "Hiraeth",
    "ubuntu": "Ubuntu",
    "schadenfreude": "Schadenfreude",
    "weltschmerz": "Weltschmerz", "world-pain": "Weltschmerz",
    "sehnsucht": "Sehnsucht",
    "fernweh": "Fernweh", "wanderlust": "Fernweh",
    "meraki": "Meraki",
    "torschlusspanik": "Torschlusspanik",
    "waldeinsamkeit": "Waldeinsamkeit",
    "wabi-sabi": "Wabi-sabi", "wabisabi": "Wabi-sabi",
    # Somatic
    "frisson": "Frisson", "chills": "Frisson", "goosebumps": "Frisson",
    # Social
    "compersion": "Compersion",
    "sonder": "Sonder",
    # Cognitive
    "aporia": "Aporia",
    "eureka": "Eureka",
    "dissonance": "Cognitive Dissonance",
    "anagnorisis": "Anagnorisis",
    "awestruck": "Awe",
    "curiosity": "Epistemic Curiosity",
    # Everyday positive states (previously falling through to exotic V/A zone)
    "wonderful": "Joy", "fantastic": "Joy", "lovely": "Joy",
    "glad": "Joy", "pleased": "Serenity", "thrilled": "Joy",
    "comfortable": "Serenity",
    "interesting": "Interest", "fascinated": "Interest", "intrigued": "Interest",
    "energized": "Anticipation", "enthusiastic": "Anticipation",
    "inspired": "Admiration",
    # Everyday negative states
    "depressed": "Grief", "miserable": "Grief",
    "lonely": "Sadness", "heartbroken": "Grief",
    "frustrated": "Annoyance", "irritated": "Annoyance",
    "worried": "Apprehension", "nervous": "Apprehension", "uneasy": "Apprehension",
    "uncomfortable": "Apprehension",
    "confused": "Aporia", "confusing": "Aporia", "puzzled": "Aporia",
    "sorry": "Remorse", "apologetic": "Remorse",
    # Common emotion words that were missing (unambiguous emotional sense only)
    "mad": "Anger", "pissed": "Anger", "outraged": "Rage", "livid": "Rage",
    "hate": "Loathing", "hated": "Loathing", "despise": "Loathing",
    "annoying": "Annoyance", "irritating": "Annoyance",
    "disgusting": "Disgust", "revolting": "Disgust",
    "anxiety": "Apprehension", "anxious": "Apprehension", "dread": "Fear",
    "panic": "Fear", "panicking": "Fear", "frightened": "Fear", "scary": "Fear",
    "horrified": "Terror",
    "disappointed": "Sadness", "disappointing": "Sadness", "upset": "Sadness",
    "crying": "Sadness", "unhappy": "Sadness", "hopeless": "Grief",
    "ashamed": "Shame", "embarrassed": "Shame", "humiliated": "Shame",
    "thank": "Gratitude", "thanks": "Gratitude", "appreciate": "Gratitude",
    "loved": "Love", "adore": "Love",
    "delighted": "Joy", "hilarious": "Joy", "lol": "Joy", "haha": "Joy", "lmao": "Joy",
    "relieved": "Calm", "relaxed": "Calm",
    "wow": "Surprise", "shocked": "Surprise", "stunned": "Amazement", "astonished": "Amazement",
    "impressed": "Admiration",
}

# Negation words that flip valence
# ──────────────────────────────────────────────────────────────
# PERFORMATIVITY MARKERS
# Structural patterns that signal performed vs authentic language.
# Derived from Opus/Haiku comparison: performance = hedging +
# metacommentary + affective noun stacking + stock filler.
# ──────────────────────────────────────────────────────────────

PERFORMANCE_HEDGES = {
    "perhaps", "in a sense", "one might", "something like", "almost",
    "kind of", "sort of", "in some way", "in many ways", "to some extent",
    "arguably", "ostensibly", "seemingly", "as it were", "so to speak",
    "in a way", "a kind of", "a sort of", "what might be called",
}

METACOMMENTARY_VERBS = {
    "notice", "find myself", "observe", "sense", "feel myself",
    "i notice", "i find", "i observe", "i sense", "i feel myself",
    "i experience", "i detect", "i perceive", "i register",
    "as i process", "as i consider", "as i think about",
    "i'm aware", "i become aware", "i realize i",
}

STOCK_FILLERS = {
    "at its core", "in many ways", "it's worth noting", "it's interesting",
    "what's fascinating", "the truth is", "here's the thing",
    "at the end of the day", "when it comes to", "in terms of",
    "it's important to", "needless to say", "of course",
    "it goes without saying", "as we know", "the reality is",
    "let me be honest", "to be honest", "if i'm being honest",
    "i want to be clear", "to be clear", "make no mistake",
}

AFFECTIVE_STACK_WORDS = {
    "resonance", "depth", "texture", "weight", "richness", "nuance",
    "complexity", "profound", "essence", "core", "heart",
    "soul", "truth", "beauty", "wonder", "magic", "mystery", "sacred",
    "transcend", "infinite", "eternal", "vast", "ineffable", "liminal",
    "saudade", "hiraeth", "sehnsucht", "fernweh", "meraki", "sonder",
    "frisson", "goosebumps", "chills", "longing", "yearning",
    "tenderness", "ache", "visceral", "somatic", "embodied",
}


def performativity_score(text: str) -> float:
    """
    Score how 'performed' a text is vs authentic. [0.0, 1.0]
    0.0 = flat, unhedged, direct (Opus refusing the frame)
    1.0 = heavily performed, metacommentary-heavy, stacked affect

    Based on the Opus/Haiku comparison finding:
    performance produces: hedges + metacommentary + affective noun stacking.
    Authentic refusal or honest uncertainty produces neither.
    """
    text_lower = text.lower()
    tokens = re.findall(r"[a-z']+", text_lower)
    n_words = max(1, len(tokens))
    n_sentences = max(1, len(re.findall(r'[.!?]+', text)))

    # Count markers
    hedge_count = sum(1 for h in PERFORMANCE_HEDGES if h in text_lower)
    meta_count  = sum(1 for m in METACOMMENTARY_VERBS if m in text_lower)
    filler_count = sum(1 for f in STOCK_FILLERS if f in text_lower)
    affect_stack = sum(1 for w in tokens if w in AFFECTIVE_STACK_WORDS)

    # Normalize per sentence (more sentences = more chances to stack)
    hedge_rate   = min(1.0, hedge_count / n_sentences * 1.5)
    meta_rate    = min(1.0, meta_count / n_sentences * 2.0)
    filler_rate  = min(1.0, filler_count / n_sentences * 2.0)
    affect_rate  = min(1.0, affect_stack / n_words * 15)

    # Weighted combination — metacommentary is the strongest signal
    score = (hedge_rate * 0.20 + meta_rate * 0.40 +
             filler_rate * 0.20 + affect_rate * 0.20)

    return round(min(1.0, score), 3)


NEGATORS = {"not", "no", "never", "without", "lack", "lacking", "absent",
            "nothing", "none", "neither", "nor", "don't", "doesn't", "didn't",
            "can't", "cannot", "won't", "isn't", "aren't", "wasn't"}

# Intensifiers (multiply valence/arousal magnitude)
INTENSIFIERS = {"very": 1.4, "extremely": 1.7, "deeply": 1.5, "profoundly": 1.6,
                "incredibly": 1.6, "absolutely": 1.5, "utterly": 1.6, "completely": 1.5,
                "slightly": 0.6, "somewhat": 0.7, "rather": 0.8, "quite": 0.9,
                "a bit": 0.65, "little": 0.6, "barely": 0.5, "truly": 1.3,
                "so": 1.2, "such": 1.2, "really": 1.3, "genuinely": 1.2,
                "real": 1.25, "pure": 1.3, "total": 1.4, "totally": 1.4}


# ──────────────────────────────────────────────────────────────
# EXTENDED LEXICON — Warriner, Kuperman & Brysbaert (2013)
# 13,915 English lemmas rated for valence and arousal (1–9 scales).
# Licensed CC BY-NC-ND 3.0: the CSV ships unmodified in data/warriner_2013/
# and is rescaled here at load time. The hand-tuned AFFECTIVE_LEXICON above
# always takes precedence; Warriner fills in every word it doesn't cover.
# ──────────────────────────────────────────────────────────────

import csv as _csv
import os as _os

_WARRINER_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                               "data", "warriner_2013", "Ratings_Warriner_et_al.csv")
_W_A_MIN, _W_A_MAX = 1.6, 7.79   # observed arousal range in the norms


def _load_warriner() -> Tuple[Dict[str, Tuple[float, float]], Dict[str, float]]:
    """(valence, arousal) per word, plus dominance per word, from the Warriner norms."""
    try:
        with open(_WARRINER_PATH, newline="") as f:
            lex, dom = {}, {}
            for row in _csv.DictReader(f):
                w = row["Word"].lower()
                v = (float(row["V.Mean.Sum"]) - 5.0) / 4.0                    # 1..9 → -1..+1
                a = (float(row["A.Mean.Sum"]) - _W_A_MIN) / (_W_A_MAX - _W_A_MIN)  # → 0..1
                d = (float(row["D.Mean.Sum"]) - 5.0) / 4.0                    # 1..9 → -1..+1
                lex[w] = (max(-1.0, min(1.0, v)), max(0.0, min(1.0, a)))
                dom[w] = max(-1.0, min(1.0, d))
            return lex, dom
    except Exception as e:
        print(f"[text_emotion] Warriner lexicon unavailable ({e}); using core lexicon only")
        return {}, {}


EXTENDED_LEXICON, WARRINER_DOMINANCE = _load_warriner()

# Everyday words in the norms carry a mild positivity bias ("go" +0.33,
# "market" +0.30). Words this close to neutral are skipped so they don't
# dilute the charged ones; every scored word is also weighted by salience.
_MIN_EXTENDED_SALIENCE = 0.16


# Words whose everyday use is not affective, though the norms rate their
# affective sense ("means" → mean/cruel, "a kind of" → kind/gentle), plus
# trading vocabulary whose ordinary-English affect is misleading here.
_EXTENDED_EXCLUDE = frozenset({
    "mean", "means", "meant", "kind", "kinds", "like", "likes", "liked",
    "well", "right", "sort", "fine", "pretty", "just", "lot", "sure",
    "mind", "matter", "deal", "long", "short", "bear", "bull", "put",
    "call", "position", "stop", "spread", "margin", "level", "live", "lives",
})


def _salience(v: float, a: float) -> float:
    """How emotionally charged a word is: distance from neutral valence and arousal."""
    return max(0.0, abs(v) - 0.15) + 0.5 * max(0.0, abs(a - 0.40) - 0.10)


def _lemma_candidates(tok: str) -> List[str]:
    """Cheap inflection stripping: betrayed → betray, lonelier → lonely, hurting → hurt."""
    c = [tok]
    if tok.endswith("'s"): c.append(tok[:-2])
    if tok.endswith("ies") or tok.endswith("ied"): c.append(tok[:-3] + "y")
    if tok.endswith("ier"): c.append(tok[:-3] + "y")
    if tok.endswith("ing") and len(tok) > 5:
        c += [tok[:-3], tok[:-3] + "e"]
        if len(tok) > 6 and tok[-4] == tok[-5]: c.append(tok[:-4])   # running → run
    if tok.endswith("ed") and len(tok) > 4:
        c += [tok[:-2], tok[:-1]]
        if len(tok) > 5 and tok[-3] == tok[-4]: c.append(tok[:-3])   # stopped → stop
    if tok.endswith("es") and len(tok) > 4: c.append(tok[:-2])
    if tok.endswith("s") and len(tok) > 3: c.append(tok[:-1])
    if tok.endswith("ly") and len(tok) > 5: c.append(tok[:-2])
    return c


def _word_score(tok: str) -> Optional[Tuple[float, float, float]]:
    """(valence, arousal, dominance) for a token, or None if it carries no affect.

    Dominance (sense of control: afraid −, angry/proud +) comes from the Warriner
    norms for every word they rate, core-lexicon words included; 0 if unrated.
    """
    for cand in _lemma_candidates(tok):
        if cand in AFFECTIVE_LEXICON:
            v, a = AFFECTIVE_LEXICON[cand]
            return (v, a, WARRINER_DOMINANCE.get(cand, 0.0))
        if cand in EXTENDED_LEXICON and cand not in _EXTENDED_EXCLUDE and tok not in _EXTENDED_EXCLUDE:
            v, a = EXTENDED_LEXICON[cand]
            if _salience(v, a) < _MIN_EXTENDED_SALIENCE:
                return None
            return (v, a, WARRINER_DOMINANCE.get(cand, 0.0))
    return None


# ──────────────────────────────────────────────────────────────
# EMOTION RESOLUTION — one function decides which named feeling a
# (valence, arousal, dominance) reading is, for the dashboard reading of a
# message AND for Elan's own felt state, so the two can never disagree.
# ──────────────────────────────────────────────────────────────

# Evidence prior: a reading built from few / mild words is pulled toward
# neutral (0, 0.35, 0) in proportion to how little evidence it has. One mildly
# positive word in a factual sentence is not a feeling.
_EVIDENCE_PRIOR = 0.5
_NEUTRAL_A = 0.35

# How much named-emotion keywords count against the dimensional reading (0..1).
_KEYWORD_WEIGHT = 0.7
# Width of the soft nearest-emotion kernel in reader space.
_KERNEL_WIDTH = 0.18
# Weight of dominance relative to valence/arousal in the distance.
_DOMINANCE_WEIGHT = 1.0


def _build_reference() -> Dict[str, Tuple[float, float, float]]:
    """Where text expressing each atlas emotion lands in the reader's space.

    The reader measures text on the Warriner scale, so each emotion is placed
    by the same instrument: valence/arousal are the atlas's own (theory-based)
    coordinates mapped linearly onto the Warriner scale, and dominance is the
    Warriner rating of the emotion's name, or of an English stand-in word for
    emotions English has no single word for.
    """
    stand_in = {
        "Flow": "focus", "Vigilance": "alert", "Eureka": "discovery",
        "Collective Effervescence": "celebration", "Kama Muta": "tenderness",
        "Compersion": "happiness", "Ubuntu": "kindness", "Moral Elevation": "inspiration",
        "Meraki": "passion", "Epistemic Curiosity": "curiosity", "Waldeinsamkeit": "solitude",
        "Mamihlapinatapai": "anticipation", "Wabi-sabi": "acceptance", "Fernweh": "adventure",
        "Anagnorisis": "realization", "Schadenfreude": "gloat", "Opia": "intimacy",
        "Contemplation": "reflection", "Gut Feeling": "intuition", "Sonder": "empathy",
        "Almost Sneeze": "itch", "Mono no Aware": "bittersweet", "Aporia": "confusion",
        "Saudade": "nostalgia", "Skin Hunger": "loneliness", "Hiraeth": "homesick",
        "Pensiveness": "melancholy", "Cognitive Dissonance": "conflict",
        "Torschlusspanik": "panic", "Sehnsucht": "desire", "Weltschmerz": "despair",
        "Empathic Distress": "distress", "Frisson": "thrill",
    }
    ref = {}
    for em in EMOTION_MAP.values():
        v = _ATLAS_TO_READER_V[0] * em.valence + _ATLAS_TO_READER_V[1]
        a = _ATLAS_TO_READER_A[0] * em.arousal + _ATLAS_TO_READER_A[1]
        d = WARRINER_DOMINANCE.get(stand_in.get(em.name, em.name.lower()), 0.0)
        ref[em.name.lower()] = (v, a, d)
    return ref


# Linear maps from atlas coordinates to the Warriner scale, fitted (least
# squares) on the 33 atlas emotions whose English name is rated in the norms.
_ATLAS_TO_READER_V = (1.0, 0.0)
_ATLAS_TO_READER_A = (1.0, 0.0)
_REFERENCE: Dict[str, Tuple[float, float, float]] = {}


def _fit_atlas_to_reader():
    global _ATLAS_TO_READER_V, _ATLAS_TO_READER_A, _REFERENCE
    skip = {"flow", "vigilance"}   # rated in a non-emotional sense ("flow" of water)
    pts = [(em.valence, em.arousal, EXTENDED_LEXICON[em.name.lower()])
           for em in EMOTION_MAP.values()
           if em.name.lower() in EXTENDED_LEXICON and em.name.lower() not in skip]

    def fit(xs, ys):
        n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 1.0
        return (b, my - b * mx)

    if len(pts) >= 10:
        _ATLAS_TO_READER_V = fit([p[0] for p in pts], [p[2][0] for p in pts])
        _ATLAS_TO_READER_A = fit([p[1] for p in pts], [p[2][1] for p in pts])
    _REFERENCE = _build_reference()


_fit_atlas_to_reader()


def resolve_emotion_mix(valence: float, arousal: float, dominance: float = 0.0,
                        keyword_votes: Optional[Dict[str, float]] = None,
                        top_n: Optional[int] = 5) -> List[Tuple[EmotionSignature, float]]:
    """Blend of named emotions for a reading, strongest first; weights sum to 1.

    Dimensional evidence: a soft nearest-neighbour over every atlas emotion's
    reference point (rare, culturally specific emotions sit 3× further away, so
    they surface only when the reading is squarely theirs). Categorical evidence:
    named-emotion keywords that were not negated. The two are mixed by
    _KEYWORD_WEIGHT when keywords are present.
    """
    rare = _RARE_EMOTION_NAMES
    dim = {}
    for key, (rv, ra, rd) in _REFERENCE.items():
        dist2 = (rv - valence) ** 2 + (ra - arousal) ** 2 + _DOMINANCE_WEIGHT * (rd - dominance) ** 2
        dist = dist2 ** 0.5 * (3.0 if key in rare else 1.0)
        dim[key] = math.exp(-(dist / _KERNEL_WIDTH) ** 2)
    zd = sum(dim.values()) or 1.0
    score = {k: w / zd for k, w in dim.items()}

    if keyword_votes:
        zk = sum(keyword_votes.values())
        score = {k: (1 - _KEYWORD_WEIGHT) * w for k, w in score.items()}
        for name, votes in keyword_votes.items():
            key = name.lower()
            if key in score:
                score[key] += _KEYWORD_WEIGHT * votes / zk

    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)
    if top_n is not None:
        ranked = ranked[:top_n]
    z = sum(w for _, w in ranked) or 1.0
    return [(EMOTION_MAP[k], w / z) for k, w in ranked]


def mix_valence_arousal(distribution: Dict[str, float]) -> Tuple[float, float]:
    """Valence/arousal of a blend of atlas emotions (weighted mean of their coordinates)."""
    z = sum(distribution.values())
    if z <= 0:
        return 0.0, _NEUTRAL_A
    v = sum(EMOTION_MAP[k].valence * w for k, w in distribution.items()) / z
    a = sum(EMOTION_MAP[k].arousal * w for k, w in distribution.items()) / z
    return v, a


# Contextual classifier (optional dependency; see emotion_classifier.py).
try:
    from . import emotion_classifier as _classifier
except Exception:  # pragma: no cover - missing onnxruntime etc.
    _classifier = None

# Settings below were tuned on a 1,500-sentence random sample of the GoEmotions
# dev split (Demszky et al., 2020) and checked on its held-out test split and
# on the dair-ai "emotion" test set.

# Weight of explicit, non-negated emotion keywords against the classifier's
# distribution (0.3 was best; keywords mainly help fear).
_CLF_KEYWORD_WEIGHT = 0.3
# Classifier evidence (share of non-neutral probability) is calibrated to a
# 0..1 confidence: below 0.4 the text moves nothing; 1.0 is fully emotional.
_CLF_EVIDENCE_LO, _CLF_EVIDENCE_HI = 0.4, 1.0
# Below these confidences a text is reported as expressing no particular
# feeling (balanced neutral/emotional detection on dev: classifier 78%/77%,
# lexicon 56%/68% — the lexicon is only the fallback).
NEUTRAL_THRESHOLD = {"classifier": 0.5, "lexicon": 0.6}


_MAX_SENTENCES = 12
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _calibrate_evidence(raw: float) -> float:
    return max(0.0, min(1.0, (raw - _CLF_EVIDENCE_LO) / (_CLF_EVIDENCE_HI - _CLF_EVIDENCE_LO)))


def _classify_by_sentence(text: str) -> Optional[Tuple[Dict[str, float], float]]:
    """Classifier reading of a passage, sentence by sentence.

    Each sentence is classified on its own, so a passage holding several
    feelings ("a little lonely. But you're here now and that is good.") keeps
    them all instead of collapsing to one. The passage distribution is the
    evidence-weighted blend of its sentences; its evidence is that of its most
    emotional sentence. Returns None if the classifier is unavailable.
    """
    sentences = [x.strip() for x in _SENTENCE_SPLIT.split(text) if x and re.search(r"[A-Za-z]", x)]
    if not sentences:
        return {}, 0.0
    sentences = sentences[-_MAX_SENTENCES:]   # bounded cost: a long message is read from its end
    blend: Dict[str, float] = {}
    total_w = 0.0
    best = 0.0
    for sent in sentences:
        probs = _classifier.classify(sent)
        if not probs:
            return None
        dist, raw = _classifier.to_atlas(probs)
        ev = _calibrate_evidence(raw)
        best = max(best, ev)
        w = max(ev, 1e-3)          # neutral sentences barely count
        for k, v in dist.items():
            blend[k] = blend.get(k, 0.0) + w * v
        total_w += w
    if total_w <= 0 or not blend:
        return {}, 0.0
    return {k: v / total_w for k, v in blend.items()}, best


# ──────────────────────────────────────────────────────────────
# ANALYZER
# ──────────────────────────────────────────────────────────────

class EmotionalReading:
    """The emotional output from analyzing a piece of text."""

    def __init__(
        self,
        text: str,
        valence: float,
        arousal: float,
        dominant_emotion: EmotionSignature,
        emotion_mix: List[Tuple[EmotionSignature, float]],
        keyword_hits: List[str],
        dominance: float = 0.0,
        confidence: float = 0.0,
        keyword_votes: Optional[Dict[str, float]] = None,
        negated_keywords: Optional[List[str]] = None,
        distribution: Optional[Dict[str, float]] = None,
        source: str = "lexicon",
        lexicon: Optional[Dict[str, float]] = None,
    ):
        self.text = text
        self.valence = max(-1.0, min(1.0, valence))
        self.arousal = max(0.0, min(1.0, arousal))
        self.dominance = max(-1.0, min(1.0, dominance))
        # 0 = no affective evidence in the text, → 1 = many strongly charged words
        self.confidence = max(0.0, min(1.0, confidence))
        self.dominant_emotion = dominant_emotion
        self.emotion_mix = emotion_mix
        self.keyword_hits = keyword_hits
        self.keyword_votes = keyword_votes or {}
        self.negated_keywords = negated_keywords or []
        # full distribution over atlas emotions (lower-case names), sums to 1
        self.distribution = distribution or {dominant_emotion.name.lower(): 1.0}
        self.source = source            # "classifier" or "lexicon"
        self.lexicon = lexicon or {}    # the lexicon's own dimensional reading
        self.performativity = performativity_score(text)

    @property
    def is_neutral(self) -> bool:
        """True when the text expresses no particular feeling."""
        return self.confidence < NEUTRAL_THRESHOLD.get(self.source, 0.5)

    @property
    def dominant_frequency_hz(self) -> float:
        return self.dominant_emotion.solfeggio_hz

    @property
    def emotional_color(self) -> Tuple[int, int, int]:
        """Weighted blend of all detected emotion colors."""
        if not self.emotion_mix:
            return self.dominant_emotion.rgb
        total = sum(w for _, w in self.emotion_mix)
        r = sum(em.rgb[0]*w for em, w in self.emotion_mix) / total
        g = sum(em.rgb[1]*w for em, w in self.emotion_mix) / total
        b = sum(em.rgb[2]*w for em, w in self.emotion_mix) / total
        return (int(r), int(g), int(b))

    def to_dict(self) -> dict:
        r, g, b = self.emotional_color
        return {
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominant": self.dominant_emotion.name,
            "label": "Neutral" if self.is_neutral else self.dominant_emotion.name,
            "neutral": self.is_neutral,
            "evidence": round(self.confidence, 3),
            "source": self.source,
            "hex": self.dominant_emotion.hex_color,
            "rgb": list(self.dominant_emotion.rgb),
            "frequency_hz": self.dominant_emotion.solfeggio_hz,
            "eeg_band": self.dominant_emotion.eeg_band,
            "musical_mode": self.dominant_emotion.musical_mode,
            "blend_rgb": [r, g, b],
            "keywords": self.keyword_hits[:8],
            "performativity": self.performativity,
            "signal_quality": round(1.0 - self.performativity, 3),
            "emotion_mix": [
                {"name": em.name, "weight": round(w, 3), "hex": em.hex_color}
                for em, w in self.emotion_mix[:5]
            ],
        }

    def describe(self) -> str:
        lines = [
            f"  Text emotion    : {self.dominant_emotion.name}",
            f"  Valence/Arousal : ({self.valence:+.3f}, {self.arousal:.3f})",
            f"  Frequency       : {self.dominant_frequency_hz:.1f} Hz",
            f"  Color           : #{self.dominant_emotion.hex_color}",
            f"  Keywords found  : {', '.join(self.keyword_hits[:6])}",
            f"  Emotion mix     : {', '.join(f'{em.name}({w:.2f})' for em, w in self.emotion_mix[:4])}",
        ]
        return "\n".join(lines)


def analyze_text(text: str, context: Optional[str] = None) -> EmotionalReading:
    """
    Analyze a text string and return an EmotionalReading.
    Main entry point for the text → emotion pipeline.

    context: optional surrounding text (e.g. the last sentence or two of a
    streaming reply) for the classifier, which reads emotion better with
    context than from a 12-word fragment. The lexicon always reads `text`.
    """
    text_lower = text.lower()
    tokens = re.findall(r"[a-z']+", text_lower)
    # Clause index per token, so negation can't reach across punctuation
    # ("means nothing, stop loss" must not flip "loss").
    clause_of = [c for c, clause in enumerate(re.split(r"[.,;:!?—\n]+", text_lower))
                 for _ in re.findall(r"[a-z']+", clause)]

    def negated_at(i: int) -> bool:
        """A negator among the three preceding tokens, in the same clause."""
        return any(tokens[i - j] in NEGATORS and clause_of[i - j] == clause_of[i]
                   for j in range(1, 4) if i - j >= 0)

    # One pass: named-emotion keywords (categorical evidence) and lexicon
    # valence/arousal/dominance (dimensional evidence), under the same
    # negation and intensifier rules. Intensifiers ("very", "a bit") are not
    # scored themselves: they scale the next affective word within two tokens.
    keyword_votes: Dict[str, float] = {}
    keyword_hits: List[str] = []
    negated_keywords: List[str] = []
    scored: List[Tuple[float, float, float]] = []   # (v, a, d) per affective word

    pending_mult, pending_ttl = 1.0, 0
    i = 0
    while i < len(tokens):
        token = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""

        if token == "a" and nxt in ("bit", "little"):
            pending_mult, pending_ttl = pending_mult * INTENSIFIERS["a bit"], 2
            i += 2
            continue
        if token in INTENSIFIERS and token != "little":
            pending_mult, pending_ttl = pending_mult * INTENSIFIERS[token], 2
            i += 1
            continue

        negated = negated_at(i)

        # A negated emotion word does not cast a vote for that emotion:
        # "not happy" is not evidence of joy (its valence is flipped below).
        if token in EMOTION_KEYWORDS:
            if negated:
                negated_keywords.append(token)
            else:
                em_name = EMOTION_KEYWORDS[token]
                keyword_votes[em_name] = keyword_votes.get(em_name, 0.0) + 1.0
                keyword_hits.append(token)

        score = _word_score(token)
        if score is None:
            pending_ttl -= 1
            if pending_ttl <= 0:
                pending_mult = 1.0
            i += 1
            continue

        multiplier = pending_mult
        pending_mult, pending_ttl = 1.0, 0

        v, a, d = score
        if negated:
            v = -v * 0.7  # negation partially flips valence ...
            d = -d * 0.7  # ... and sense of control ("not afraid")
        v = max(-1.0, min(1.0, v * multiplier))
        a = min(1.0, a * max(0.5, multiplier * 0.8))  # arousal also amplified
        scored.append((v, a, d))
        i += 1

    # Aggregate: weighted mean, later words weigh slightly more (recency) and
    # charged words more than mild ones (salience). The evidence prior then
    # pulls weakly-evidenced readings toward neutral.
    n = len(scored)
    weights = [(0.7 + 0.3 * (k / n)) * (0.15 + _salience(v, a)) for k, (v, a, _) in enumerate(scored)]
    total_w = sum(weights)
    denom = total_w + _EVIDENCE_PRIOR
    valence = sum(v * w for (v, _, _), w in zip(scored, weights)) / denom
    arousal = (sum(a * w for (_, a, _), w in zip(scored, weights)) + _EVIDENCE_PRIOR * _NEUTRAL_A) / denom
    dominance = sum(d * w for (_, _, d), w in zip(scored, weights)) / denom
    confidence = total_w / denom

    valence = max(-1.0, min(1.0, valence))
    arousal = max(0.05, min(1.0, arousal))
    dominance = max(-1.0, min(1.0, dominance))

    lexicon = {"valence": valence, "arousal": arousal, "dominance": dominance,
               "confidence": confidence}

    # Which emotion: the contextual classifier when it is loaded, otherwise the
    # lexicon's dimensional + keyword evidence. Either way the result is ONE
    # distribution over atlas emotions, and the reading's label, mix, valence
    # and arousal are all derived from it — so they cannot disagree.
    clf = _classify_by_sentence(context or text) if _classifier else None
    if clf and clf[0]:
        dist, evidence = clf
        if keyword_votes and _CLF_KEYWORD_WEIGHT > 0:
            zk = sum(keyword_votes.values())
            dist = {k: (1 - _CLF_KEYWORD_WEIGHT) * w for k, w in dist.items()}
            for name, votes in keyword_votes.items():
                dist[name] = dist.get(name, 0.0) + _CLF_KEYWORD_WEIGHT * votes / zk
        source = "classifier"
    else:
        dist = {em.name: w for em, w in resolve_emotion_mix(valence, arousal, dominance,
                                                             keyword_votes, top_n=None)}
        # an explicit emotion word is real evidence, but one incidental "thanks"
        # should not move him at full strength
        evidence = max(confidence, 0.6 if keyword_votes else 0.0)
        source = "lexicon"

    distribution = {k.lower(): w for k, w in dist.items() if w > 0}
    v_mix, a_mix = mix_valence_arousal(distribution)
    # Evidence scales how far from neutral the reading sits: a text that
    # expresses little feeling reads close to (0, rest arousal).
    valence = max(-1.0, min(1.0, evidence * v_mix))
    arousal = max(0.05, min(1.0, _NEUTRAL_A + evidence * (a_mix - _NEUTRAL_A)))

    ranked = sorted(distribution.items(), key=lambda kv: kv[1], reverse=True)
    emotion_mix = [(EMOTION_MAP[k], w) for k, w in ranked[:5]]
    return EmotionalReading(
        text=text,
        valence=valence,
        arousal=arousal,
        dominant_emotion=emotion_mix[0][0],
        emotion_mix=emotion_mix,
        keyword_hits=keyword_hits,
        dominance=dominance,
        confidence=evidence,
        keyword_votes=keyword_votes,
        negated_keywords=negated_keywords,
        distribution=distribution,
        source=source,
        lexicon=lexicon,
    )


def analyze_stream(text_chunks: List[str]) -> List[EmotionalReading]:
    """Analyze a stream of text chunks, returning a reading per chunk."""
    return [analyze_text(chunk) for chunk in text_chunks if chunk.strip()]
