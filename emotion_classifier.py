"""
emotion_classifier.py — Contextual emotion classifier for the text reader.

Which emotion a passage expresses cannot be recovered from word-level
valence/arousal scores: "I'm disappointed in you" and "I'm scared of you" land
in almost the same place. This module adds a trained classifier for the
categorical question, while text_emotion's lexicon keeps doing what it does well
(polarity, intensity, negation, transparency) and remains the fallback.

Model: RoBERTa-base fine-tuned on GoEmotions (Demszky et al., 2020) — 27
emotions + neutral, multi-label — by SamLowe, MIT licence, int8 ONNX export
(SamLowe/roberta-base-go_emotions-onnx). Runs on CPU via onnxruntime.

The model is fetched once (pinned revision, SHA-256 verified) into a cache
directory — the Railway volume when present — and loaded in a background
thread so server start-up is never blocked. Until it is ready, classify()
returns None and callers fall back to the lexicon, and say so.
"""

from __future__ import annotations

import hashlib
import os
import threading
import urllib.request
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

MODEL_REPO = "SamLowe/roberta-base-go_emotions-onnx"
MODEL_REVISION = "90ee0c1c4796d370e68968687b8ba51fc11224f4"
MODEL_FILES = {
    "onnx/model_quantized.onnx": "0c1981c5b479674747911c8e2228f0c4ec90bf47bf66e830f7d4fc62be082958",
    "onnx/tokenizer.json": "63735ef382776e869c0ee50f8e999ab19111bb794f8a451559e611077dfe7f25",
}

LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion",
    "curiosity", "desire", "disappointment", "disapproval", "disgust", "embarrassment",
    "excitement", "fear", "gratitude", "grief", "joy", "love", "nervousness", "optimism",
    "pride", "realization", "relief", "remorse", "sadness", "surprise", "neutral",
]

# GoEmotions label → atlas emotion(s). Weights per label sum to 1.
LABEL_TO_ATLAS: Dict[str, Dict[str, float]] = {
    "admiration": {"Admiration": 1.0},
    "amusement": {"Amusement": 1.0},
    "anger": {"Anger": 1.0},
    "annoyance": {"Annoyance": 1.0},
    "approval": {"Acceptance": 1.0},
    "caring": {"Compassion": 1.0},
    "confusion": {"Aporia": 1.0},
    "curiosity": {"Interest": 1.0},
    "desire": {"Anticipation": 1.0},
    "disappointment": {"Disappointment": 1.0},
    "disapproval": {"Annoyance": 0.6, "Contempt": 0.4},
    "disgust": {"Disgust": 1.0},
    "embarrassment": {"Shame": 1.0},
    "excitement": {"Excitement": 1.0},
    "fear": {"Fear": 1.0},
    "gratitude": {"Gratitude": 1.0},
    "grief": {"Grief": 1.0},
    "joy": {"Joy": 1.0},
    "love": {"Love": 1.0},
    "nervousness": {"Apprehension": 1.0},
    "optimism": {"Optimism": 1.0},
    "pride": {"Pride": 1.0},
    "realization": {"Surprise": 0.5, "Interest": 0.5},
    "relief": {"Relief": 1.0},
    "remorse": {"Remorse": 1.0},
    "sadness": {"Sadness": 1.0},
    "surprise": {"Surprise": 1.0},
}

MAX_TOKENS = 128          # model trained on short Reddit comments
_WINDOW_WORDS = 60        # long texts are classified in word windows and averaged

_lock = threading.Lock()
_session = None
_tokenizer = None
_status = "not_started"   # not_started | loading | ready | unavailable
_error: Optional[str] = None
_cache: "OrderedDict[str, List[float]]" = OrderedDict()
_cache_lock = threading.Lock()
_CACHE_MAX = 512
_MAX_WINDOWS = 4          # a very long text is read from its last ~240 words


def model_dir() -> str:
    explicit = os.environ.get("FEELING_EMOTION_MODEL_DIR")
    if explicit:
        return explicit
    base = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "models")
    return os.path.join(base, "goemotions-onnx-" + MODEL_REVISION[:8])


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _ensure_files() -> str:
    root = model_dir()
    for rel, digest in MODEL_FILES.items():
        dest = os.path.join(root, rel)
        if os.path.exists(dest) and _sha256(dest) == digest:
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        url = f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{rel}"
        tmp = f"{dest}.{os.getpid()}.{threading.get_ident()}.part"
        with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
            for block in iter(lambda: resp.read(1 << 20), b""):
                out.write(block)
        got = _sha256(tmp)
        if got != digest:
            os.remove(tmp)
            raise RuntimeError(f"checksum mismatch for {rel}: {got}")
        os.replace(tmp, dest)
    return root


_LOAD_ATTEMPTS = 5


