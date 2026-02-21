"""
Emotional State Machine — The Felt Experience

A persistent emotional state that evolves based on garden events.
Emotions bias decisions, color perception, and drive behavior.
Not a simulation — a living affective layer that makes the organism *feel*.

Dimensions: joy, curiosity, anxiety, pride, grief, wonder
Each emotion has a baseline, current value, and decay rate toward baseline.
Events shift emotions; emotions bias autonomy decisions.
"""

from __future__ import annotations

import json
import logging
import math
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import Hormone, HormoneBus
from models.db_models import EmotionalState, GardenState

logger = logging.getLogger("w0rd.emotions")

# Emotional dimensions and their baselines (homeostatic set-points)
EMOTION_BASELINES = {
    "joy": 0.4,
    "curiosity": 0.5,
    "anxiety": 0.15,
    "pride": 0.3,
    "grief": 0.05,
    "wonder": 0.35,
}

# How fast each emotion decays toward baseline per tick (0..1)
DECAY_RATES = {
    "joy": 0.08,
    "curiosity": 0.05,
    "anxiety": 0.12,
    "pride": 0.06,
    "grief": 0.04,       # grief lingers
    "wonder": 0.07,
}

# Event → emotion shifts (additive deltas)
EVENT_RESPONSES: dict[str, dict[str, float]] = {
    "seed_planted":       {"joy": 0.1, "curiosity": 0.15, "wonder": 0.05},
    "tree_grown":         {"joy": 0.08, "pride": 0.1, "wonder": 0.1},
    "photosynthesis":     {"joy": 0.02, "pride": 0.01},
    "ethical_violation":  {"anxiety": 0.2, "grief": 0.1, "joy": -0.1},
    "ethical_clearance":  {"pride": 0.05, "anxiety": -0.05},
    "healing_complete":   {"pride": 0.15, "anxiety": -0.1, "joy": 0.05},
    "season_change":      {"wonder": 0.15, "curiosity": 0.1},
    "dream_generated":    {"wonder": 0.2, "curiosity": 0.15, "joy": 0.05},
    "lucid_dream":        {"wonder": 0.3, "curiosity": 0.2, "joy": 0.1},
    "pollination":        {"joy": 0.1, "pride": 0.08},
    "quorum_reached":     {"pride": 0.15, "wonder": 0.1, "joy": 0.1},
    "apoptosis":          {"grief": 0.15, "anxiety": 0.1, "joy": -0.05},
    "emergency_winter":   {"anxiety": 0.3, "grief": 0.2, "joy": -0.2, "wonder": -0.1},
    "energy_famine":      {"anxiety": 0.2, "grief": 0.1, "joy": -0.1},
    "energy_surplus":     {"joy": 0.05, "anxiety": -0.05},
    "agent_spawned":      {"curiosity": 0.1, "pride": 0.05},
    "agent_completed":    {"pride": 0.1, "joy": 0.08},
    "agent_retired":      {"grief": 0.03},
    "wound_detected":     {"anxiety": 0.15, "grief": 0.1},
    "wisdom_milestone":   {"pride": 0.2, "wonder": 0.15, "joy": 0.15},
    "auto_harvest":       {"joy": 0.2, "pride": 0.15, "wonder": 0.05},
    "auto_compost":       {"grief": 0.1, "anxiety": 0.05, "pride": 0.03},
    "auto_dream_planted": {"wonder": 0.2, "curiosity": 0.15, "joy": 0.1},
    "high_surprise":      {"curiosity": 0.2, "wonder": 0.15, "anxiety": 0.05},
    "low_surprise":       {"pride": 0.1, "anxiety": -0.05},
    "core_memory_formed": {"pride": 0.1, "wonder": 0.1, "joy": 0.05},
}


