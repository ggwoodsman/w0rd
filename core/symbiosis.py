"""
Mycelial Network — The Underground Intelligence

Connects all gardens through symbiotic linking, cross-pollination of
successful patterns, quorum sensing for critical mass detection, and
nutrient sharing along synergy-weighted links.
"""

from __future__ import annotations

import json
import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import Seed, Sprout, SymbioticLink

logger = logging.getLogger("w0rd.symbiosis")

QUORUM_THRESHOLD = 3       # minimum seeds sharing a theme to trigger quorum
SIMILARITY_THRESHOLD = 0.4  # minimum cosine similarity for symbiotic link


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _theme_overlap(themes_a: list[str], themes_b: list[str]) -> float:
    """Jaccard similarity between theme sets."""
    set_a, set_b = set(themes_a), set(themes_b)
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _classify_relationship(synergy: float, energy_a: float, energy_b: float) -> str:
    """Classify symbiotic relationship type."""
    if synergy > 0.6:
        return "mutualism"
    elif abs(energy_a - energy_b) > max(energy_a, energy_b) * 0.5:
        return "commensalism"
    elif synergy < 0.1:
        return "parasitism"
    return "mutualism"


class MycelialNetwork:
    """The underground intelligence connecting all seeds."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus

    async def scan_and_link(self, session: AsyncSession) -> list[SymbioticLink]:
        """
        Scan all living seeds for potential symbiotic connections.
        Creates links where similarity exceeds threshold.
        Preloads existing links to avoid N+1 queries.
        """
        result = await session.execute(
            select(Seed).where(Seed.is_composted == False)
        )
        seeds = list(result.scalars().all())
        if len(seeds) < 2:
            return []

        # Preload all existing link pairs into a set for O(1) lookup
        existing_result = await session.execute(select(SymbioticLink))
        existing_pairs: set[tuple[str, str]] = set()
        for link in existing_result.scalars().all():
            existing_pairs.add((link.sprout_a_id, link.sprout_b_id))
            existing_pairs.add((link.sprout_b_id, link.sprout_a_id))

        new_links: list[SymbioticLink] = []

        for i in range(len(seeds)):
            for j in range(i + 1, len(seeds)):
                seed_a, seed_b = seeds[i], seeds[j]

                # O(1) check against preloaded set
                if (seed_a.id, seed_b.id) in existing_pairs:
                    continue

                # Calculate synergy from embeddings and themes
                emb_a = json.loads(seed_a.embedding or "[]")
                emb_b = json.loads(seed_b.embedding or "[]")
                themes_a = json.loads(seed_a.themes or "[]")
                themes_b = json.loads(seed_b.themes or "[]")

                embedding_sim = _cosine_similarity(emb_a, emb_b)
                theme_sim = _theme_overlap(themes_a, themes_b)
                synergy = round(0.6 * embedding_sim + 0.4 * theme_sim, 4)

                if synergy >= SIMILARITY_THRESHOLD:
                    rel_type = _classify_relationship(synergy, seed_a.energy, seed_b.energy)
                    link = SymbioticLink(
                        sprout_a_id=seed_a.id,
                        sprout_b_id=seed_b.id,
                        relationship_type=rel_type,
                        synergy_score=synergy,
                    )
                    session.add(link)
                    new_links.append(link)
                    existing_pairs.add((seed_a.id, seed_b.id))
                    existing_pairs.add((seed_b.id, seed_a.id))

        await session.flush()

        if new_links:
            logger.info("Mycelium formed %d new symbiotic links", len(new_links))

        return new_links

    async def pollinate(self, session: AsyncSession, completed_seed: Seed) -> int:
        """
        Cross-pollination: broadcast a completed seed's essence as pollen.
        Unrelated seeds with partial theme overlap absorb a small boost.
        """
        completed_themes = set(json.loads(completed_seed.themes or "[]"))
        if not completed_themes:
            return 0

        result = await session.execute(
            select(Seed).where(
                Seed.is_composted == False,
                Seed.id != completed_seed.id,
                Seed.status != "harvested",
            )
        )
        living_seeds = list(result.scalars().all())
        pollinated = 0

        for seed in living_seeds:
            seed_themes = set(json.loads(seed.themes or "[]"))
            overlap = completed_themes & seed_themes

            if overlap and len(overlap) < len(completed_themes):
                # Partial overlap = good pollination target
                boost = 0.5 * (len(overlap) / len(completed_themes))
                seed.energy += round(boost, 4)
                seed.warmth = getattr(seed, 'warmth', 0) or 0
                pollinated += 1

        await session.flush()

        if pollinated > 0:
            await self.bus.signal(
                "pollination",
                payload={
                    "source_seed_id": completed_seed.id,
                    "pollinated_count": pollinated,
                },
                emitter="symbiosis",
            )
            logger.info("Pollinated %d seeds from completed seed %s", pollinated, completed_seed.id)

        return pollinated

    async def check_quorum(self, session: AsyncSession) -> list[str]:
        """
        Quorum sensing: detect theme clusters that have reached critical mass.
        Returns list of themes that triggered quorum.
        """
        result = await session.execute(
            select(Seed).where(Seed.is_composted == False)
        )
        seeds = list(result.scalars().all())

        # Count theme frequencies
        theme_counts: dict[str, int] = {}
        for seed in seeds:
            themes = json.loads(seed.themes or "[]")
            for theme in themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

        quorum_themes = [
            theme for theme, count in theme_counts.items()
            if count >= QUORUM_THRESHOLD
        ]

        for theme in quorum_themes:
            await self.bus.signal(
                "quorum_reached",
                payload={"theme": theme, "count": theme_counts[theme]},
                emitter="symbiosis",
            )
            logger.info("Quorum reached for theme '%s' (%d seeds)", theme, theme_counts[theme])

        return quorum_themes

    async def share_nutrients(self, session: AsyncSession) -> float:
        """
        Flow surplus energy along symbiotic links weighted by synergy_score.
        Preloads all seeds into a dict to avoid N+1 queries.
        Returns total energy transferred.
        """
        result = await session.execute(select(SymbioticLink))
        links = list(result.scalars().all())
        if not links:
            return 0.0

        # Preload all living seeds into a dict for O(1) lookup
        seed_result = await session.execute(
            select(Seed).where(Seed.is_composted == False)
        )
        seed_map: dict[str, Seed] = {s.id: s for s in seed_result.scalars().all()}

        total_transferred = 0.0

        for link in links:
            seed_a = seed_map.get(link.sprout_a_id)
            seed_b = seed_map.get(link.sprout_b_id)

            if not seed_a or not seed_b:
                continue

            # Flow from surplus to deficit
            if seed_a.energy > seed_b.energy * 1.5:
                transfer = (seed_a.energy - seed_b.energy) * 0.1 * link.synergy_score
                seed_a.energy -= transfer
                seed_b.energy += transfer
                link.nutrient_flow += transfer
                total_transferred += transfer
            elif seed_b.energy > seed_a.energy * 1.5:
                transfer = (seed_b.energy - seed_a.energy) * 0.1 * link.synergy_score
                seed_b.energy -= transfer
                seed_a.energy += transfer
                link.nutrient_flow += transfer
                total_transferred += transfer

        await session.flush()

        if total_transferred > 0:
            logger.debug("Mycelium transferred %.2f total energy via nutrient sharing", total_transferred)

        return round(total_transferred, 4)
