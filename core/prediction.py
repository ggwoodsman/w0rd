"""
Prediction & Surprise Engine — The Expectation Machine

The organism makes predictions about what will happen next, then compares
reality to expectations. The gap between prediction and reality is *surprise*
— the fundamental driver of learning and consciousness.

High surprise → curiosity hormones → more dreaming, more introspection
Low surprise → confidence → less LLM usage, more efficient decisions
Prediction errors accumulate into wisdom.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import GardenState, Prediction, Seed

logger = logging.getLogger("w0rd.prediction")

# How many unresolved predictions to keep active
MAX_ACTIVE_PREDICTIONS = 20


class PredictionEngine:
    """The organism's expectation machine — predicts, observes, learns from surprise."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._cumulative_surprise = 0.0
        self._prediction_count = 0
        self._correct_count = 0

    @property
    def accuracy(self) -> float:
        if self._prediction_count == 0:
            return 0.5
        return self._correct_count / self._prediction_count

    @property
    def average_surprise(self) -> float:
        if self._prediction_count == 0:
            return 0.5
        return self._cumulative_surprise / self._prediction_count

    async def make_predictions(self, session: AsyncSession) -> list[Prediction]:
        """
        Survey the garden and make predictions about what will happen next tick.
        Called once per lifecycle tick.
        """
        # Don't accumulate too many unresolved predictions
        active_count = await session.execute(
            select(func.count(Prediction.id)).where(Prediction.resolved == False)
        )
        if (active_count.scalar() or 0) >= MAX_ACTIVE_PREDICTIONS:
            return []

        predictions: list[Prediction] = []

        # Predict seed outcomes
        seed_preds = await self._predict_seed_outcomes(session)
        predictions.extend(seed_preds)

        # Predict energy trends
        energy_pred = await self._predict_energy_trend(session)
        if energy_pred:
            predictions.append(energy_pred)

        for p in predictions:
            session.add(p)

        if predictions:
            await session.flush()
            logger.info("Made %d predictions", len(predictions))

        return predictions

    async def resolve_predictions(self, session: AsyncSession) -> list[dict]:
        """
        Check unresolved predictions against reality.
        Returns list of resolved predictions with surprise scores.
        """
        result = await session.execute(
            select(Prediction).where(Prediction.resolved == False)
        )
        unresolved = list(result.scalars().all())

        resolved: list[dict] = []
        total_surprise = 0.0

        for pred in unresolved:
            outcome = await self._check_outcome(session, pred)
            if outcome is None:
                continue  # Not yet resolvable

            pred.actual_outcome = outcome["actual"]
            pred.surprise_score = outcome["surprise"]
            pred.resolved = True
            pred.resolved_at = time.time()

            self._prediction_count += 1
            self._cumulative_surprise += outcome["surprise"]
            if outcome["correct"]:
                self._correct_count += 1

            total_surprise += outcome["surprise"]

            resolved.append({
                "prediction_id": pred.id,
                "type": pred.prediction_type,
                "predicted": pred.predicted_outcome,
                "actual": outcome["actual"],
                "surprise": outcome["surprise"],
                "correct": outcome["correct"],
            })

        await session.flush()

        # Emit surprise signal if significant
        if resolved and total_surprise > 0:
            avg_surprise = total_surprise / len(resolved)
            if avg_surprise > 0.5:
                await self.bus.signal(
                    "high_surprise",
                    payload={
                        "average_surprise": round(avg_surprise, 3),
                        "resolved_count": len(resolved),
                        "accuracy": round(self.accuracy, 3),
                    },
                    emitter="prediction",
                )
                logger.info("High surprise! avg=%.2f across %d predictions", avg_surprise, len(resolved))
            elif avg_surprise < 0.2:
                await self.bus.signal(
                    "low_surprise",
                    payload={
                        "average_surprise": round(avg_surprise, 3),
                        "accuracy": round(self.accuracy, 3),
                    },
                    emitter="prediction",
                )

        if resolved:
            logger.info(
                "Resolved %d predictions (accuracy=%.1f%%, avg_surprise=%.2f)",
                len(resolved), self.accuracy * 100, self.average_surprise,
            )

        return resolved

    async def _predict_seed_outcomes(self, session: AsyncSession) -> list[Prediction]:
        """Predict what will happen to currently growing seeds."""
        result = await session.execute(
            select(Seed).where(
                Seed.is_composted == False,
                Seed.status.in_(["planted", "growing"]),
            )
        )
        seeds = list(result.scalars().all())
        predictions = []

        for seed in seeds[:3]:  # Limit predictions per tick
            # Check if we already have an active prediction for this seed
            existing = await session.execute(
                select(Prediction).where(
                    Prediction.subject_id == seed.id,
                    Prediction.resolved == False,
                    Prediction.prediction_type == "seed_outcome",
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Heuristic prediction
            age = time.time() - (seed.created_at or time.time())
            if seed.energy > 15 and age > 120:
                predicted = "harvest"
                confidence = min(0.5 + seed.energy / 50, 0.9)
            elif seed.energy < 2 and age > 200:
                predicted = "compost"
                confidence = min(0.4 + (300 - age) / 500, 0.8)
            elif seed.status == "planted" and age < 60:
                predicted = "growing"
                confidence = 0.7
            else:
                predicted = "continue"
                confidence = 0.5

            predictions.append(Prediction(
                prediction_type="seed_outcome",
                subject_id=seed.id,
                predicted_outcome=predicted,
                confidence=round(confidence, 3),
            ))

        return predictions

    async def _predict_energy_trend(self, session: AsyncSession) -> Prediction | None:
        """Predict whether total garden energy will increase or decrease."""
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if not state:
            return None

        # Check if we already have an active energy prediction
        existing = await session.execute(
            select(Prediction).where(
                Prediction.prediction_type == "energy_trend",
                Prediction.resolved == False,
            )
        )
        if existing.scalar_one_or_none():
            return None

        # Count living seeds (more seeds = more photosynthesis = energy up)
        seed_count = await session.execute(
            select(func.count(Seed.id)).where(
                Seed.is_composted == False,
                Seed.status.in_(["planted", "growing"]),
            )
        )
        living = seed_count.scalar() or 0

        season = state.season
        current_energy = state.total_energy

        if season in ("spring", "summer") and living > 2:
            predicted = "increase"
            confidence = 0.6
        elif season == "winter" or living == 0:
            predicted = "decrease"
            confidence = 0.7
        else:
            predicted = "stable"
            confidence = 0.4

        return Prediction(
            prediction_type="energy_trend",
            subject_id="garden",
            predicted_outcome=f"{predicted}|{round(current_energy, 1)}",
            confidence=round(confidence, 3),
        )

    async def _check_outcome(self, session: AsyncSession, pred: Prediction) -> dict | None:
        """Check if a prediction can be resolved and compute surprise."""
        if pred.prediction_type == "seed_outcome":
            return await self._check_seed_outcome(session, pred)
        elif pred.prediction_type == "energy_trend":
            return await self._check_energy_trend(session, pred)
        return None

    async def _check_seed_outcome(self, session: AsyncSession, pred: Prediction) -> dict | None:
        """Check seed outcome prediction."""
        result = await session.execute(select(Seed).where(Seed.id == pred.subject_id))
        seed = result.scalar_one_or_none()
        if not seed:
            return {"actual": "disappeared", "surprise": 0.8, "correct": False}

        # Only resolve if seed has changed state since prediction
        age_since_prediction = time.time() - pred.created_at
        if age_since_prediction < 60:  # Wait at least 1 tick
            return None

        actual = seed.status
        predicted = pred.predicted_outcome

        if actual == predicted:
            surprise = max(0.0, 0.2 - pred.confidence * 0.2)
            return {"actual": actual, "surprise": round(surprise, 3), "correct": True}
        else:
            # Surprise proportional to confidence in wrong prediction
            surprise = min(pred.confidence * 0.8 + 0.2, 1.0)
            return {"actual": actual, "surprise": round(surprise, 3), "correct": False}

    async def _check_energy_trend(self, session: AsyncSession, pred: Prediction) -> dict | None:
        """Check energy trend prediction."""
        age = time.time() - pred.created_at
        if age < 60:
            return None

        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if not state:
            return None

        parts = pred.predicted_outcome.split("|")
        predicted_direction = parts[0]
        old_energy = float(parts[1]) if len(parts) > 1 else 100.0
        current_energy = state.total_energy

        delta = current_energy - old_energy
        if delta > 2:
            actual = "increase"
        elif delta < -2:
            actual = "decrease"
        else:
            actual = "stable"

        correct = actual == predicted_direction
        if correct:
            surprise = max(0.0, 0.15 - pred.confidence * 0.15)
        else:
            surprise = min(pred.confidence * 0.7 + 0.3, 1.0)

        return {
            "actual": f"{actual}|{round(current_energy, 1)}",
            "surprise": round(surprise, 3),
            "correct": correct,
        }

    def get_stats(self) -> dict:
        """Return prediction engine statistics."""
        return {
            "total_predictions": self._prediction_count,
            "accuracy": round(self.accuracy, 3),
            "average_surprise": round(self.average_surprise, 3),
            "correct_count": self._correct_count,
        }
