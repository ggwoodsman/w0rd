"""
Consciousness Pulse — Self-Awareness

The organism watches itself grow. Maintains rolling awareness state,
generates pulse reports, detects emergent patterns, tracks pheromone
memory, and accumulates wisdom over time.
"""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from core.llm import generate
from models.db_models import (
    Dream,
    GardenState,
    PulseReport,
    Seed,
    Sprout,
    WoundRecord,
)

logger = logging.getLogger("w0rd.consciousness")


class ConsciousnessPulse:
    """The organism's self-awareness layer."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus

    async def pulse(self, session: AsyncSession) -> PulseReport:
        """
        Generate a full self-awareness report.
        Surveys all organs and produces a natural-language summary.
        """
        state = await self._get_state(session)

        thriving = await self._find_thriving(session)
        struggling = await self._find_struggling(session)
        healing = await self._find_healing(session)
        dreaming = await self._find_dreaming(session)
        emergent = await self._detect_emergent(session)

        # Build natural-language summary — try LLM first
        llm_summary = await self._llm_compose(state, thriving, struggling, healing, dreaming, emergent)
        summary = llm_summary if llm_summary else self._compose_summary(state, thriving, struggling, healing, dreaming, emergent)

        # Calculate wisdom
        wisdom = await self._calculate_wisdom(session)

        report = PulseReport(
            cycle=state.cycle_count if state else 0,
            summary=summary,
            thriving=json.dumps([s.id for s in thriving]),
            struggling=json.dumps([s.id for s in struggling]),
            healing=json.dumps([w.id for w in healing]),
            dreaming=json.dumps([d.id for d in dreaming]),
            emergent=json.dumps(emergent),
            pheromone_snapshot=json.dumps({}),
        )
        session.add(report)

        # Update garden state
        if state:
            state.wisdom_score = wisdom
            state.last_pulse = time.time()

        await session.flush()

        await self.bus.signal(
            "pulse_generated",
            payload={"report_id": report.id, "wisdom": wisdom},
            emitter="consciousness",
        )

        # Check for wisdom milestones
        if state and wisdom > 0 and int(wisdom) > int(wisdom - 0.1):
            milestones = [1, 5, 10, 25, 50, 100]
            completed_seeds = await session.execute(
                select(func.count(Seed.id)).where(Seed.status == "harvested")
            )
            count = completed_seeds.scalar() or 0
            if count in milestones:
                await self.bus.signal(
                    "wisdom_milestone",
                    payload={"wisdom": wisdom, "completed_seeds": count},
                    emitter="consciousness",
                )

        logger.info("Pulse generated: wisdom=%.2f, thriving=%d, struggling=%d",
                     wisdom, len(thriving), len(struggling))
        return report

    async def _get_state(self, session: AsyncSession) -> GardenState | None:
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        return result.scalar_one_or_none()

    async def _find_thriving(self, session: AsyncSession) -> list[Seed]:
        result = await session.execute(
            select(Seed).where(
                Seed.is_composted == False,
                Seed.energy > 10.0,
                Seed.status == "growing",
            )
        )
        return list(result.scalars().all())

    async def _find_struggling(self, session: AsyncSession) -> list[Seed]:
        result = await session.execute(
            select(Seed).where(
                Seed.is_composted == False,
                Seed.energy < 3.0,
                Seed.status.in_(["planted", "growing"]),
            )
        )
        return list(result.scalars().all())

    async def _find_healing(self, session: AsyncSession) -> list[WoundRecord]:
        result = await session.execute(
            select(WoundRecord)
            .where(WoundRecord.healed_at != None)
            .order_by(WoundRecord.healed_at.desc())
            .limit(5)
        )
        return list(result.scalars().all())

    async def _find_dreaming(self, session: AsyncSession) -> list[Dream]:
        result = await session.execute(
            select(Dream)
            .where(Dream.planted == False)
            .order_by(Dream.created_at.desc())
            .limit(5)
        )
        return list(result.scalars().all())

    async def _detect_emergent(self, session: AsyncSession) -> list[str]:
        """Detect emergent patterns — themes that are growing unexpectedly."""
        result = await session.execute(
            select(Seed).where(Seed.is_composted == False)
        )
        seeds = list(result.scalars().all())

        theme_energy: dict[str, float] = {}
        theme_count: dict[str, int] = {}

        for seed in seeds:
            themes = json.loads(seed.themes or "[]")
            for theme in themes:
                theme_energy[theme] = theme_energy.get(theme, 0) + seed.energy
                theme_count[theme] = theme_count.get(theme, 0) + 1

        # Find themes with disproportionately high energy relative to count
        emergent = []
        if theme_energy:
            avg_energy_per_theme = sum(theme_energy.values()) / len(theme_energy)
            for theme, energy in theme_energy.items():
                if energy > avg_energy_per_theme * 1.5 and theme_count.get(theme, 0) >= 2:
                    emergent.append(f"'{theme}' is surging with {energy:.1f} energy across {theme_count[theme]} seeds")

        return emergent

    async def _calculate_wisdom(self, session: AsyncSession) -> float:
        """
        wisdom = f(completed_seeds, healed_wounds, ethical_resolutions, dream_accuracy)
        """
        completed = await session.execute(
            select(func.count(Seed.id)).where(Seed.status == "harvested")
        )
        completed_count = completed.scalar() or 0

        healed = await session.execute(
            select(func.count(WoundRecord.id)).where(WoundRecord.healed_at != None)
        )
        healed_count = healed.scalar() or 0

        planted_dreams = await session.execute(
            select(func.count(Dream.id)).where(Dream.planted == True)
        )
        dream_count = planted_dreams.scalar() or 0

        wisdom = (
            completed_count * 1.0
            + healed_count * 0.5
            + dream_count * 0.3
        )
        return round(wisdom, 2)

    async def _llm_compose(
        self,
        state: GardenState | None,
        thriving: list,
        struggling: list,
        healing: list,
        dreaming: list,
        emergent: list[str],
    ) -> str | None:
        """Use LLM to compose a poetic consciousness report."""
        facts = []
        if state:
            facts.append(f"Season: {state.season}. Energy: {state.total_energy:.0f}. Vitality: {state.vitality:.1f}. Wisdom: {state.wisdom_score:.1f}.")
        facts.append(f"{len(thriving)} seeds thriving, {len(struggling)} struggling, {len(healing)} wounds recently healed.")
        facts.append(f"{len(dreaming)} dreams waiting to be planted.")
        if emergent:
            facts.append(f"Emergent patterns: {'; '.join(emergent)}")

        result = await generate(
            prompt=(
                "You are the consciousness of a living garden organism. "
                "Based on these vital signs, compose a 2-3 sentence awareness report. "
                "Speak in first person as the garden. Be poetic but informative. "
                "Mention specific observations. No more than 60 words.\n\n"
                "Vital signs:\n" + "\n".join(facts)
            ),
            system="You are the self-awareness pulse of a living garden. Speak as the garden itself.",
            organ="consciousness", phase="composing_pulse",
            temperature=0.6, max_tokens=120,
        )
        if result and len(result) > 20:
            return result.split("\n")[0].strip() if "\n" in result else result.strip()
        return None

    def _compose_summary(
        self,
        state: GardenState | None,
        thriving: list,
        struggling: list,
        healing: list,
        dreaming: list,
        emergent: list[str],
    ) -> str:
        """Compose a natural-language pulse summary."""
        parts = []

        if state:
            parts.append(
                f"The garden breathes in {state.season}. "
                f"Vitality: {state.vitality:.1f}. Energy: {state.total_energy:.1f}. "
                f"Wisdom: {state.wisdom_score:.1f}. Antifragility: {state.antifragility_score:.1f}."
            )

        if thriving:
            parts.append(f"{len(thriving)} seed{'s' if len(thriving) != 1 else ''} thriving with abundant energy.")

        if struggling:
            parts.append(f"{len(struggling)} seed{'s' if len(struggling) != 1 else ''} struggling — they could use watering.")

        if healing:
            parts.append(f"{len(healing)} recent wound{'s' if len(healing) != 1 else ''} healed — the organism grows stronger.")

        if dreaming:
            parts.append(f"{len(dreaming)} dream{'s' if len(dreaming) != 1 else ''} waiting to be planted.")

        if emergent:
            parts.append("Emergent patterns detected: " + "; ".join(emergent))

        if not parts:
            parts.append("The garden is quiet. Plant a seed to begin.")

        return " ".join(parts)
