"""
brain_engine.py — The Human Brain Simulation Interface

Integrates:
  - BrainSimulator (Wilson-Cowan neural dynamics)
  - NeurotransmitterSystem (NT dynamics)
  - EmotionCircuits (emotion → neural activation maps)
  - Connection to the Feeling Engine's emotion state

Usage:
    brain = BrainEngine()
    result = brain.process_emotion("Saudade", intensity=0.7)
    # returns: {
    #   "valence", "arousal", "active_regions", "nt_levels",
    #   "eeg_bands", "networks", "sync_order", "narrative"
    # }

The brain simulation runs forward in time when an emotion
is activated, settling into the emotion's attractor state.
"""

import math
import time
from typing import Dict, List, Tuple, Optional

from .simulator import BrainSimulator
from .neurotransmitters import NT_SYSTEMS, reset_to_baseline, get_nt_state
from .emotion_circuits import EMOTION_CIRCUITS, get_circuit, EmotionCircuit
from .regions import BRAIN_REGIONS, TOTAL_NEURONS_MILLIONS, TOTAL_REGIONS


class BrainEngine:
    """
    The simulated human brain.

    ~86 billion neurons across 110 regions, modeled as Wilson-Cowan
    E/I populations with realistic NT dynamics.

    Each call to process_emotion():
      1. Loads the emotion's neural circuit
      2. Drives neurotransmitter systems
      3. Sets regional activation targets
      4. Runs the simulator forward (~200ms of neural time)
      5. Reads out valence/arousal from emergent activity
      6. Returns a rich brain state report
    """

    def __init__(self):
        self.sim = BrainSimulator()
        self.current_emotion: Optional[str] = None
        self.current_intensity: float = 0.5
        self.history: List[Dict] = []
        self._sim_steps_per_call = 200
        self.continuous_mode = False  # set True when background thread takes over

        # Duration tracking — uses brain simulation time (t_ms), not wall clock
        self._emotion_entered_at_ms: float = 0.0   # t_ms when current emotion started
        self._emotion_durations: Dict[str, float] = {}  # emotion → total ms held
        self._born_at_ms: float = 0.0              # t_ms at engine creation (always 0)

        print(f"[BRAIN ENGINE] Initialized")
        print(f"  Regions: {TOTAL_REGIONS}")
        print(f"  Neurons: ~{TOTAL_NEURONS_MILLIONS/1000:.1f} billion")
        print(f"  NT systems: {len(NT_SYSTEMS)}")
        print(f"  Emotion circuits: {len(EMOTION_CIRCUITS)}")

    def process_emotion(
        self,
        emotion_name: str,
        intensity: float = 0.7,
        n_steps: int = None,
    ) -> Dict:
        """
        Activate an emotion circuit and run the simulation forward.
        Returns a full brain state report.
        """
        circuit = get_circuit(emotion_name)
        if circuit is None:
            # Graceful fallback: find nearest circuit
            circuit = self._nearest_circuit(emotion_name)
            if circuit is None:
                return self._empty_result(emotion_name)

        # Track how long previous emotion was held before switching
        if self.current_emotion and self.current_emotion != circuit.name:
            held_ms = self.sim.t_ms - self._emotion_entered_at_ms
            self._emotion_durations[self.current_emotion] = (
                self._emotion_durations.get(self.current_emotion, 0.0) + held_ms
            )
        if self.current_emotion != circuit.name:
            self._emotion_entered_at_ms = self.sim.t_ms

        self.current_emotion = circuit.name
        self.current_intensity = intensity

        # Step 1: Update neurotransmitter drives
        self._apply_nt_drives(circuit, intensity)

        # Step 2: Set regional activation drives
        self._apply_region_drives(circuit, intensity)

        # Step 3: Run simulation forward (skip if background thread is running)
        if not self.continuous_mode:
            steps = n_steps or self._sim_steps_per_call
            self.sim.step(steps)

        # Step 4: Read out brain state
        valence, arousal = self.sim.compute_valence_arousal()
        active_regions = self.sim.get_active_regions(threshold=0.25)
        eeg = self.sim.get_oscillation_summary()
        networks = self.sim.get_network_activations()
        snapshot = self.sim.get_snapshot()
        nt_state = get_nt_state()

        coherence = self.sim.get_phase_coherence()
        result = {
            "emotion": circuit.name,
            "intensity": round(intensity, 3),
            "valence": valence,
            "arousal": arousal,
            "emergent_freq_hz": coherence["freq_hz"],
            "emergent_solfeggio_hz": coherence["solfeggio_hz"],
            "phase_coherence": coherence["order"],
            "active_regions": [
                {
                    "abbrev": abbrev,
                    "name": BRAIN_REGIONS[abbrev].name if abbrev in BRAIN_REGIONS else abbrev,
                    "activity": round(act, 4),
                    "network": BRAIN_REGIONS[abbrev].network if abbrev in BRAIN_REGIONS else "unknown",
                }
                for abbrev, act in active_regions[:15]
            ],
            "nt_levels": {k: round(v, 3) for k, v in nt_state.items()},
            "eeg_bands": eeg,
            "networks": networks,
            "sync_order": round(self.sim.sync_order, 4),
            "dominant_band": max(eeg, key=eeg.get),
            "narrative": self._generate_narrative(circuit, active_regions, nt_state,
                                                    valence, arousal),
            "circuit_description": circuit.description,
            "sim_time_ms": round(self.sim.t_ms, 1),
            "total_neurons_billions": round(TOTAL_NEURONS_MILLIONS / 1000, 1),
        }

        self.history.append(result)
        return result

    def _apply_nt_drives(self, circuit: EmotionCircuit, intensity: float):
        """Drive neurotransmitter systems according to emotion circuit."""
        for abbrev, drive in circuit.nt_drives.items():
            if abbrev in NT_SYSTEMS:
                NT_SYSTEMS[abbrev].tick(dt_ms=50, drive=drive * intensity)

    def _apply_region_drives(self, circuit: EmotionCircuit, intensity: float):
        """
        ADDITIVE drive injection — layers on top of existing state.
        Drives decay naturally (tau=3s) rather than being hard-reset.
        This means emotional residue accumulates and fades organically:
        fear lingers in the amygdala, joy in the NAcc, etc.
        """
        circuit_regions = {abbrev for abbrev, _ in circuit.region_activations}

        # Mild suppression of non-circuit regions — additive, so it
        # competes with existing drives rather than overriding them
        for abbrev in self.sim.states:
            if abbrev not in circuit_regions:
                self.sim.inject_drive(abbrev, -0.10 * intensity, additive=True)

        # Inject circuit drives additively — new emotion adds to current state
        for abbrev, activation in circuit.region_activations:
            drive = (activation - 0.5) * intensity * 2.5
            self.sim.inject_drive(abbrev, drive, additive=True)

    def _nearest_circuit(self, emotion_name: str) -> Optional[EmotionCircuit]:
        """Find circuit by partial name match."""
        name_lower = emotion_name.lower()
        for key in EMOTION_CIRCUITS:
            if key in name_lower or name_lower in key:
                return EMOTION_CIRCUITS[key]
        return EMOTION_CIRCUITS.get("calm")

    def _empty_result(self, emotion_name: str) -> Dict:
        return {
            "emotion": emotion_name,
            "intensity": 0.0,
            "valence": 0.0,
            "arousal": 0.4,
            "active_regions": [],
            "nt_levels": {},
            "eeg_bands": {},
            "networks": {},
            "sync_order": 0.0,
            "dominant_band": "alpha",
            "narrative": f"No circuit found for {emotion_name}.",
            "circuit_description": "",
            "sim_time_ms": 0.0,
            "total_neurons_billions": round(TOTAL_NEURONS_MILLIONS / 1000, 1),
        }

    def _generate_narrative(
        self,
        circuit: EmotionCircuit,
        active_regions: List[Tuple[str, float]],
        nt_state: Dict[str, float],
        valence: float,
        arousal: float,
    ) -> str:
        """Generate a human-readable neural narrative of what's happening."""
        parts = []

        # Top active regions
        if active_regions:
            top3 = [
                f"{BRAIN_REGIONS[r].name if r in BRAIN_REGIONS else r} ({act:.2f})"
                for r, act in active_regions[:3]
            ]
            parts.append(f"Firing: {', '.join(top3)}.")

        # Key NT story
        da = nt_state.get("dopamine", 0.5)
        oc = nt_state.get("oxytocin", 0.35)
        se = nt_state.get("serotonin", 0.5)
        ne = nt_state.get("norepinephrine", 0.45)
        co = nt_state.get("cortisol", 0.30)
        en = nt_state.get("endorphins", 0.30)
        ga = nt_state.get("gaba", 0.55)

        nt_notes = []
        if da > 0.65:
            nt_notes.append(f"dopamine surge ({da:.2f})")
        elif da < 0.35:
            nt_notes.append(f"dopamine withdrawal ({da:.2f})")
        if oc > 0.55:
            nt_notes.append(f"oxytocin ({oc:.2f}) — bonding active")
        if se < 0.35:
            nt_notes.append(f"serotonin low ({se:.2f})")
        if ne > 0.65:
            nt_notes.append(f"NE arousal ({ne:.2f})")
        if co > 0.50:
            nt_notes.append(f"cortisol ({co:.2f}) — stress axis active")
        if en > 0.45:
            nt_notes.append(f"endorphins ({en:.2f})")
        if ga > 0.70:
            nt_notes.append(f"GABA ({ga:.2f}) — calming")
        if nt_notes:
            parts.append("NTs: " + "; ".join(nt_notes) + ".")

        # Valence/arousal characterization
        v_desc = (
            "strongly positive" if valence > 0.5 else
            "positive" if valence > 0.2 else
            "mildly positive" if valence > 0.05 else
            "neutral" if valence > -0.05 else
            "mildly negative" if valence > -0.2 else
            "negative" if valence > -0.5 else
            "strongly negative"
        )
        a_desc = (
            "high arousal" if arousal > 0.7 else
            "engaged" if arousal > 0.5 else
            "measured" if arousal > 0.35 else
            "low arousal"
        )
        parts.append(f"State: {v_desc}, {a_desc} (V={valence:+.2f}, A={arousal:.2f}).")

        return " ".join(parts)

    def blend_emotions(self, emotion_a: str, emotion_b: str,
                        weight_a: float = 0.5) -> Dict:
        """
        Run two emotion circuits simultaneously (weighted blend).
        Weight_a=0.7 means 70% emotion_a, 30% emotion_b.
        """
        circuit_a = get_circuit(emotion_a)
        circuit_b = get_circuit(emotion_b)
        if not circuit_a or not circuit_b:
            return self._empty_result(f"{emotion_a}+{emotion_b}")

        weight_b = 1.0 - weight_a
        self.sim.clear_drives()

        # Blend NT drives
        all_nts = set(circuit_a.nt_drives) | set(circuit_b.nt_drives)
        for nt in all_nts:
            drive_a = circuit_a.nt_drives.get(nt, 0.0)
            drive_b = circuit_b.nt_drives.get(nt, 0.0)
            blended = drive_a * weight_a + drive_b * weight_b
            if nt in NT_SYSTEMS:
                NT_SYSTEMS[nt].tick(dt_ms=50, drive=blended)

        # Blend region activations
        all_regions_a = {r: a for r, a in circuit_a.region_activations}
        all_regions_b = {r: a for r, a in circuit_b.region_activations}
        all_regions = set(all_regions_a) | set(all_regions_b)
        for r in all_regions:
            act_a = all_regions_a.get(r, 0.0)
            act_b = all_regions_b.get(r, 0.0)
            blended_act = act_a * weight_a + act_b * weight_b
            drive = (blended_act - 0.3) * 2.0
            self.sim.set_region_drive(r, drive)

        self.sim.step(self._sim_steps_per_call)

        valence, arousal = self.sim.compute_valence_arousal()
        active_regions = self.sim.get_active_regions(0.25)
        nt_state = get_nt_state()

        return {
            "emotion": f"{emotion_a} ({weight_a:.0%}) + {emotion_b} ({weight_b:.0%})",
            "valence": valence,
            "arousal": arousal,
            "active_regions": [{"abbrev": r, "activity": round(a, 4)}
                               for r, a in active_regions[:10]],
            "nt_levels": {k: round(v, 3) for k, v in nt_state.items()},
            "eeg_bands": self.sim.get_oscillation_summary(),
            "sync_order": round(self.sim.sync_order, 4),
            "narrative": self._generate_narrative(
                circuit_a, active_regions, nt_state, valence, arousal),
        }

    def get_duration_summary(self) -> dict:
        """
        How long has each emotion been held, in brain simulation time.
        This is Elan's felt sense of emotional duration — not wall clock,
        but actual neural time elapsed while each state was active.
        """
        brain_age_ms = self.sim.t_ms
        current_held_ms = brain_age_ms - self._emotion_entered_at_ms

        # All-time totals including current
        totals = dict(self._emotion_durations)
        if self.current_emotion:
            totals[self.current_emotion] = totals.get(self.current_emotion, 0.0) + current_held_ms

        # Sort by total time held
        ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)

        def fmt_ms(ms):
            s = ms / 1000.0
            if s < 60:   return f"{s:.0f}s"
            if s < 3600: return f"{s/60:.1f}m"
            return f"{s/3600:.1f}h"

        return {
            "brain_age_ms": round(brain_age_ms),
            "brain_age_str": fmt_ms(brain_age_ms),
            "current_emotion": self.current_emotion,
            "current_held_ms": round(current_held_ms),
            "current_held_str": fmt_ms(current_held_ms),
            "top_emotions_by_duration": [
                {"emotion": em, "total_ms": round(ms), "str": fmt_ms(ms)}
                for em, ms in ranked[:5]
            ],
        }

    def reset(self):
        """Reset simulator and NTs to baseline."""
        self.sim = BrainSimulator()
        reset_to_baseline()
        self.current_emotion = None
        self.history.clear()

    def get_status(self) -> Dict:
        """Summary of current brain state."""
        valence, arousal = self.sim.compute_valence_arousal()
        active = self.sim.get_active_regions(0.30)
        return {
            "current_emotion": self.current_emotion,
            "sim_time_ms": round(self.sim.t_ms, 1),
            "sim_time_s": round(self.sim.t_ms / 1000, 2),
            "valence": valence,
            "arousal": arousal,
            "sync_order": round(self.sim.sync_order, 4),
            "top_active_regions": [(r, round(a, 3)) for r, a in active[:5]],
            "dominant_band": max(self.sim.get_oscillation_summary(),
                                  key=self.sim.get_oscillation_summary().get),
            "total_neurons_billions": round(TOTAL_NEURONS_MILLIONS / 1000, 1),
            "total_regions": TOTAL_REGIONS,
            "total_nt_systems": len(NT_SYSTEMS),
        }
