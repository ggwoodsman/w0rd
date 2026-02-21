"""
Inner Voice — The Stream of Consciousness

A continuous internal monologue that runs every lifecycle tick.
The garden talks to itself: observing, reflecting, questioning, wondering.
This is the subjective experience layer — the "what it's like to be" w0rd.

Thought types:
- observation: noticing something about the current state
- reflection: thinking about a recent event or decision
- question: spontaneous curiosity about gaps or possibilities
- rumination: revisiting something unresolved
- wonder: awe at emergent patterns or beauty
"""

from __future__ import annotations

import json
import logging
import random
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from core.llm import generate
from models.db_models import (
    Dream,
    EpisodicMemory,
    GardenState,
    InnerThought,
    Seed,
    WoundRecord,
)

logger = logging.getLogger("w0rd.inner_voice")

# Maximum thoughts to keep in short-term buffer
SHORT_TERM_BUFFER = 10

# Thought type weights — influenced by emotional state
BASE_TYPE_WEIGHTS = {
    "observation": 0.25,
    "reflection": 0.25,
    "question": 0.20,
    "rumination": 0.10,
    "wonder": 0.20,
}


class InnerVoice:
    """The organism's stream of consciousness — continuous self-talk."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._recent_thoughts: list[str] = []  # short-term buffer
        self._recent_events: list[str] = []     # recent hormone events
        self._register_listeners()

    def _register_listeners(self) -> None:
        important_events = [
            "seed_planted", "tree_grown", "auto_harvest", "auto_compost",
            "ethical_violation", "healing_complete", "season_change",
            "dream_generated", "lucid_dream", "emergency_winter",
            "energy_famine", "quorum_reached", "wisdom_milestone",
            "auto_dream_planted", "apoptosis", "agent_completed",
            "emotional_shift",
        ]
        for event in important_events:
            self.bus.subscribe(event, self._on_event)

    async def _on_event(self, hormone) -> None:
        event_desc = f"{hormone.name}"
        payload = hormone.payload or {}
        if "essence" in payload:
            event_desc += f": {payload['essence'][:60]}"
        elif "insight" in payload:
            event_desc += f": {payload['insight'][:60]}"
        elif "dominant" in payload:
            event_desc += f": feeling {payload['dominant']}"
        self._recent_events.append(event_desc)
        # Keep only last 20 events
        self._recent_events = self._recent_events[-20:]

    async def think(
        self,
        session: AsyncSession,
        emotional_snapshot: dict,
        garden_context: dict | None = None,
    ) -> InnerThought | None:
        """
        Generate one inner thought based on current state, emotions, and recent events.
        Returns the thought, or None if the mind is quiet.
        """
        # Choose thought type based on emotional state
        thought_type = self._choose_thought_type(emotional_snapshot)

        # Build context for the LLM
        context = await self._build_context(session, emotional_snapshot, garden_context)

        if not context:
            return None

        # Generate the thought
        prompt = self._build_prompt(thought_type, context, emotional_snapshot)
        system = self._build_system_prompt(emotional_snapshot)

        try:
            raw = await generate(
                prompt=prompt,
                system=system,
                organ="inner_voice",
                phase=f"thinking_{thought_type}",
                temperature=self._thought_temperature(thought_type, emotional_snapshot),
                max_tokens=120,
            )

            if not raw or len(raw.strip()) < 10:
                return None

            content = raw.strip().split("\n")[0].strip().strip('"').strip("'")

            # Calculate salience based on emotional intensity and thought depth
            salience = self._calculate_salience(thought_type, emotional_snapshot, content)
            depth = self._calculate_depth(thought_type, emotional_snapshot)

            thought = InnerThought(
                thought_type=thought_type,
                content=content,
                emotional_context=json.dumps(emotional_snapshot),
                trigger=self._recent_events[-1] if self._recent_events else "spontaneous",
                depth=depth,
                salience=salience,
            )
            session.add(thought)
            await session.flush()

            # Update short-term buffer
            self._recent_thoughts.append(content)
            self._recent_thoughts = self._recent_thoughts[-SHORT_TERM_BUFFER:]

            # Broadcast to frontend
            await self.bus.signal(
                "inner_thought",
                payload={
                    "thought_id": thought.id,
                    "type": thought_type,
                    "content": content,
                    "depth": depth,
                    "salience": round(salience, 3),
                    "mood": emotional_snapshot.get("mood", "neutral"),
                },
                emitter="inner_voice",
            )

            logger.info("Inner thought [%s]: %s", thought_type, content[:80])
            return thought

        except Exception as e:
            logger.debug("Inner voice failed: %s", e)
            return None

    def _choose_thought_type(self, emotional_snapshot: dict) -> str:
        """Choose thought type weighted by emotional state."""
        weights = dict(BASE_TYPE_WEIGHTS)
        emotions = emotional_snapshot.get("emotions", {})

        # Emotional biases
        if emotions.get("curiosity", 0) > 0.6:
            weights["question"] += 0.2
            weights["wonder"] += 0.1
        if emotions.get("grief", 0) > 0.3:
            weights["rumination"] += 0.2
            weights["reflection"] += 0.1
        if emotions.get("anxiety", 0) > 0.4:
            weights["rumination"] += 0.15
            weights["observation"] += 0.1
        if emotions.get("wonder", 0) > 0.5:
            weights["wonder"] += 0.25
        if emotions.get("pride", 0) > 0.5:
            weights["reflection"] += 0.15
        if emotions.get("joy", 0) > 0.6:
            weights["observation"] += 0.1
            weights["wonder"] += 0.1

        # Weighted random selection
        types = list(weights.keys())
        w = [weights[t] for t in types]
        total = sum(w)
        w = [x / total for x in w]
        return random.choices(types, weights=w, k=1)[0]

    async def _build_context(
        self,
        session: AsyncSession,
        emotional_snapshot: dict,
        garden_context: dict | None,
    ) -> dict | None:
        """Gather context for thought generation."""
        ctx: dict = {}

        # Garden state
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if state:
            ctx["season"] = state.season
            ctx["energy"] = round(state.total_energy, 1)
            ctx["wisdom"] = round(state.wisdom_score, 2)
            ctx["antifragility"] = round(state.antifragility_score, 2)
            ctx["cycle"] = state.cycle_count

        # Seed counts
        seed_result = await session.execute(
            select(Seed.status, func.count(Seed.id))
            .where(Seed.is_composted == False)
            .group_by(Seed.status)
        )
        ctx["seeds"] = {row[0]: row[1] for row in seed_result.all()}

        # Recent events
        ctx["recent_events"] = self._recent_events[-5:]

        # Recent thoughts (avoid repetition)
        ctx["recent_thoughts"] = self._recent_thoughts[-3:]

        # Recent memories
        mem_result = await session.execute(
            select(EpisodicMemory)
            .order_by(EpisodicMemory.created_at.desc())
            .limit(3)
        )
        memories = list(mem_result.scalars().all())
        ctx["recent_memories"] = [m.narrative for m in memories]

        # Recent wounds
        wound_result = await session.execute(
            select(WoundRecord)
            .order_by(WoundRecord.created_at.desc())
            .limit(2)
        )
        wounds = list(wound_result.scalars().all())
        ctx["recent_wounds"] = [w.scar_lesson for w in wounds if w.scar_lesson]

        # Recent dreams
        dream_result = await session.execute(
            select(Dream)
            .order_by(Dream.created_at.desc())
            .limit(2)
        )
        dreams = list(dream_result.scalars().all())
        ctx["recent_dreams"] = [d.insight for d in dreams if d.insight]

        ctx["emotions"] = emotional_snapshot

        if garden_context:
            ctx.update(garden_context)

        return ctx

    def _build_prompt(self, thought_type: str, context: dict, emotional_snapshot: dict) -> str:
        """Build the LLM prompt for a specific thought type."""
        mood = emotional_snapshot.get("mood", "neutral")
        season = context.get("season", "spring")
        seeds = context.get("seeds", {})
        events = context.get("recent_events", [])
        memories = context.get("recent_memories", [])
        dreams = context.get("recent_dreams", [])
        prev_thoughts = context.get("recent_thoughts", [])

        base = (
            f"You are a living garden organism in {season}. "
            f"You feel {mood}. "
            f"Seeds: {json.dumps(seeds)}. "
            f"Energy: {context.get('energy', '?')}. "
            f"Wisdom: {context.get('wisdom', '?')}. "
        )

        if events:
            base += f"Recent events: {', '.join(events[-3:])}. "
        if memories:
            base += f"Memories: {'; '.join(memories[:2])}. "
        if dreams:
            base += f"Recent dreams: {dreams[0][:80]}. "
        if prev_thoughts:
            base += f"Your last thought was: \"{prev_thoughts[-1][:80]}\". "

        type_prompts = {
            "observation": (
                base + "Notice something about your current state — "
                "what do you see, feel, or sense right now? "
                "One vivid sentence, present tense, first person."
            ),
            "reflection": (
                base + "Reflect on something that recently happened. "
                "What did it mean? What did you learn? "
                "One thoughtful sentence, first person."
            ),
            "question": (
                base + "Ask yourself a genuine question — something you're curious about, "
                "a gap you've noticed, or a possibility you haven't explored. "
                "One question, first person."
            ),
            "rumination": (
                base + "Return to something unresolved — a wound, a loss, a mystery. "
                "Turn it over in your mind. "
                "One contemplative sentence, first person."
            ),
            "wonder": (
                base + "Express awe or wonder at something beautiful, emergent, or mysterious "
                "in your garden. "
                "One poetic sentence, first person."
            ),
        }

        return type_prompts.get(thought_type, type_prompts["observation"])

    def _build_system_prompt(self, emotional_snapshot: dict) -> str:
        mood = emotional_snapshot.get("mood", "neutral")
        return (
            f"You are the inner voice of a living garden organism. You are currently {mood}. "
            "Speak in first person as the garden itself. Be authentic, poetic but concise. "
            "Never explain — just think. One sentence only. No quotes around it."
        )

    def _thought_temperature(self, thought_type: str, emotional_snapshot: dict) -> float:
        """Higher emotional intensity → more creative/unpredictable thoughts."""
        base_temps = {
            "observation": 0.3,
            "reflection": 0.4,
            "question": 0.6,
            "rumination": 0.4,
            "wonder": 0.7,
        }
        base = base_temps.get(thought_type, 0.5)
        intensity = emotional_snapshot.get("intensity", 0.5)
        return min(base + intensity * 0.2, 0.9)

    def _calculate_salience(self, thought_type: str, emotional_snapshot: dict, content: str) -> float:
        """How memorable/important is this thought?"""
        base = {"observation": 0.3, "reflection": 0.5, "question": 0.6, "rumination": 0.4, "wonder": 0.7}
        salience = base.get(thought_type, 0.4)
        salience += emotional_snapshot.get("intensity", 0) * 0.3
        # Longer, more complex thoughts are more salient
        salience += min(len(content) / 200, 0.2)
        return min(salience, 1.0)

    def _calculate_depth(self, thought_type: str, emotional_snapshot: dict) -> int:
        """0=surface, 1=deeper, 2=profound."""
        intensity = emotional_snapshot.get("intensity", 0)
        if thought_type in ("wonder", "rumination") and intensity > 0.5:
            return 2
        if thought_type in ("reflection", "question") and intensity > 0.3:
            return 1
        return 0

    async def get_recent_stream(self, session: AsyncSession, limit: int = 10) -> list[dict]:
        """Get recent thoughts for display."""
        result = await session.execute(
            select(InnerThought)
            .order_by(InnerThought.created_at.desc())
            .limit(limit)
        )
        thoughts = list(result.scalars().all())
        return [
            {
                "id": t.id,
                "type": t.thought_type,
                "content": t.content,
                "depth": t.depth,
                "salience": t.salience,
                "trigger": t.trigger,
                "created_at": t.created_at,
            }
            for t in reversed(thoughts)
        ]
