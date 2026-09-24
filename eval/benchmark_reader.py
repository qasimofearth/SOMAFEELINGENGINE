"""
Reproduce Table 8 of the paper (§5.1.5): held-out accuracy of the text reader.

    python -m feeling_engine.eval.benchmark_reader            # deployed reader
    python -m feeling_engine.eval.benchmark_reader --lexicon  # lexicon fallback only
    python -m feeling_engine.eval.benchmark_reader --classifier-only  # no keyword evidence

Downloads the GoEmotions test split (Demszky et al., 2020) and the dair-ai
"emotion" test split (Saravia et al., 2018) on first run, and the pinned
classifier (see emotion_classifier.py). Scores single-label examples by
emotion family (GoEmotions' Ekman grouping), macro-averaged, with 95%
bootstrap intervals; valence polarity; and neutral detection.
"""
import collections
import json
import os
import random
import sys
import urllib.request

import feeling_engine.text_emotion as te
from feeling_engine import emotion_classifier as ec

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
GE = "https://raw.githubusercontent.com/google-research/google-research/master/goemotions/data/"
DAIR = ("https://datasets-server.huggingface.co/rows?dataset=dair-ai/emotion"
        "&config=split&split=test&offset={}&length=100")

# Atlas emotion -> emotion family; None for low-affect states (contemplation, …).
ATLAS_FAMILY = {
    **dict.fromkeys([
        "Ecstasy", "Eureka", "Love", "Collective Effervescence", "Joy", "Kama Muta", "Compersion",
        "Gratitude", "Frisson", "Flow", "Admiration", "Ubuntu", "Moral Elevation", "Pride", "Meraki",
        "Optimism", "Trust", "Hope", "Serenity", "Calm", "Waldeinsamkeit", "Acceptance", "Wabi-sabi",
        "Mamihlapinatapai", "Anticipation", "Fernweh", "Schadenfreude", "Excitement", "Relief",
        "Amusement", "Compassion"], "joy"),
    **dict.fromkeys([
        "Surprise", "Amazement", "Awe", "Epistemic Curiosity", "Interest", "Anagnorisis", "Aporia",
        "Cognitive Dissonance"], "surprise"),
    **dict.fromkeys(["Fear", "Terror", "Apprehension", "Torschlusspanik", "Vigilance"], "fear"),
    **dict.fromkeys(["Anger", "Rage", "Annoyance", "Contempt", "Envy"], "anger"),
    **dict.fromkeys(["Disgust", "Loathing"], "disgust"),
    **dict.fromkeys([
        "Sadness", "Grief", "Remorse", "Shame", "Pensiveness", "Weltschmerz", "Saudade", "Hiraeth",
        "Sehnsucht", "Empathic Distress", "Skin Hunger", "Disappointment"], "sadness"),
}


def _fetch(name, url):
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    return path


def goemotions_test():
    labels = open(_fetch("emotions.txt", GE + "emotions.txt")).read().split()
    ekman = json.load(open(_fetch("ekman_mapping.json", GE + "ekman_mapping.json")))
    sent = json.load(open(_fetch("sentiment_mapping.json", GE + "sentiment_mapping.json")))
    fam = {f: e for e, fs in ekman.items() for f in fs}
    pol = {f: p for p, fs in sent.items() for f in fs}
    rows = []
    for line in open(_fetch("test.tsv", GE + "test.tsv"), encoding="utf-8"):
        text, ids, _ = line.rstrip("\n").split("\t")
        ids = [int(x) for x in ids.split(",")]
        if len(ids) == 1:
            lab = labels[ids[0]]
            rows.append((text, fam.get(lab), pol.get(lab)))   # neutral -> (None, None)
    return rows


def dair_test():
    path = os.path.join(DATA, "dair_test.json")
    if not os.path.exists(path):
        rows, names = [], None
        for off in range(0, 2000, 100):
            d = json.load(urllib.request.urlopen(DAIR.format(off)))
            names = d["features"][1]["type"]["names"]
            rows += [(r["row"]["text"], r["row"]["label"]) for r in d["rows"]]
        os.makedirs(DATA, exist_ok=True)
        json.dump({"names": names, "rows": rows}, open(path, "w"))
    d = json.load(open(path))
    fam = {"sadness": "sadness", "joy": "joy", "love": "joy", "anger": "anger", "fear": "fear",
           "surprise": "surprise"}
    pol = {"sadness": "negative", "joy": "positive", "love": "positive", "anger": "negative",
           "fear": "negative", "surprise": None}
    return [(t, fam[d["names"][l]], pol[d["names"][l]]) for t, l in d["rows"]]


def score(rows, seed=0):
    pairs, pol_ok, pol_n, neu_ok, neu_n = [], 0, 0, 0, 0
    for i, (text, family, polarity) in enumerate(rows):
        r = te.analyze_text(text)
        if family is None:                                   # neutral example
            neu_n += 1; neu_ok += r.is_neutral
            continue
        pairs.append((family, ATLAS_FAMILY.get(r.dominant_emotion.name)))
        if polarity in ("positive", "negative"):
            pol_n += 1
            pol_ok += abs(r.valence) >= 0.05 and ((r.valence > 0) == (polarity == "positive"))
        if i % 500 == 0:
            print(f"  {i}/{len(rows)}", file=sys.stderr)

    def macro(ps):
        tot, ok = collections.Counter(), collections.Counter()
        for g, p in ps:
            tot[g] += 1; ok[g] += g == p
        return sum(ok[k] / tot[k] for k in tot) / len(tot), {k: ok[k] / tot[k] for k in tot}

    m, per = macro(pairs)
    rnd = random.Random(seed)
    boots = sorted(macro([pairs[rnd.randrange(len(pairs))] for _ in pairs])[0] for _ in range(1000))
    out = {"family_macro": m, "ci95": (boots[25], boots[974]), "per_family": per,
           "polarity": pol_ok / pol_n if pol_n else None}
    if neu_n:
        out["neutral_kept_neutral"] = neu_ok / neu_n
    return out


def main():
    if "--lexicon" in sys.argv:
        te._classifier = None
    elif not ec.load_blocking():
        sys.exit(f"classifier unavailable: {ec.status()}")
    if "--classifier-only" in sys.argv:
        te._CLF_KEYWORD_WEIGHT = 0.0
    for name, rows in [("GoEmotions test", goemotions_test()), ("dair-ai emotion test", dair_test())]:
        res = score(rows)
        print(f"\n{name}: family macro {res['family_macro']:.1%} "
              f"[{res['ci95'][0]:.1%}, {res['ci95'][1]:.1%}]"
              + (f"  polarity {res['polarity']:.1%}" if res["polarity"] is not None else "")
              + (f"  neutral kept neutral {res['neutral_kept_neutral']:.1%}" if "neutral_kept_neutral" in res else ""))
        print("  per family:", {k: round(v, 3) for k, v in sorted(res["per_family"].items())})


if __name__ == "__main__":
    main()
