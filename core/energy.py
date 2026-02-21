"""
Phloem & Mycorrhizal Flow — The Circulatory System

Models finite energy as a living fluid with vertical phloem transport,
lateral mycorrhizal redistribution, entropy decay, photosynthesis from
user attention, and tidal modulation.
"""

from __future__ import annotations

import json
import logging
import math
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import GardenState, Seed, Sprout

logger = logging.getLogger("w0rd.energy")

PHI = (1 + math.sqrt(5)) / 2


class EnergyOrgan:
    """The organism's circulatory system — manages all energy flow."""

    def __init__(
        self,
        bus: HormoneBus,
        base_photosynthesis_rate: float = 1.0,
        decay_rate: float = 0.02,
        mycorrhizal_ratio: float = 0.15,
        tidal_period_seconds: float = 14400,  # 4 hours
    ):
        self.bus = bus
        self.base_rate = base_photosynthesis_rate
        self.decay_rate = decay_rate
        self.mycorrhizal_ratio = mycorrhizal_ratio
        self.tidal_period = tidal_period_seconds

    # ── Photosynthesis ────────────────────────────────────────────

    async def photosynthesize(
        self,
        session: AsyncSession,
        seed: Seed,
        attention_seconds: float = 1.0,
        resonance_multiplier: float | None = None,
    ) -> float:
        """
        Generate energy from user attention.
        E = base_rate * attention_seconds * resonance_multiplier * tidal_coefficient
        """
        if resonance_multiplier is None:
            resonance_multiplier = max(seed.resonance, 0.1) + 1.0

        tidal = self._tidal_coefficient()
        energy_gained = self.base_rate * attention_seconds * resonance_multiplier * tidal
        energy_gained = round(min(energy_gained, 50.0), 4)

        seed.energy += energy_gained
        await self._update_garden_energy(session, energy_gained)
        await session.flush()

        await self.bus.signal(
            "photosynthesis",
            payload={"seed_id": seed.id, "energy_gained": energy_gained, "tidal": tidal},
            emitter="energy",
        )

        logger.debug("Photosynthesis: seed %s gained %.2f energy (tidal=%.2f)", seed.id, energy_gained, tidal)
        return energy_gained

    # ── Phloem Transport (vertical) ──────────────────────────────

    async def phloem_distribute(self, session: AsyncSession, seed: Seed) -> None:
        """
        Distribute energy vertically from canopy (shallow) to roots (deep).
        Flow proportional to ethical_score * pressure_need.
        """
        result = await session.execute(
            select(Sprout)
            .where(Sprout.seed_id == seed.id, Sprout.is_composted == False)
            .order_by(Sprout.depth)
        )
        sprouts = list(result.scalars().all())
        if not sprouts:
            return

        total_need = sum(s.pressure * s.ethical_score for s in sprouts) or 1.0
        distributable = seed.energy * 0.3  # distribute 30% of seed energy per cycle

        for sprout in sprouts:
            share = (sprout.pressure * sprout.ethical_score / total_need) * distributable
            sprout.energy += round(share, 4)

        seed.energy -= distributable
        await session.flush()
        logger.debug("Phloem distributed %.2f energy across %d sprouts", distributable, len(sprouts))

    # ── Mycorrhizal Redistribution (lateral) ─────────────────────

    async def mycorrhizal_redistribute(self, session: AsyncSession, seed: Seed) -> None:
        """
        Surplus energy from thriving sprouts flows laterally to struggling neighbors.
        Transfer rate = surplus * mycorrhizal_ratio * proximity_score
        """
        result = await session.execute(
            select(Sprout)
            .where(Sprout.seed_id == seed.id, Sprout.is_composted == False)
        )
        sprouts = list(result.scalars().all())
        if len(sprouts) < 2:
            return

        avg_energy = sum(s.energy for s in sprouts) / len(sprouts)
        donors = [s for s in sprouts if s.energy > avg_energy * 1.3]
        receivers = [s for s in sprouts if s.energy < avg_energy * 0.7]

        if not donors or not receivers:
            return

        total_transferred = 0.0
        for donor in donors:
            surplus = donor.energy - avg_energy
            transfer = surplus * self.mycorrhizal_ratio
            donor.energy -= transfer

            per_receiver = transfer / len(receivers)
            for receiver in receivers:
                proximity = 1.0 / (1.0 + abs(donor.depth - receiver.depth))
                actual = per_receiver * proximity
                receiver.energy += round(actual, 4)
                total_transferred += actual

        await session.flush()

        if total_transferred > 0.5:
            await self.bus.signal(
                "energy_surplus",
                payload={"seed_id": seed.id, "transferred": round(total_transferred, 4)},
                emitter="energy",
            )
            logger.debug("Mycorrhizal: transferred %.2f energy in seed %s", total_transferred, seed.id)

    # ── Entropy Decay ─────────────────────────────────────────────

    async def apply_entropy(self, session: AsyncSession, season: str = "summer") -> int:
        """
        Apply entropy decay to all living sprouts.
        energy_t+1 = energy_t * (1 - decay_rate * season_modifier)
        Returns count of sprouts that hit zero.
        """
        season_modifiers = {"spring": 0.5, "summer": 1.0, "autumn": 0.8, "winter": 0.2}
        modifier = season_modifiers.get(season, 1.0)
        effective_decay = self.decay_rate * modifier

        result = await session.execute(
            select(Sprout).where(Sprout.is_composted == False)
        )
        sprouts = list(result.scalars().all())
        depleted_count = 0

        for sprout in sprouts:
            sprout.energy = round(sprout.energy * (1 - effective_decay), 4)
            if sprout.energy < 0.01:
                sprout.energy = 0.0
                depleted_count += 1

        await session.flush()

        if depleted_count > 0:
            await self.bus.signal(
                "energy_famine",
                payload={"depleted_count": depleted_count, "season": season},
                emitter="energy",
            )

        logger.debug("Entropy: decay=%.4f, depleted=%d sprouts", effective_decay, depleted_count)
        return depleted_count

    # ── Tidal Modulation ──────────────────────────────────────────

    def _tidal_coefficient(self) -> float:
        """
        Sinusoidal oscillation between 0.5 and 1.5 over the tidal period.
        Modulates energy availability like circadian rhythm.
        """
        phase = (time.time() % self.tidal_period) / self.tidal_period
        return round(1.0 + 0.5 * math.sin(2 * math.pi * phase), 4)

    def get_tidal_phase(self) -> float:
        """Current tidal phase 0..1."""
        return round((time.time() % self.tidal_period) / self.tidal_period, 4)

    # ── Garden-Level Energy ───────────────────────────────────────

    async def _update_garden_energy(self, session: AsyncSession, delta: float) -> None:
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if state:
            state.total_energy += delta
            state.tidal_phase = self.get_tidal_phase()
