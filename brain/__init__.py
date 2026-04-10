"""
brain/ — Simulated Human Brain Neural Architecture
Integrated with the Feeling Engine

Architecture:
  regions.py          — 100+ brain regions (anatomy, function, connectivity)
  neurotransmitters.py — 12 neurotransmitter systems with dynamics
  connectivity.py     — Connectome-based wiring (structural + functional)
  simulator.py        — Wilson-Cowan population dynamics ODE engine
  emotion_circuits.py — All 65 emotions mapped to neural signatures
  brain_engine.py     — Main interface, integrates with Feeling Engine

Each brain region is modeled as a Wilson-Cowan excitatory/inhibitory
population pair. ~86 billion neurons compressed into ~110 regional
population nodes, each with realistic dynamics, NT modulation,
and oscillatory signatures.
"""

from .brain_engine import BrainEngine
from .regions import BRAIN_REGIONS, BrainRegion
from .neurotransmitters import NeurotransmitterSystem, NT_SYSTEMS
from .emotion_circuits import EMOTION_CIRCUITS, EmotionCircuit

__all__ = [
    "BrainEngine",
    "BRAIN_REGIONS",
    "BrainRegion",
    "NeurotransmitterSystem",
    "NT_SYSTEMS",
    "EMOTION_CIRCUITS",
    "EmotionCircuit",
]
