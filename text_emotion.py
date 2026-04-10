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
    nearest_emotion_by_frequency, get_emotion,
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

    # Intensifiers (handled separately, but included for lexicon completeness)
    "very": (0, 0), "extremely": (0, 0), "deeply": (0, 0), "profoundly": (0, 0),
    "slightly": (0, 0), "somewhat": (0, 0), "rather": (0, 0),

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
    "awe": "Awe", "awesome": "Awe",
    "trust": "Trust", "trusting": "Trust",
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
    "interest": "Interest", "curious": "Interest",
    "contemplat": "Contemplation", "contemplative": "Contemplation", "reflecting": "Contemplation",
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
    "flow": "Flow", "in the zone": "Flow",
    # Social
    "compersion": "Compersion",
    "sonder": "Sonder",
    # Cognitive
    "aporia": "Aporia",
    "eureka": "Eureka",
    "dissonance": "Cognitive Dissonance",
    "anagnorisis": "Anagnorisis",
    "wonder": "Awe", "awestruck": "Awe",
    "curiosity": "Epistemic Curiosity", "curious": "Epistemic Curiosity",
    # Everyday positive states (previously falling through to exotic V/A zone)
    "good": "Serenity", "great": "Joy", "nice": "Serenity",
    "wonderful": "Joy", "fantastic": "Joy", "lovely": "Joy",
    "glad": "Joy", "pleased": "Serenity", "thrilled": "Joy",
    "comfortable": "Serenity",
    "fine": "Calm", "alright": "Calm", "okay": "Calm",
    "interesting": "Interest", "fascinated": "Interest", "intrigued": "Interest",
    "energized": "Anticipation", "enthusiastic": "Anticipation",
    "inspired": "Admiration", "moved": "Awe",
    # Everyday negative states
    "awful": "Sadness", "terrible": "Sadness", "horrible": "Sadness",
    "depressed": "Grief", "miserable": "Grief",
    "lonely": "Sadness", "heartbroken": "Grief",
    "frustrated": "Annoyance", "irritated": "Annoyance",
    "worried": "Apprehension", "nervous": "Apprehension", "uneasy": "Apprehension",
    "uncomfortable": "Apprehension",
    "confused": "Distraction", "lost": "Pensiveness",
    "sorry": "Remorse", "apologetic": "Remorse",
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
                "so": 1.2, "such": 1.2, "really": 1.3, "genuinely": 1.2}


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
    ):
        self.text = text
        self.valence = max(-1.0, min(1.0, valence))
        self.arousal = max(0.0, min(1.0, arousal))
        self.dominant_emotion = dominant_emotion
        self.emotion_mix = emotion_mix
        self.keyword_hits = keyword_hits
        self.performativity = performativity_score(text)

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


def analyze_text(text: str) -> EmotionalReading:
    """
    Analyze a text string and return an EmotionalReading.
    Main entry point for the text → emotion pipeline.
    """
    text_lower = text.lower()
    tokens = re.findall(r"[a-z']+", text_lower)

    # ── Pass 1: direct emotion keyword matching ──
    keyword_emotions: Dict[str, float] = {}
    keyword_hits = []

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in EMOTION_KEYWORDS:
            em_name = EMOTION_KEYWORDS[token]
            keyword_emotions[em_name] = keyword_emotions.get(em_name, 0) + 1.0
            keyword_hits.append(token)
        i += 1

    # ── Pass 2: lexicon valence/arousal with negation + intensifiers ──
    valence_scores = []
    arousal_scores = []

    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Check for intensifier
        multiplier = INTENSIFIERS.get(token, 1.0)

        # Check window for negation (3 words back)
        negated = any(tokens[max(0,i-j)] in NEGATORS for j in range(1,4))

        if token in AFFECTIVE_LEXICON:
            v, a = AFFECTIVE_LEXICON[token]
            if negated:
                v = -v * 0.7  # negation partially flips valence
            v *= multiplier
            a *= max(0.5, multiplier * 0.8)  # arousal also amplified
            valence_scores.append(v)
            arousal_scores.append(a)
        i += 1

    # Aggregate
    if valence_scores:
        # Weighted mean: words later in text weighted slightly more (recency)
        weights = [0.7 + 0.3 * (i / len(valence_scores)) for i in range(len(valence_scores))]
        total_w = sum(weights)
        valence = sum(v * w for v, w in zip(valence_scores, weights)) / total_w
        arousal = sum(a * w for a, w in zip(arousal_scores, weights)) / total_w
    else:
        valence = 0.0
        arousal = 0.35  # neutral baseline

    # Clamp
    valence = max(-1.0, min(1.0, valence))
    arousal = max(0.05, min(1.0, arousal))

    # ── Resolve dominant emotion ──
    # Merge keyword hits with V/A coordinate
    if keyword_emotions:
        # Keyword emotions take priority — map each to signature
        weighted_em: Dict[str, float] = {}
        for em_name, count in keyword_emotions.items():
            em = get_emotion(em_name)
            if em:
                weighted_em[em.name] = weighted_em.get(em.name, 0) + count

        # Also add V/A nearest emotions at lower weight
        va_emotions = emotions_by_valence_arousal(valence, arousal, top_n=3)
        for i, em in enumerate(va_emotions):
            w = 0.3 / (i + 1)
            weighted_em[em.name] = weighted_em.get(em.name, 0) + w

        total = sum(weighted_em.values())
        ranked = sorted(weighted_em.items(), key=lambda x: x[1], reverse=True)
        emotion_mix = [(EMOTION_MAP[n.lower()], w/total) for n, w in ranked
                       if n.lower() in EMOTION_MAP]
        dominant = emotion_mix[0][0] if emotion_mix else va_emotions[0]
    else:
        va_emotions = emotions_by_valence_arousal(valence, arousal, top_n=5)
        total_dist = len(va_emotions)
        emotion_mix = [(em, (total_dist - i) / sum(range(1, total_dist+1)))
                       for i, em in enumerate(va_emotions)]
        dominant = va_emotions[0]

    return EmotionalReading(
        text=text,
        valence=valence,
        arousal=arousal,
        dominant_emotion=dominant,
        emotion_mix=emotion_mix,
        keyword_hits=keyword_hits,
    )


def analyze_stream(text_chunks: List[str]) -> List[EmotionalReading]:
    """Analyze a stream of text chunks, returning a reading per chunk."""
    return [analyze_text(chunk) for chunk in text_chunks if chunk.strip()]