def _load():
    """Fetch + load, retrying transient failures (network) with backoff."""
    import time
    global _status
    for attempt in range(1, _LOAD_ATTEMPTS + 1):
        if _load_once():
            return
        if isinstance(_last_exc, ImportError) or attempt == _LOAD_ATTEMPTS:
            break
        time.sleep(min(600, 30 * 2 ** (attempt - 1)))
    with _lock:
        _status = "unavailable"
    print(f"[emotion_classifier] unavailable — lexicon fallback ({_error})", flush=True)


_last_exc: Optional[BaseException] = None


def _load_once() -> bool:
    global _session, _tokenizer, _status, _error, _last_exc
    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer
        root = _ensure_files()
        tok = Tokenizer.from_file(os.path.join(root, "onnx/tokenizer.json"))
        tok.enable_truncation(max_length=MAX_TOKENS)
        so = ort.SessionOptions()
        so.intra_op_num_threads = int(os.environ.get("FEELING_EMOTION_THREADS", "2"))
        so.inter_op_num_threads = 1
        sess = ort.InferenceSession(os.path.join(root, "onnx/model_quantized.onnx"), so,
                                    providers=["CPUExecutionProvider"])
        with _lock:
            _tokenizer, _session, _status, _error = tok, sess, "ready", None
        print(f"[emotion_classifier] ready ({root})", flush=True)
        return True
    except Exception as e:  # never take the server down over the classifier
        with _lock:
            _error, _last_exc = f"{type(e).__name__}: {e}", e
        print(f"[emotion_classifier] load failed ({_error})", flush=True)
        return False


def start_background_load() -> None:
    """Begin fetching/loading the model without blocking the caller."""
    global _status
    with _lock:
        if _status != "not_started":
            return
        _status = "loading"
    threading.Thread(target=_load, name="emotion-classifier-load", daemon=True).start()


def load_blocking() -> bool:
    """Load synchronously (tests, offline tools). Returns True when ready."""
    import time
    global _status
    with _lock:
        if _status == "ready":
            return True
        already = _status == "loading"
        if not already:
            _status = "loading"
    if already:                      # a background load is in flight: wait for it
        while _status == "loading":
            time.sleep(0.2)
        return _status == "ready"
    _load()
    return _status == "ready"


def status() -> Dict[str, Optional[str]]:
    return {"status": _status, "error": _error, "model": f"{MODEL_REPO}@{MODEL_REVISION[:8]}"}


def is_ready() -> bool:
    return _status == "ready"


def _run(text: str) -> List[float]:
    import numpy as np
    enc = _tokenizer.encode(text)
    ids = np.array([enc.ids], dtype=np.int64)
    mask = np.array([enc.attention_mask], dtype=np.int64)
    logits = _session.run(None, {"input_ids": ids, "attention_mask": mask})[0][0]
    return [float(1.0 / (1.0 + np.exp(-x))) for x in logits]   # multi-label sigmoid


def classify(text: str) -> Optional[Dict[str, float]]:
    """Per-label probabilities (multi-label sigmoid) for text, or None if unavailable.

    Texts longer than one window are split into ~60-word windows and averaged,
    so a long reply is read whole rather than truncated.
    """
    if _status != "ready" or not text or not text.strip():
        return None
    key = text.strip()
    with _cache_lock:
        hit = _cache.pop(key, None)
        if hit is not None:
            _cache[key] = hit          # re-insert as most recent
    if hit is None:
        try:
            words = key.split()
            if len(words) <= _WINDOW_WORDS:
                probs = _run(key)
            else:
                windows = [" ".join(words[i:i + _WINDOW_WORDS])
                           for i in range(0, len(words), _WINDOW_WORDS)]
                windows = windows[-_MAX_WINDOWS:]   # bounded cost: the most recent part
                runs = [_run(w) for w in windows]
                probs = [sum(col) / len(runs) for col in zip(*runs)]
        except Exception as e:
            print(f"[emotion_classifier] inference error: {e}", flush=True)
            return None
        with _cache_lock:
            _cache[key] = probs
            while len(_cache) > _CACHE_MAX:
                _cache.popitem(last=False)
        hit = probs
    return dict(zip(LABELS, hit))


def to_atlas(probs: Dict[str, float]) -> Tuple[Dict[str, float], float]:
    """Map label probabilities to (atlas emotion distribution, affect evidence).

    The distribution sums to 1 over atlas emotions. Evidence in [0, 1] is the
    share of probability mass on emotions rather than on 'neutral' — how much
    this text is expressing a feeling at all.
    """
    dist: Dict[str, float] = {}
    total = 0.0
    for label, p in probs.items():
        if label == "neutral":
            continue
        for name, w in LABEL_TO_ATLAS[label].items():
            dist[name] = dist.get(name, 0.0) + p * w
        total += p
    neutral = probs.get("neutral", 0.0)
    if total <= 0:
        return {}, 0.0
    dist = {k: v / total for k, v in dist.items()}
    evidence = total / (total + neutral)
    return dist, evidence
