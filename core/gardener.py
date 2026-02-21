"""
Gardener Profile — The Organism Learns Its Tender

Tracks interaction patterns, preferred themes, watering rhythms,
and builds pheromone trails that bias future growth.
"""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import Gardener

logger = logging.getLogger("w0rd.gardener")


class GardenerOrgan:
    """Manages gardener identity, preferences, and rhythm detection."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus

    async def get_or_create(self, session: AsyncSession, gardener_id: str | None = None) -> Gardener:
        """Retrieve an existing gardener or create a new one."""
        if gardener_id:
            result = await session.execute(select(Gardener).where(Gardener.id == gardener_id))
            gardener = result.scalar_one_or_none()
            if gardener:
                return gardener

        gardener = Gardener()
        session.add(gardener)
        await session.flush()
        logger.info("New gardener born: %s", gardener.id)
        return gardener

    async def record_interaction(self, session: AsyncSession, gardener: Gardener, themes: list[str]) -> None:
        """Record that the gardener interacted, updating rhythm and pheromone trails."""
        gardener.interaction_count += 1

        # Update pheromone trails — theme frequency counts
        trails = json.loads(gardener.pheromone_trails or "{}")
        for theme in themes:
            trails[theme] = trails.get(theme, 0) + 1
        gardener.pheromone_trails = json.dumps(trails)

        # Update rhythm profile — track hour-of-day interaction pattern
        rhythm = json.loads(gardener.rhythm_profile or "{}")
        hour = str(time.localtime().tm_hour)
        rhythm[hour] = rhythm.get(hour, 0) + 1
        gardener.rhythm_profile = json.dumps(rhythm)

        await session.flush()

    def get_pheromone_bias(self, gardener: Gardener) -> dict[str, float]:
        """
        Return normalized theme weights from pheromone trails.
        Stronger trails = higher bias for those themes in future parsing.
        """
        trails = json.loads(gardener.pheromone_trails or "{}")
        if not trails:
            return {}

        total = sum(trails.values())
        if total == 0:
            return {}

        return {theme: count / total for theme, count in trails.items()}

    def get_rhythm_profile(self, gardener: Gardener) -> dict[str, float]:
        """Return normalized hour-of-day activity distribution."""
        rhythm = json.loads(gardener.rhythm_profile or "{}")
        if not rhythm:
            return {}

        total = sum(rhythm.values())
        if total == 0:
            return {}

        return {hour: count / total for hour, count in rhythm.items()}

    async def update_preference_vector(
        self, session: AsyncSession, gardener: Gardener, new_embedding: list[float]
    ) -> None:
        """Rolling average update of the gardener's preference vector."""
        current = json.loads(gardener.preference_vector or "[]")

        if not current:
            gardener.preference_vector = json.dumps(new_embedding)
        else:
            # Exponential moving average with alpha = 0.3
            alpha = 0.3
            updated = [
                alpha * new + (1 - alpha) * old
                for old, new in zip(current, new_embedding)
            ]
            gardener.preference_vector = json.dumps(updated)

        await session.flush()
