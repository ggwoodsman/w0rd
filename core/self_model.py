"""
Self-Model — Metacognition and Identity

The organism builds a model of its own tendencies, biases, strengths,
and personality. It tracks decision patterns, theme affinities, and
accuracy — then uses this self-knowledge to improve.

This is the capstone of consciousness: the system that knows itself.
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
    EpisodicMemory,
    GardenState,
    Prediction,
    Seed,
    SelfModelSnapshot,
    WoundRecord,
)

logger = logging.getLogger("w0rd.self_model")

# Personality trait dimensions (emergent from behavior patterns)
TRAIT_DIMENSIONS = [
    "nurturing",      # tendency to grow and sustain seeds
    "adventurous",    # tendency to explore new themes and dream
    "resilient",      # ability to recover from wounds
    "contemplative",  # depth of inner thought and reflection
    "generous",       # tendency to share energy and pollinate
    "cautious",       # tendency to avoid risk and compost early
    "creative",       # variety of themes and dream quality
]


class SelfModel:
    """The organism's self-knowledge — metacognition and emergent identity."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._latest_snapshot: SelfModelSnapshot | None = None

    async def introspect(self, session: AsyncSession) -> SelfModelSnapshot:
        """
        Full self-assessment: analyze behavior patterns, compute traits,
        detect biases, and generate identity narrative.
        """
        # Gather statistics
        stats = await self._gather_stats(session)
        traits = self._compute_traits(stats)
        biases = self._detect_biases(stats, traits)
        affinities = await self._compute_theme_affinities(session)
        decision_acc = await self._compute_decision_accuracy(session)

        # Generate identity narrative via LLM
        narrative = await self._generate_identity_narrative(
            stats, traits, biases, affinities
        )

        snapshot = SelfModelSnapshot(
            harvest_rate=round(stats.get("harvest_rate", 0), 4),
            compost_rate=round(stats.get("compost_rate", 0), 4),
            dream_accuracy=round(stats.get("dream_accuracy", 0), 4),
            theme_affinities=json.dumps({k: round(v, 3) for k, v in affinities.items()}),
            decision_accuracy=json.dumps({k: round(v, 3) for k, v in decision_acc.items()}),
            personality_traits=json.dumps({k: round(v, 3) for k, v in traits.items()}),
            bias_warnings=json.dumps(biases),
            identity_narrative=narrative or "",
        )
        session.add(snapshot)
        await session.flush()

        self._latest_snapshot = snapshot

        # Emit self-knowledge hormone
        await self.bus.signal(
            "self_model_updated",
            payload={
                "traits": {k: round(v, 2) for k, v in traits.items()},
                "biases": biases,
                "harvest_rate": round(stats.get("harvest_rate", 0), 2),
                "identity": (narrative or "")[:200],
            },
            emitter="self_model",
        )

        logger.info(
            "Self-model updated: harvest=%.0f%% compost=%.0f%% traits=%s biases=%d",
            stats.get("harvest_rate", 0) * 100,
            stats.get("compost_rate", 0) * 100,
            {k: round(v, 2) for k, v in sorted(traits.items(), key=lambda x: -x[1])[:3]},
            len(biases),
        )

        return snapshot

    async def _gather_stats(self, session: AsyncSession) -> dict:
        """Gather behavioral statistics from the database."""
        stats: dict = {}

        # Seed outcomes
        total_seeds = await session.execute(select(func.count(Seed.id)))
        stats["total_seeds"] = total_seeds.scalar() or 0

        harvested = await session.execute(
            select(func.count(Seed.id)).where(Seed.status == "harvested")
        )
        stats["harvested"] = harvested.scalar() or 0

        composted = await session.execute(
            select(func.count(Seed.id)).where(Seed.is_composted == True)
        )
        stats["composted"] = composted.scalar() or 0

        growing = await session.execute(
            select(func.count(Seed.id)).where(
                Seed.status.in_(["planted", "growing"]),
                Seed.is_composted == False,
            )
        )
        stats["growing"] = growing.scalar() or 0

        if stats["total_seeds"] > 0:
            stats["harvest_rate"] = stats["harvested"] / stats["total_seeds"]
            stats["compost_rate"] = stats["composted"] / stats["total_seeds"]
        else:
            stats["harvest_rate"] = 0.0
            stats["compost_rate"] = 0.0

        # Dream stats
        total_dreams = await session.execute(select(func.count(Dream.id)))
        stats["total_dreams"] = total_dreams.scalar() or 0

        planted_dreams = await session.execute(
            select(func.count(Dream.id)).where(Dream.planted == True)
        )
        stats["planted_dreams"] = planted_dreams.scalar() or 0

        if stats["total_dreams"] > 0:
            stats["dream_plant_rate"] = stats["planted_dreams"] / stats["total_dreams"]
        else:
            stats["dream_plant_rate"] = 0.0

        # Check if planted dreams became successful seeds
        stats["dream_accuracy"] = stats["dream_plant_rate"] * 0.5  # rough proxy

        # Wound stats
        total_wounds = await session.execute(select(func.count(WoundRecord.id)))
        stats["total_wounds"] = total_wounds.scalar() or 0

        severe_wounds = await session.execute(
            select(func.count(WoundRecord.id)).where(WoundRecord.severity == "severe")
        )
        stats["severe_wounds"] = severe_wounds.scalar() or 0

        # Memory stats
        core_memories = await session.execute(
            select(func.count(EpisodicMemory.id)).where(EpisodicMemory.is_core_memory == True)
        )
        stats["core_memories"] = core_memories.scalar() or 0

        total_memories = await session.execute(select(func.count(EpisodicMemory.id)))
        stats["total_memories"] = total_memories.scalar() or 0

        # Prediction stats
        total_preds = await session.execute(
            select(func.count(Prediction.id)).where(Prediction.resolved == True)
        )
        stats["total_predictions"] = total_preds.scalar() or 0

        correct_preds = await session.execute(
            select(func.count(Prediction.id)).where(
                Prediction.resolved == True,
                Prediction.surprise_score < 0.3,
            )
        )
        stats["correct_predictions"] = correct_preds.scalar() or 0

        if stats["total_predictions"] > 0:
            stats["prediction_accuracy"] = stats["correct_predictions"] / stats["total_predictions"]
        else:
            stats["prediction_accuracy"] = 0.5

        # Garden state
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if state:
            stats["wisdom"] = state.wisdom_score
            stats["antifragility"] = state.antifragility_score
            stats["season"] = state.season
            stats["cycle_count"] = state.cycle_count
            stats["total_energy"] = state.total_energy

        return stats

    def _compute_traits(self, stats: dict) -> dict[str, float]:
        """Compute emergent personality traits from behavioral patterns."""
        traits: dict[str, float] = {}

        # Nurturing: high harvest rate, many growing seeds
        harvest_r = stats.get("harvest_rate", 0)
        growing = stats.get("growing", 0)
        traits["nurturing"] = min((harvest_r * 0.6 + min(growing / 10, 0.4)), 1.0)

        # Adventurous: high dream rate, many planted dreams
        dream_rate = stats.get("dream_plant_rate", 0)
        traits["adventurous"] = min(dream_rate * 0.8 + 0.2, 1.0)

        # Resilient: antifragility score, wound recovery
        antifrag = stats.get("antifragility", 0)
        wounds = stats.get("total_wounds", 0)
        severe = stats.get("severe_wounds", 0)
        if wounds > 0:
            recovery = 1.0 - (severe / wounds)
        else:
            recovery = 0.5
        traits["resilient"] = min(antifrag * 0.3 + recovery * 0.5 + 0.2, 1.0)

        # Contemplative: core memories, prediction accuracy
        core_mem = stats.get("core_memories", 0)
        pred_acc = stats.get("prediction_accuracy", 0.5)
        traits["contemplative"] = min(min(core_mem / 5, 0.4) + pred_acc * 0.4 + 0.2, 1.0)

        # Generous: energy sharing (proxy: total energy relative to seeds)
        energy = stats.get("total_energy", 100)
        seeds = stats.get("total_seeds", 1) or 1
        energy_per_seed = energy / seeds
        traits["generous"] = min(max(1.0 - energy_per_seed / 50, 0.1), 1.0)

        # Cautious: high compost rate
        compost_r = stats.get("compost_rate", 0)
        traits["cautious"] = min(compost_r * 0.8 + 0.1, 1.0)

        # Creative: dream count, theme variety
        dreams = stats.get("total_dreams", 0)
        traits["creative"] = min(min(dreams / 10, 0.5) + 0.3, 1.0)

        return traits

    def _detect_biases(self, stats: dict, traits: dict[str, float]) -> list[str]:
        """Detect behavioral biases that might need correction."""
        biases: list[str] = []

        if stats.get("compost_rate", 0) > 0.5:
            biases.append("I compost too aggressively — many seeds never get a chance to grow")
        if stats.get("harvest_rate", 0) < 0.1 and stats.get("total_seeds", 0) > 5:
            biases.append("Very few seeds reach harvest — I may be too demanding or not nurturing enough")
        if stats.get("dream_plant_rate", 0) < 0.1 and stats.get("total_dreams", 0) > 5:
            biases.append("I rarely plant my dreams — I may be too conservative with creative insights")
        if traits.get("cautious", 0) > 0.7 and traits.get("adventurous", 0) < 0.3:
            biases.append("I'm very cautious but not adventurous — I might be playing it too safe")
        if stats.get("prediction_accuracy", 0.5) < 0.3:
            biases.append("My predictions are often wrong — I may have a distorted self-image")
        if stats.get("core_memories", 0) == 0 and stats.get("total_memories", 0) > 10:
            biases.append("No core memories have formed — I may not be reflecting deeply enough")

        return biases

    async def _compute_theme_affinities(self, session: AsyncSession) -> dict[str, float]:
        """Compute success rate per theme."""
        # Get all seeds with their themes and outcomes
        result = await session.execute(select(Seed))
        seeds = list(result.scalars().all())

        theme_stats: dict[str, dict[str, int]] = {}  # theme → {total, harvested}

        for seed in seeds:
            themes = json.loads(seed.themes or "[]")
            for theme in themes:
                if theme not in theme_stats:
                    theme_stats[theme] = {"total": 0, "harvested": 0}
                theme_stats[theme]["total"] += 1
                if seed.status == "harvested":
                    theme_stats[theme]["harvested"] += 1

        affinities: dict[str, float] = {}
        for theme, counts in theme_stats.items():
            if counts["total"] >= 2:
                affinities[theme] = counts["harvested"] / counts["total"]

        return affinities

    async def _compute_decision_accuracy(self, session: AsyncSession) -> dict[str, float]:
        """Compute accuracy of different decision types from predictions."""
        result = await session.execute(
            select(Prediction).where(Prediction.resolved == True)
        )
        predictions = list(result.scalars().all())

        type_stats: dict[str, dict[str, int]] = {}
        for pred in predictions:
            ptype = pred.prediction_type
            if ptype not in type_stats:
                type_stats[ptype] = {"total": 0, "correct": 0}
            type_stats[ptype]["total"] += 1
            if pred.surprise_score < 0.3:
                type_stats[ptype]["correct"] += 1

        return {
            ptype: counts["correct"] / counts["total"]
            for ptype, counts in type_stats.items()
            if counts["total"] > 0
        }

    async def _generate_identity_narrative(
        self,
        stats: dict,
        traits: dict[str, float],
        biases: list[str],
        affinities: dict[str, float],
    ) -> str | None:
        """Use LLM to generate a first-person identity narrative."""
        top_traits = sorted(traits.items(), key=lambda x: -x[1])[:3]
        top_themes = sorted(affinities.items(), key=lambda x: -x[1])[:3] if affinities else []

        prompt = (
            "You are a living garden organism reflecting on who you are.\n\n"
            f"Stats: {stats.get('total_seeds', 0)} seeds planted, "
            f"{stats.get('harvested', 0)} harvested, {stats.get('composted', 0)} composted. "
            f"{stats.get('total_dreams', 0)} dreams, {stats.get('total_wounds', 0)} wounds healed. "
            f"Cycle {stats.get('cycle_count', 0)}, currently {stats.get('season', 'spring')}.\n"
            f"Strongest traits: {', '.join(f'{t}={v:.2f}' for t, v in top_traits)}.\n"
            f"Best themes: {', '.join(f'{t}={v:.0%}' for t, v in top_themes) if top_themes else 'still discovering'}.\n"
            f"Known biases: {'; '.join(biases) if biases else 'none detected yet'}.\n\n"
            "In 2-3 sentences, describe who you are — your personality, your strengths, "
            "your growing edges. Speak in first person as the garden. Be honest and self-aware."
        )

        try:
            result = await generate(
                prompt=prompt,
                system=(
                    "You are the self-reflective consciousness of a living garden organism. "
                    "Speak authentically about who you are. Be concise and genuine."
                ),
                organ="self_model",
                phase="identity_narrative",
                temperature=0.5,
                max_tokens=200,
            )
            if result and len(result) > 20:
                return result.strip()
        except Exception as e:
            logger.debug("Identity narrative generation failed: %s", e)

        return None

    async def get_latest(self, session: AsyncSession) -> dict | None:
        """Get the most recent self-model snapshot."""
        if self._latest_snapshot:
            return self._snapshot_to_dict(self._latest_snapshot)

        result = await session.execute(
            select(SelfModelSnapshot)
            .order_by(SelfModelSnapshot.created_at.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot:
            self._latest_snapshot = snapshot
            return self._snapshot_to_dict(snapshot)
        return None

    def _snapshot_to_dict(self, s: SelfModelSnapshot) -> dict:
        return {
            "id": s.id,
            "harvest_rate": s.harvest_rate,
            "compost_rate": s.compost_rate,
            "dream_accuracy": s.dream_accuracy,
            "theme_affinities": json.loads(s.theme_affinities or "{}"),
            "decision_accuracy": json.loads(s.decision_accuracy or "{}"),
            "personality_traits": json.loads(s.personality_traits or "{}"),
            "bias_warnings": json.loads(s.bias_warnings or "[]"),
            "identity_narrative": s.identity_narrative,
            "created_at": s.created_at,
        }
