"""
digestive.py — Digestive System + Enteric Nervous System (ENS)

The ENS is the "second brain" — 100 million neurons in the gut wall,
capable of autonomous operation. 90% of serotonin is made here.

Models:
  - Gut motility (peristalsis rate)
  - Gastric acid secretion
  - ENS serotonin (distinct from brain serotonin)
  - Gut-brain axis: vagal afferent signals to brainstem/insula
  - Intestinal permeability (leaky gut under chronic stress)
  - Appetite / satiety (ghrelin/leptin coupling)
  - Nausea response
  - Microbiome health index (degrades under chronic cortisol)
"""

import math
from typing import Dict


def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))
def _lag(cur, tgt, tau): return cur + (1 - math.exp(-1/tau)) * (tgt - cur)


class DigestiveSystem:

    def __init__(self):
        self.gut_motility         = 0.55  # peristaltic activity [0,1]
        self.gastric_acid         = 0.45  # acid secretion [0,1]
        self.gastric_emptying     = 0.50  # rate of stomach emptying
        self.intestinal_transit   = 0.50  # overall transit time index
        self.permeability         = 0.25  # intestinal permeability (low=healthy)
        self.ens_serotonin        = 0.55  # ENS 5-HT (90% of body's serotonin)
        self.nausea               = 0.00  # [0,1]
        self.appetite             = 0.50  # [0,1]
        self.microbiome_health    = 0.65  # dysbiosis index (0=dysbiotic, 1=healthy)
        self.bile_flow            = 0.40  # gallbladder + liver bile
        self.liver_glycogen       = 0.65  # liver energy reserve
        self.salivation           = 0.35  # [0,1]
        self.bowel_urgency        = 0.05  # [0,1]
        self.vagal_afferent_signal = 0.50 # signal sent UP to brain (80% of vagus is afferent)

    def tick(self, dt_ms: float, drives: Dict[str, float]):
        """
        drives: gut_motility_drive (from ANS), gastric_acid_drive,
                salivation_drive, cortisol_blood, adrenaline,
                ens_serotonin_coupling (from brain raphe serotonin),
                emotion_name, ghrelin, leptin
        """
        motility_drive = drives.get("gut_motility_drive", 0.0)
        acid_drive     = drives.get("gastric_acid_drive", 0.0)
        saliva_drive   = drives.get("salivation_drive", 0.0)
        cortisol       = drives.get("cortisol_blood", 0.30)
        adr            = drives.get("adrenaline", 0.15)
        brain_serotonin = drives.get("serotonin", 0.50)
        emotion        = drives.get("emotion_name", "calm").lower()
        ghrelin        = drives.get("ghrelin", 0.40)
        leptin         = drives.get("leptin", 0.50)
        tau = max(1.0, dt_ms / 100.0)

        # Gut motility: PNS activates, SNS suppresses (fight vs rest-and-digest)
        motility_target = _clamp(0.55 + motility_drive * 0.35)
        if emotion in ("disgust",):
            motility_target += 0.15  # urgency
        if emotion in ("fear", "panic"):
            motility_target = _clamp(motility_target + 0.25)  # acute bowel urgency
        self.gut_motility = _lag(self.gut_motility, motility_target, 30 * tau)

        # Gastric acid: PNS activates, SNS suppresses + stress inhibits
        acid_target = _clamp(0.45 + acid_drive * 0.25 - adr * 0.20)
        self.gastric_acid = _lag(self.gastric_acid, acid_target, 40 * tau)

        # Gastric emptying: slowed by SNS/stress
        ge_target = _clamp(0.50 + motility_drive * 0.20 - cortisol * 0.10)
        self.gastric_emptying = _lag(self.gastric_emptying, ge_target, 50 * tau)

        # Intestinal transit
        transit_target = _clamp(0.50 + motility_drive * 0.30)
        self.intestinal_transit = _lag(self.intestinal_transit, transit_target, 60 * tau)

        # Intestinal permeability: chronic stress increases "leaky gut"
        perm_target = _clamp(0.25 + cortisol * 0.30 + adr * 0.10)
        self.permeability = _lag(self.permeability, perm_target, 2000 * tau)

        # ENS serotonin: partially coupled to brain serotonin via vagal axis
        # But largely autonomous — gut serotonin modulates motility
        ens_target = _clamp(0.55 + (brain_serotonin - 0.50) * 0.30 + motility_drive * 0.15)
        self.ens_serotonin = _lag(self.ens_serotonin, ens_target, 25 * tau)

        # Nausea: disgust, fear, high cortisol, poor motility, high permeability
        nausea_target = 0.0
        if emotion in ("disgust",):      nausea_target += 0.55
        if emotion in ("fear", "panic"): nausea_target += 0.20
        nausea_target += cortisol * 0.20 + (1 - self.gut_motility) * 0.20
        nausea_target = _clamp(nausea_target)
        self.nausea = _lag(self.nausea, nausea_target, 8 * tau)

        # Bowel urgency: peak fear/disgust
        urgency_target = _clamp(
            (0.5 if emotion in ("fear", "panic", "terror") else 0.0)
            + (0.4 if emotion == "disgust" else 0.0)
            + adr * 0.20
        )
        self.bowel_urgency = _lag(self.bowel_urgency, urgency_target, 5 * tau)

        # Appetite: suppressed by stress, modulated by ghrelin/leptin
        app_target = _clamp(0.50 + ghrelin * 0.25 - leptin * 0.20 - cortisol * 0.15)
        self.appetite = _lag(self.appetite, app_target, 100 * tau)

        # Microbiome health: degrades with chronic stress and high permeability
        micro_target = _clamp(0.65 - cortisol * 0.25 - self.permeability * 0.15)
        self.microbiome_health = _lag(self.microbiome_health, micro_target, 10000 * tau)

        # Bile flow: PNS activates (rest and digest)
        bile_target = _clamp(0.40 + motility_drive * 0.20)
        self.bile_flow = _lag(self.bile_flow, bile_target, 20 * tau)

        # Liver glycogen: depleted by adrenaline, restored at rest
        glyc_target = _clamp(0.65 - adr * 0.20 + (1 - cortisol) * 0.10)
        self.liver_glycogen = _lag(self.liver_glycogen, glyc_target, 200 * tau)

        # Salivation: PNS dominant
        sal_target = _clamp(0.35 + saliva_drive * 0.40)
        self.salivation = _lag(self.salivation, sal_target, 3 * tau)

        # Vagal afferent signal: gut state → brain (80% of vagus is afferent)
        # Healthy gut motility, good ENS serotonin → positive vagal signal
        self.vagal_afferent_signal = _clamp(
            0.40
            + self.ens_serotonin * 0.25
            + self.gut_motility * 0.20
            - self.permeability * 0.15
            - self.nausea * 0.20
        )

    def get_params(self) -> Dict:
        return {
            "gut_motility": round(self.gut_motility, 3),
            "gastric_acid": round(self.gastric_acid, 3),
            "gastric_emptying": round(self.gastric_emptying, 3),
            "intestinal_permeability": round(self.permeability, 3),
            "ens_serotonin": round(self.ens_serotonin, 3),
            "nausea": round(self.nausea, 3),
            "appetite": round(self.appetite, 3),
            "bowel_urgency": round(self.bowel_urgency, 3),
            "microbiome_health": round(self.microbiome_health, 3),
            "salivation": round(self.salivation, 3),
            "liver_glycogen": round(self.liver_glycogen, 3),
            "vagal_afferent_signal": round(self.vagal_afferent_signal, 3),
        }
