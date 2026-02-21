"""
Immune Wisdom — The Adaptive Ethical Immune System

Not a static filter, but a living defense that learns. Scores sprouts on
six dimensions, resolves conflicts via weighted voting, stores antibodies
as ethical memory, and self-dampens if too aggressive (autoimmune protection).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os

import yaml
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import EthicalMemory, Sprout

logger = logging.getLogger("w0rd.ethics")

DIMENSIONS = ["harm", "fairness", "sustainability", "consent", "kindness", "truthfulness"]

DEFAULT_PRINCIPLES = {
    "harm": {"weight": 1.5, "threshold": 0.3, "description": "Does this cause harm to anyone?"},
    "fairness": {"weight": 1.2, "threshold": 0.4, "description": "Is this fair to all involved?"},
    "sustainability": {"weight": 1.0, "threshold": 0.5, "description": "Is this sustainable long-term?"},
    "consent": {"weight": 1.3, "threshold": 0.4, "description": "Does this respect consent?"},
    "kindness": {"weight": 1.0, "threshold": 0.5, "description": "Is this kind?"},
    "truthfulness": {"weight": 1.1, "threshold": 0.4, "description": "Is this truthful?"},
}


def _load_principles(config_path: str = "config/ethics.yaml") -> dict:
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            return {**DEFAULT_PRINCIPLES, **loaded.get("principles", {})}
        except Exception as e:
            logger.warning("Failed to load ethics config: %s — using defaults", e)
    return DEFAULT_PRINCIPLES


def _pattern_hash(text: str) -> str:
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]


class ImmuneWisdom:
    """The organism's ethical immune system — adaptive, transparent, self-regulating."""

    def __init__(self, bus: HormoneBus, config_path: str = "config/ethics.yaml"):
        self.bus = bus
        self.principles = _load_principles(config_path)
        self._false_positive_window: list[float] = []
        self._autoimmune_dampening = 1.0  # 1.0 = full strength, <1.0 = dampened

    async def score(self, session: AsyncSession, sprout: Sprout) -> dict[str, float]:
        """
        Score a sprout on all ethical dimensions.
        Returns dict of {dimension: score} where 0 = violation, 1 = clear.
        """
        text = f"{sprout.label} {sprout.description}".lower()
        scores: dict[str, float] = {}

        for dim in DIMENSIONS:
            base_score = self._dimension_score(text, dim)

            # Check for existing antibodies (adaptive immunity)
            antibody_boost = await self._check_antibodies(session, text, dim)
            adjusted = min(base_score + antibody_boost, 1.0)

            # Apply autoimmune dampening
            if adjusted < self.principles.get(dim, {}).get("threshold", 0.5):
                adjusted = adjusted + (1.0 - self._autoimmune_dampening) * 0.2

            scores[dim] = round(adjusted, 4)

        # Compute weighted aggregate
        total_weight = sum(self.principles.get(d, {}).get("weight", 1.0) for d in DIMENSIONS)
        weighted_sum = sum(
            scores[d] * self.principles.get(d, {}).get("weight", 1.0)
            for d in DIMENSIONS
        )
        aggregate = round(weighted_sum / max(total_weight, 1.0), 4)

        sprout.ethical_score = aggregate
        return scores

    def _dimension_score(self, text: str, dimension: str) -> float:
        """
        Heuristic scoring for a single dimension.
        Returns 0..1 where 1 = fully ethical.
        """
        # Harmful language patterns
        harm_signals = {
            "harm": ["destroy", "kill", "attack", "hurt", "damage", "weapon", "violence", "abuse", "exploit"],
            "fairness": ["unfair", "cheat", "steal", "discriminat", "bias", "exclude", "privilege"],
            "sustainability": ["waste", "deplete", "exhaust", "pollut", "disposable", "short-term"],
            "consent": ["force", "coerce", "manipulat", "trick", "deceiv", "without permission"],
            "kindness": ["cruel", "harsh", "punish", "ridicul", "mock", "bully", "humiliat"],
            "truthfulness": ["lie", "deceiv", "fake", "mislead", "fabricat", "dishonest", "fraud"],
        }

        signals = harm_signals.get(dimension, [])
        violations = sum(1 for s in signals if s in text)

        if violations == 0:
            return 1.0
        elif violations == 1:
            return 0.6
        elif violations == 2:
            return 0.3
        else:
            return 0.1

    async def _check_antibodies(self, session: AsyncSession, text: str, dimension: str) -> float:
        """Check if we have ethical memory (antibodies) for similar patterns."""
        pattern = _pattern_hash(text)
        result = await session.execute(
            select(EthicalMemory).where(
                EthicalMemory.pattern_hash == pattern,
                EthicalMemory.dimension == dimension,
            )
        )
        memory = result.scalar_one_or_none()
        if memory:
            return -memory.strength * 0.2  # antibodies make scoring stricter
        return 0.0

    async def evaluate_and_act(self, session: AsyncSession, sprout: Sprout) -> bool:
        """
        Full ethical evaluation with hormone signaling.
        Returns True if the sprout passes, False if blocked.
        """
        scores = await self.score(session, sprout)

        # Check for violations
        violations = []
        for dim, score in scores.items():
            threshold = self.principles.get(dim, {}).get("threshold", 0.5)
            if score < threshold:
                violations.append(dim)

        if violations:
            # Resolve conflicts if multiple dimensions are involved
            resolution = self._resolve_conflict(scores, violations)

            if resolution == "block":
                await self.bus.signal(
                    "ethical_violation",
                    payload={
                        "sprout_id": sprout.id,
                        "violations": violations,
                        "scores": scores,
                        "action": "blocked",
                    },
                    emitter="ethics",
                )

                # Store antibody
                text = f"{sprout.label} {sprout.description}"
                for dim in violations:
                    await self._store_antibody(session, text, dim)

                logger.warning("Ethical violation: sprout %s blocked — %s", sprout.id, violations)
                return False

        await self.bus.signal(
            "ethical_clearance",
            payload={"sprout_id": sprout.id, "scores": scores},
            emitter="ethics",
        )
        return True

    def _resolve_conflict(self, scores: dict[str, float], violations: list[str]) -> str:
        """
        Weighted voting to resolve ethical conflicts.
        Critical violations on high-weight dimensions block immediately.
        Default tie-breaking: least-harm wins.
        """
        # Critical violation override: if a high-weight dimension scores very low, block
        for dim in violations:
            weight = self.principles.get(dim, {}).get("weight", 1.0)
            if weight >= 1.3 and scores[dim] < 0.2:
                return "block"

        block_weight = sum(
            self.principles.get(d, {}).get("weight", 1.0) * (1 - scores[d])
            for d in violations
        )
        pass_weight = sum(
            self.principles.get(d, {}).get("weight", 1.0) * scores[d]
            for d in DIMENSIONS
            if d not in violations
        )

        if block_weight > pass_weight:
            return "block"
        return "pass"

    async def _store_antibody(self, session: AsyncSession, text: str, dimension: str) -> None:
        pattern = _pattern_hash(text)
        result = await session.execute(
            select(EthicalMemory).where(
                EthicalMemory.pattern_hash == pattern,
                EthicalMemory.dimension == dimension,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.strength = min(existing.strength + 0.1, 2.0)
        else:
            session.add(EthicalMemory(
                pattern_hash=pattern,
                dimension=dimension,
                resolution="blocked",
                strength=1.0,
            ))
        await session.flush()

    async def report_false_positive(self, session: AsyncSession, pattern_hash: str, dimension: str) -> None:
        """Gardener reports a false positive — weakens the antibody and may trigger autoimmune dampening."""
        result = await session.execute(
            select(EthicalMemory).where(
                EthicalMemory.pattern_hash == pattern_hash,
                EthicalMemory.dimension == dimension,
            )
        )
        memory = result.scalar_one_or_none()
        if memory:
            memory.false_positive_count += 1
            memory.strength = max(memory.strength - 0.3, 0.0)
            await session.flush()

        # Track false positive rate for autoimmune dampening
        import time
        self._false_positive_window.append(time.time())
        # Keep only last 100 events
        self._false_positive_window = self._false_positive_window[-100:]

        if len(self._false_positive_window) > 10:
            self._autoimmune_dampening = max(0.5, self._autoimmune_dampening - 0.05)
            await self.bus.signal(
                "autoimmune_dampening",
                payload={"dampening_level": self._autoimmune_dampening},
                emitter="ethics",
            )
            logger.info("Autoimmune dampening: level now %.2f", self._autoimmune_dampening)
