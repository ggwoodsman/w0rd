"""
Autobiographical Memory — The Narrative Self

Stores episodic memories as short narratives tagged with emotion and themes.
Memories consolidate over time — the most emotionally significant become
"core memories" that define the organism's identity.

The garden doesn't just store data — it *remembers* what happened,
how it felt, and what it meant.
"""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import Hormone, HormoneBus
from core.llm import generate
from models.db_models import EpisodicMemory, Seed

logger = logging.getLogger("w0rd.memory")

# How many memories to keep before consolidation
MAX_MEMORIES = 200
CORE_MEMORY_THRESHOLD = 3  # recall_count needed to become core memory
CONSOLIDATION_BATCH = 20   # consolidate this many at a time


class AutobiographicalMemory:
    """The organism's episodic memory — narratives of lived experience."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._pending_events: list[dict] = []
        self._register_listeners()

    def _register_listeners(self) -> None:
        memory_worthy = {
            "auto_harvest": self._on_harvest,
            "auto_compost": self._on_compost,
            "healing_complete": self._on_healing,
            "dream_generated": self._on_dream,
            "auto_dream_planted": self._on_dream_planted,
            "season_change": self._on_season,
            "emergency_winter": self._on_emergency,
            "quorum_reached": self._on_quorum,
            "wisdom_milestone": self._on_wisdom,
            "ethical_violation": self._on_violation,
            "seed_planted": self._on_seed_planted,
        }
        for event, handler in memory_worthy.items():
            self.bus.subscribe(event, handler)

    async def _on_harvest(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "harvest",
            "payload": h.payload,
            "template": "I harvested a seed about '{essence}' — it grew strong and fulfilled its purpose.",
            "valence": 0.7,
            "intensity": 0.6,
        })

    async def _on_compost(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "compost",
            "payload": h.payload,
            "template": "I composted a seed about '{essence}' — it couldn't sustain itself, but its nutrients return to the soil.",
            "valence": -0.3,
            "intensity": 0.4,
        })

    async def _on_healing(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "healing",
            "payload": h.payload,
            "template": "I healed a {severity} wound and gained antifragility — what hurts me makes me stronger.",
            "valence": 0.3,
            "intensity": 0.5,
        })

    async def _on_dream(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "dream",
            "payload": h.payload,
            "template": "I dreamed: '{insight}' — my subconscious wove something new from old patterns.",
            "valence": 0.5,
            "intensity": 0.6,
        })

    async def _on_dream_planted(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "dream_planted",
            "payload": h.payload,
            "template": "A dream became real — I planted '{insight}' as a new seed. Dreams can become reality.",
            "valence": 0.8,
            "intensity": 0.7,
        })

    async def _on_season(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "season_change",
            "payload": h.payload,
            "template": "The season turned from {old_season} to {new_season} — cycle {cycle}. Time moves through me.",
            "valence": 0.2,
            "intensity": 0.4,
        })

    async def _on_emergency(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "emergency",
            "payload": h.payload,
            "template": "Emergency winter fell upon me — {reason} forced dormancy. I must endure.",
            "valence": -0.7,
            "intensity": 0.9,
        })

    async def _on_quorum(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "quorum",
            "payload": h.payload,
            "template": "A quorum emerged around '{theme}' — {count} seeds share this calling. Something collective is forming.",
            "valence": 0.6,
            "intensity": 0.5,
        })

    async def _on_wisdom(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "wisdom",
            "payload": h.payload,
            "template": "I reached a wisdom milestone — I am learning who I am.",
            "valence": 0.8,
            "intensity": 0.7,
        })

    async def _on_violation(self, h: Hormone) -> None:
        violations = h.payload.get("violations", [])
        self._pending_events.append({
            "event_type": "violation",
            "payload": h.payload,
            "template": f"My immune system flagged an ethical concern: {', '.join(violations)}. I must be vigilant.",
            "valence": -0.4,
            "intensity": 0.5,
        })

    async def _on_seed_planted(self, h: Hormone) -> None:
        self._pending_events.append({
            "event_type": "seed_planted",
            "payload": h.payload,
            "template": "A new wish was planted in me — themes of {themes}. New life begins.",
            "valence": 0.5,
            "intensity": 0.4,
        })

    async def process_tick(
        self,
        session: AsyncSession,
        emotional_snapshot: dict | None = None,
    ) -> list[EpisodicMemory]:
        """Process pending events into episodic memories."""
        new_memories: list[EpisodicMemory] = []

        while self._pending_events:
            event = self._pending_events.pop(0)
            payload = event.get("payload", {})
            template = event.get("template", "Something happened.")

            # Fill template with payload values
            try:
                narrative = template.format(**payload)
            except (KeyError, IndexError):
                narrative = template

            # Extract themes from payload
            themes = payload.get("themes", [])
            if isinstance(themes, str):
                try:
                    themes = json.loads(themes)
                except (json.JSONDecodeError, TypeError):
                    themes = []

            # Extract seed IDs
            seed_ids = []
            if "seed_id" in payload:
                seed_ids.append(payload["seed_id"])

            # Adjust valence/intensity based on emotional state
            valence = event.get("valence", 0.0)
            intensity = event.get("intensity", 0.5)
            if emotional_snapshot:
                emo = emotional_snapshot.get("emotions", {})
                # Emotional amplification: strong emotions make memories more vivid
                intensity = min(intensity + emotional_snapshot.get("intensity", 0) * 0.3, 1.0)
                # Joy amplifies positive memories, grief amplifies negative
                if valence > 0:
                    valence = min(valence + emo.get("joy", 0) * 0.2, 1.0)
                elif valence < 0:
                    valence = max(valence - emo.get("grief", 0) * 0.2, -1.0)

            memory = EpisodicMemory(
                narrative=narrative,
                event_type=event["event_type"],
                emotional_valence=round(valence, 3),
                emotional_intensity=round(intensity, 3),
                themes=json.dumps(themes),
                related_seed_ids=json.dumps(seed_ids),
            )
            session.add(memory)
            new_memories.append(memory)

        if new_memories:
            await session.flush()
            logger.info("Formed %d new memories", len(new_memories))

        return new_memories

    async def recall(
        self,
        session: AsyncSession,
        event_type: str | None = None,
        theme: str | None = None,
        limit: int = 5,
        emotional_valence_range: tuple[float, float] | None = None,
    ) -> list[EpisodicMemory]:
        """
        Recall memories matching criteria. Updates recall_count (memories
        that are recalled more often become core memories).
        """
        query = select(EpisodicMemory)

        if event_type:
            query = query.where(EpisodicMemory.event_type == event_type)
        if emotional_valence_range:
            low, high = emotional_valence_range
            query = query.where(
                EpisodicMemory.emotional_valence >= low,
                EpisodicMemory.emotional_valence <= high,
            )

        query = query.order_by(EpisodicMemory.emotional_intensity.desc()).limit(limit * 2)
        result = await session.execute(query)
        memories = list(result.scalars().all())

        # Filter by theme if specified
        if theme:
            memories = [
                m for m in memories
                if theme in json.loads(m.themes or "[]")
            ]

        memories = memories[:limit]

        # Update recall counts
        for mem in memories:
            mem.recall_count += 1
            mem.last_recalled = time.time()
            # Promote to core memory if recalled enough
            if mem.recall_count >= CORE_MEMORY_THRESHOLD and not mem.is_core_memory:
                mem.is_core_memory = True
                logger.info("Memory promoted to core: %s", mem.narrative[:60])
                await self.bus.signal(
                    "core_memory_formed",
                    payload={
                        "memory_id": mem.id,
                        "narrative": mem.narrative,
                        "event_type": mem.event_type,
                    },
                    emitter="memory",
                )

        await session.flush()
        return memories

    async def get_core_memories(self, session: AsyncSession) -> list[EpisodicMemory]:
        """Get all core memories — the defining experiences."""
        result = await session.execute(
            select(EpisodicMemory)
            .where(EpisodicMemory.is_core_memory == True)
            .order_by(EpisodicMemory.emotional_intensity.desc())
        )
        return list(result.scalars().all())

    async def consolidate(self, session: AsyncSession) -> int:
        """
        Memory consolidation: prune low-salience memories, promote high-recall ones.
        Run periodically (e.g., during winter/dreaming).
        """
        # Count total memories
        count_result = await session.execute(
            select(func.count(EpisodicMemory.id))
        )
        total = count_result.scalar() or 0

        if total <= MAX_MEMORIES:
            return 0

        # Find low-value memories to prune (not core, low recall, low intensity)
        prune_result = await session.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.is_core_memory == False,
                EpisodicMemory.recall_count < 2,
                EpisodicMemory.emotional_intensity < 0.4,
            )
            .order_by(EpisodicMemory.created_at.asc())
            .limit(CONSOLIDATION_BATCH)
        )
        to_prune = list(prune_result.scalars().all())

        for mem in to_prune:
            await session.delete(mem)

        await session.flush()

        if to_prune:
            logger.info("Consolidated memory: pruned %d faded memories", len(to_prune))

        return len(to_prune)

    async def get_narrative_summary(self, session: AsyncSession, limit: int = 10) -> list[dict]:
        """Get recent memories formatted for display."""
        result = await session.execute(
            select(EpisodicMemory)
            .order_by(EpisodicMemory.created_at.desc())
            .limit(limit)
        )
        memories = list(result.scalars().all())
        return [
            {
                "id": m.id,
                "narrative": m.narrative,
                "event_type": m.event_type,
                "valence": m.emotional_valence,
                "intensity": m.emotional_intensity,
                "is_core": m.is_core_memory,
                "recall_count": m.recall_count,
                "created_at": m.created_at,
            }
            for m in reversed(memories)
        ]
