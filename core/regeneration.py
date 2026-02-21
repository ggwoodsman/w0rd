"""
Seasonal Heartbeat — The Breath of Dormancy and Renewal

Four seasons with distinct behaviors layered with tidal micro-rhythms.
Spring awakening, summer peak, autumn harvest, winter dormancy.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import GardenState, Seed, Sprout

logger = logging.getLogger("w0rd.regeneration")

SEASON_ORDER = ["spring", "summer", "autumn", "winter"]

SEASON_BEHAVIORS = {
    "spring": {
        "growth_bonus": 1.3,
        "decay_modifier": 0.5,
        "photosynthesis_modifier": 1.2,
        "dreaming_active": False,
        "pollination_active": True,
        "description": "Energy redistribution, dream-planting, new growth bonus",
    },
    "summer": {
        "growth_bonus": 1.0,
        "decay_modifier": 1.0,
        "photosynthesis_modifier": 1.5,
        "dreaming_active": False,
        "pollination_active": True,
        "description": "Peak activity, maximum photosynthesis, pollination active",
    },
    "autumn": {
        "growth_bonus": 0.7,
        "decay_modifier": 0.8,
        "photosynthesis_modifier": 0.8,
        "dreaming_active": False,
        "pollination_active": False,
        "description": "Declining branches flagged, energy reclamation, harvest bonus",
    },
    "winter": {
        "growth_bonus": 0.0,
        "decay_modifier": 0.2,
        "photosynthesis_modifier": 0.3,
        "dreaming_active": True,
        "pollination_active": False,
        "description": "No new growth, dreaming active, memory consolidation",
    },
}


class SeasonalHeartbeat:
    """The organism's breath — seasonal macro-cycles and tidal micro-rhythms."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self.bus.subscribe("emergency_winter", self._on_emergency_winter)

    async def _on_emergency_winter(self, hormone) -> None:
        """Handle emergency winter triggered by severe wounds."""
        logger.warning("Emergency winter triggered: %s", hormone.payload.get("reason", "unknown"))

    async def get_current_season(self, session: AsyncSession) -> str:
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        return state.season if state else "spring"

    async def turn_season(self, session: AsyncSession, force_season: str | None = None) -> str:
        """
        Advance to the next season (or force a specific one).
        Applies season-specific behaviors and emits hormone.
        """
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if not state:
            return "spring"

        old_season = state.season

        if force_season and force_season in SEASON_ORDER:
            new_season = force_season
        else:
            current_idx = SEASON_ORDER.index(old_season) if old_season in SEASON_ORDER else 0
            new_season = SEASON_ORDER[(current_idx + 1) % len(SEASON_ORDER)]

        state.season = new_season
        state.cycle_count += 1

        # Apply season-specific actions
        await self._apply_season_effects(session, new_season)

        await session.flush()

        await self.bus.signal(
            "season_change",
            payload={
                "old_season": old_season,
                "new_season": new_season,
                "cycle": state.cycle_count,
            },
            emitter="regeneration",
        )

        logger.info("Season turned: %s → %s (cycle %d)", old_season, new_season, state.cycle_count)
        return new_season

    async def _apply_season_effects(self, session: AsyncSession, season: str) -> None:
        """Apply season-specific effects to the garden."""
        behaviors = SEASON_BEHAVIORS.get(season, {})

        if season == "spring":
            await self._spring_awakening(session)
        elif season == "autumn":
            await self._autumn_harvest(session)
        elif season == "winter":
            await self._winter_dormancy(session)

    async def _spring_awakening(self, session: AsyncSession) -> None:
        """Spring: redistribute energy, boost vitality of growing seeds."""
        result = await session.execute(
            select(Seed).where(Seed.is_composted == False, Seed.status == "growing")
        )
        seeds = list(result.scalars().all())
        for seed in seeds:
            seed.energy *= 1.1  # spring energy boost
            seed.vitality = min(seed.vitality + 0.1, 2.0)
        await session.flush()
        logger.info("Spring awakening: boosted %d growing seeds", len(seeds))

    async def _autumn_harvest(self, session: AsyncSession) -> None:
        """Autumn: flag declining sprouts, begin energy reclamation."""
        result = await session.execute(
            select(Sprout).where(
                Sprout.is_composted == False,
                Sprout.energy < 0.5,
                Sprout.status == "budding",
            )
        )
        wilting = list(result.scalars().all())
        for sprout in wilting:
            sprout.status = "wilting"
        await session.flush()
        logger.info("Autumn: flagged %d wilting sprouts", len(wilting))

    async def _winter_dormancy(self, session: AsyncSession) -> None:
        """Winter: no new growth, prepare for dreaming."""
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if state:
            state.vitality = max(state.vitality * 0.9, 0.3)
        await session.flush()
        logger.info("Winter dormancy: garden resting")

    def get_season_behavior(self, season: str) -> dict:
        """Get the behavior configuration for a season."""
        return SEASON_BEHAVIORS.get(season, SEASON_BEHAVIORS["spring"])