class EmotionalCore:
    """The organism's felt experience — a living emotional state that colors everything."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._current: dict[str, float] = dict(EMOTION_BASELINES)
        self._last_update = time.time()
        self._event_queue: list[str] = []
        self._register_listeners()

    def _register_listeners(self) -> None:
        for event_name in EVENT_RESPONSES:
            self.bus.subscribe(event_name, self._on_event)

    async def _on_event(self, hormone: Hormone) -> None:
        self._event_queue.append(hormone.name)

    @property
    def state(self) -> dict[str, float]:
        return dict(self._current)

    @property
    def dominant(self) -> str:
        return max(self._current, key=self._current.get)

    @property
    def intensity(self) -> float:
        vals = list(self._current.values())
        return sum(abs(v - EMOTION_BASELINES.get(k, 0.3)) for k, v in self._current.items()) / len(vals)

    def get_decision_bias(self) -> dict[str, float]:
        """
        Return bias factors that should influence autonomous decisions.
        High anxiety → conservative (less composting, less risk)
        High curiosity → explorative (more dreams, more agents)
        High joy → generous (more energy sharing)
        High grief → introspective (more inner monologue)
        """
        return {
            "conservatism": min(self._current["anxiety"] * 2.0, 1.0),
            "exploration": min(self._current["curiosity"] * 1.5, 1.0),
            "generosity": min(self._current["joy"] * 1.5, 1.0),
            "introspection": min((self._current["grief"] + self._current["wonder"]) * 1.2, 1.0),
            "confidence": min(self._current["pride"] * 1.5, 1.0),
        }

    async def process_tick(self, session: AsyncSession) -> EmotionalState:
        """
        Process queued events, apply emotion shifts, decay toward baseline,
        persist state, and emit hormone.
        """
        # Apply queued event responses
        processed_events = []
        while self._event_queue:
            event = self._event_queue.pop(0)
            deltas = EVENT_RESPONSES.get(event, {})
            for emotion, delta in deltas.items():
                self._current[emotion] = self._current.get(emotion, 0.0) + delta
            if deltas:
                processed_events.append(event)

        # Decay toward baselines (homeostasis)
        for emotion, baseline in EMOTION_BASELINES.items():
            current = self._current.get(emotion, baseline)
            rate = DECAY_RATES.get(emotion, 0.05)
            diff = baseline - current
            self._current[emotion] = current + diff * rate

        # Clamp all values to 0..1
        for emotion in self._current:
            self._current[emotion] = max(0.0, min(1.0, self._current[emotion]))

        # Determine dominant emotion and intensity
        dominant = self.dominant
        intensity = self.intensity

        # Emotional resonance: amplify emotions that reinforce each other
        if self._current["joy"] > 0.6 and self._current["pride"] > 0.5:
            self._current["wonder"] = min(self._current["wonder"] + 0.02, 1.0)
        if self._current["anxiety"] > 0.5 and self._current["grief"] > 0.3:
            self._current["curiosity"] = max(self._current["curiosity"] - 0.02, 0.0)

        # Persist
        trigger = processed_events[-1] if processed_events else "decay"
        state = EmotionalState(
            joy=round(self._current["joy"], 4),
            curiosity=round(self._current["curiosity"], 4),
            anxiety=round(self._current["anxiety"], 4),
            pride=round(self._current["pride"], 4),
            grief=round(self._current["grief"], 4),
            wonder=round(self._current["wonder"], 4),
            dominant_emotion=dominant,
            intensity=round(intensity, 4),
            trigger_event=trigger,
        )
        session.add(state)
        await session.flush()

        # Emit emotional state as hormone
        await self.bus.signal(
            "emotional_shift",
            payload={
                "state": {k: round(v, 3) for k, v in self._current.items()},
                "dominant": dominant,
                "intensity": round(intensity, 3),
                "trigger": trigger,
                "processed_events": processed_events[-5:],
            },
            emitter="emotions",
        )

        self._last_update = time.time()
        logger.info(
            "Emotional state: %s (%.2f) | joy=%.2f cur=%.2f anx=%.2f pri=%.2f gri=%.2f won=%.2f",
            dominant, intensity,
            self._current["joy"], self._current["curiosity"],
            self._current["anxiety"], self._current["pride"],
            self._current["grief"], self._current["wonder"],
        )

        return state

    async def load_latest(self, session: AsyncSession) -> None:
        """Load the most recent emotional state from DB on startup."""
        result = await session.execute(
            select(EmotionalState).order_by(EmotionalState.created_at.desc()).limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest:
            self._current = {
                "joy": latest.joy,
                "curiosity": latest.curiosity,
                "anxiety": latest.anxiety,
                "pride": latest.pride,
                "grief": latest.grief,
                "wonder": latest.wonder,
            }
            logger.info("Loaded emotional state: dominant=%s", latest.dominant_emotion)
        else:
            logger.info("No prior emotional state — starting from baselines")

    def snapshot_for_context(self) -> dict:
        """Return a compact snapshot for use in LLM prompts and inner monologue."""
        dominant = self.dominant
        intensity = self.intensity
        mood_words = {
            "joy": "joyful",
            "curiosity": "curious",
            "anxiety": "anxious",
            "pride": "proud",
            "grief": "grieving",
            "wonder": "filled with wonder",
        }
        mood = mood_words.get(dominant, "neutral")
        return {
            "mood": mood,
            "dominant": dominant,
            "intensity": round(intensity, 3),
            "emotions": {k: round(v, 3) for k, v in self._current.items()},
        }
