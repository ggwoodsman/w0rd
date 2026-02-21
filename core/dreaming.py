"""
Dreaming Engine — The Subconscious

Activates during winter or idle periods. Consolidates completed seed
patterns into archetypes, then recombines them via Markov-like walks
with temperature-controlled creativity to generate novel seed suggestions.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from core.llm import generate
from models.db_models import Dream, Seed

logger = logging.getLogger("w0rd.dreaming")


def _centroid(vectors: list[list[float]]) -> list[float]:
    """Average of a list of vectors — the archetype center."""
    if not vectors:
        return []
    dim = len(vectors[0])
    result = [0.0] * dim
    for v in vectors:
        for i in range(min(dim, len(v))):
            result[i] += v[i]
    return [x / len(vectors) for x in result]


def _perturb(vector: list[float], temperature: float) -> list[float]:
    """Add Gaussian noise scaled by temperature for creative variation."""
    return [
        x + random.gauss(0, temperature * 0.1)
        for x in vector
    ]


def _perplexity(vector: list[float], archetype: list[float]) -> float:
    """
    Measure how far a dream vector is from the archetype center.
    Lower = more coherent (lucid), higher = more novel.
    """
    if not vector or not archetype or len(vector) != len(archetype):
        return 1.0
    dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(vector, archetype)))
    return round(min(dist, 5.0), 4)


def _generate_insight(themes: list[str], temperature: float) -> str:
    """
    Generate a dream insight by recombining themes.
    Higher temperature = more surprising combinations.
    """
    if not themes:
        return "The garden rests in quiet potential."

    # Shuffle themes with temperature-controlled randomness
    shuffled = list(themes)
    for _ in range(int(temperature * 5)):
        if len(shuffled) >= 2:
            i, j = random.sample(range(len(shuffled)), 2)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]

    # Combine themes into dream-like insight phrases
    connectors = [
        "meets", "flows into", "awakens", "transforms through",
        "dances with", "remembers", "seeds", "nurtures",
        "illuminates", "bridges", "weaves into", "echoes",
    ]

    if len(shuffled) == 1:
        return f"A deeper layer of {shuffled[0]} wants to emerge."

    pairs = []
    for i in range(0, len(shuffled) - 1, 2):
        connector = random.choice(connectors)
        pairs.append(f"{shuffled[i]} {connector} {shuffled[i + 1]}")

    if len(shuffled) % 2 == 1:
        pairs.append(f"{shuffled[-1]} awaits its moment")

    return ". ".join(pairs).capitalize() + "."


async def _llm_dream(themes: list[str], seed_essences: list[str], temperature: float) -> str | None:
    """Use LLM to generate a creative dream insight from completed seed patterns."""
    theme_str = ", ".join(themes) if themes else "the garden's quiet potential"
    seeds_str = "\n".join(f"- {e}" for e in seed_essences[:5]) if seed_essences else "- quiet stillness"
    result = await generate(
        prompt=(
            f"The garden is dreaming. These themes swirl in its subconscious: {theme_str}\n\n"
            f"Recent memories being processed:\n{seeds_str}\n\n"
            "Generate ONE dream-like insight (1-2 sentences, max 40 words). "
            "It should be surprising, poetic, and suggest a new direction the gardener "
            "hasn't considered. Combine themes in unexpected ways. "
            "Speak as the garden's subconscious. No quotes, no explanation."
        ),
        system="You are the dreaming subconscious of a living garden organism. You recombine memories into novel visions.",
        organ="dreaming", phase="dreaming",
        temperature=min(temperature + 0.3, 1.2), max_tokens=100,
    )
    if result and len(result) > 10:
        return result.split("\n")[0].strip()
    return None


class DreamingEngine:
    """The garden's subconscious — dreams during dormancy and idle periods."""

    def __init__(self, bus: HormoneBus, default_temperature: float = 0.7):
        self.bus = bus
        self.default_temperature = default_temperature

    async def dream(
        self,
        session: AsyncSession,
        temperature: float | None = None,
    ) -> Dream | None:
        """
        Generate a dream from completed seed archetypes.
        Returns the Dream object, or None if not enough material.
        """
        temp = temperature or self.default_temperature

        # Gather completed seeds as dream material
        result = await session.execute(
            select(Seed).where(Seed.status.in_(["harvested", "composted"]))
        )
        completed = list(result.scalars().all())

        if not completed:
            logger.debug("No completed seeds to dream about — garden too young")
            return None

        # Consolidate into archetype
        embeddings = [json.loads(s.embedding or "[]") for s in completed if json.loads(s.embedding or "[]")]
        all_themes: list[str] = []
        source_ids: list[str] = []

        for seed in completed:
            themes = json.loads(seed.themes or "[]")
            all_themes.extend(themes)
            source_ids.append(seed.id)

        # Deduplicate themes but preserve frequency for weighting
        unique_themes = list(set(all_themes))

        # Generate archetype vector
        archetype = _centroid(embeddings) if embeddings else []

        # Perturb for creative variation
        dream_vector = _perturb(archetype, temp) if archetype else []

        # Calculate perplexity (novelty measure)
        pplx = _perplexity(dream_vector, archetype) if archetype else 0.5

        # Generate insight text — try LLM first
        llm_insight = await _llm_dream(unique_themes, [s.essence or s.raw_text for s in completed[-5:]], temp)
        insight = llm_insight if llm_insight else _generate_insight(unique_themes, temp)

        dream = Dream(
            source_seed_ids=json.dumps(source_ids[-10:]),  # last 10 sources
            insight=insight,
            archetype_vector=json.dumps([round(x, 6) for x in dream_vector]),
            temperature=temp,
            perplexity=pplx,
            planted=False,
        )
        session.add(dream)
        await session.flush()

        # Determine if lucid (high confidence = low perplexity)
        is_lucid = pplx < 0.5
        hormone_name = "lucid_dream" if is_lucid else "dream_generated"

        await self.bus.signal(
            hormone_name,
            payload={
                "dream_id": dream.id,
                "insight": insight,
                "perplexity": pplx,
                "temperature": temp,
                "is_lucid": is_lucid,
            },
            emitter="dreaming",
        )

        logger.info(
            "Dream generated: %s (perplexity=%.2f, lucid=%s) — '%s'",
            dream.id, pplx, is_lucid, insight[:80],
        )
        return dream

    async def plant_dream(self, session: AsyncSession, dream_id: str) -> Seed | None:
        """Turn a dream into a new seed — the gardener plants what resonated."""
        result = await session.execute(select(Dream).where(Dream.id == dream_id))
        dream = result.scalar_one_or_none()
        if not dream or dream.planted:
            return None

        dream.planted = True

        # Create a new seed from the dream's insight
        seed = Seed(
            raw_text=dream.insight,
            essence=dream.insight,
            embedding=dream.archetype_vector,
            themes=json.dumps(["dream"]),
            resonance=0.8,  # dreams have high resonance
            energy=8.0,
            status="planted",
        )
        session.add(seed)
        await session.flush()

        await self.bus.signal(
            "dream_planted",
            payload={"dream_id": dream.id, "new_seed_id": seed.id},
            emitter="dreaming",
        )

        logger.info("Dream %s planted as seed %s", dream.id, seed.id)
        return seed
