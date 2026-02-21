"""
Scar Tissue — The Wound-Healing and Resilience Layer

Listens for damage signals (ethical violations, energy famine, apoptosis),
triages wounds by severity, applies healing responses, and builds
anti-fragility through scar memory.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import Hormone, HormoneBus
from models.db_models import GardenState, Sprout, WoundRecord

logger = logging.getLogger("w0rd.healing")


class ScarTissue:
    """The organism's wound-response and resilience layer."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._register_listeners()

    def _register_listeners(self) -> None:
        self.bus.subscribe("ethical_violation", self._on_wound)
        self.bus.subscribe("energy_famine", self._on_wound)
        self.bus.subscribe("apoptosis", self._on_wound)

    async def _on_wound(self, hormone: Hormone) -> None:
        """
        Receive a wound signal and queue it for processing.
        Actual healing requires a DB session, so we emit a follow-up hormone.
        """
        await self.bus.signal(
            "wound_detected",
            payload={
                "source_hormone": hormone.name,
                "original_payload": hormone.payload,
            },
            emitter="healing",
            parent_depth=hormone.depth,
        )

    async def triage_and_heal(self, session: AsyncSession, wound_hormone: str, payload: dict) -> WoundRecord | None:
        """
        Full wound processing: triage → heal → record scar.
        Called from the API layer with a live session.
        """
        severity = self._classify_severity(wound_hormone, payload)
        affected_ids = self._extract_affected_ids(payload)

        healing_action, scar_lesson = await self._apply_healing(
            session, severity, wound_hormone, payload
        )

        antifragility = self._calculate_antifragility_gain(severity)

        wound = WoundRecord(
            wound_type=wound_hormone,
            severity=severity,
            source_hormone=wound_hormone,
            affected_ids=str(affected_ids),
            healing_action=healing_action,
            scar_lesson=scar_lesson,
            antifragility_gained=antifragility,
            healed_at=time.time(),
        )
        session.add(wound)

        # Update garden antifragility
        result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
        state = result.scalar_one_or_none()
        if state:
            state.antifragility_score += antifragility

        await session.flush()

        await self.bus.signal(
            "healing_complete",
            payload={
                "wound_id": wound.id,
                "severity": severity,
                "antifragility_gained": antifragility,
            },
            emitter="healing",
        )

        logger.info("Healed %s wound (severity=%s, antifragility+%.2f)", wound_hormone, severity, antifragility)
        return wound

    def _classify_severity(self, wound_type: str, payload: dict) -> str:
        """Triage: minor, moderate, or severe."""
        if wound_type == "apoptosis":
            return "minor"
        elif wound_type == "ethical_violation":
            violations = payload.get("violations", [])
            if len(violations) >= 3:
                return "severe"
            elif len(violations) >= 2:
                return "moderate"
            return "minor"
        elif wound_type == "energy_famine":
            depleted = payload.get("depleted_count", 0)
            if depleted >= 10:
                return "severe"
            elif depleted >= 5:
                return "moderate"
            return "minor"
        return "minor"

    def _extract_affected_ids(self, payload: dict) -> list[str]:
        ids = []
        for key in ["sprout_id", "seed_id"]:
            if key in payload:
                ids.append(payload[key])
        return ids

    async def _apply_healing(
        self, session: AsyncSession, severity: str, wound_type: str, payload: dict
    ) -> tuple[str, str]:
        """Apply healing response based on severity. Returns (action, lesson)."""

        if severity == "minor":
            action = "Redistributed energy from healthy neighbors; logged lesson"
            lesson = f"Minor {wound_type}: resilience through local redistribution"

        elif severity == "moderate":
            action = "Pruned damaged branch; strengthened ethical antibodies; redistributed freed energy"
            lesson = f"Moderate {wound_type}: pruning creates space for healthier growth"

            # Prune affected sprouts
            sprout_id = payload.get("sprout_id")
            if sprout_id:
                result = await session.execute(select(Sprout).where(Sprout.id == sprout_id))
                sprout = result.scalar_one_or_none()
                if sprout:
                    sprout.status = "wilting"
                    await session.flush()

        elif severity == "severe":
            action = "Triggered emergency winter; forced dormancy; consolidating for spring rebuild"
            lesson = f"Severe {wound_type}: emergency dormancy protects the whole organism"

            await self.bus.signal(
                "emergency_winter",
                payload={"reason": wound_type, "severity": severity},
                emitter="healing",
            )

        else:
            action = "Observed and logged"
            lesson = "Unknown wound type — observation recorded"

        return action, lesson

    def _calculate_antifragility_gain(self, severity: str) -> float:
        """More severe wounds, once healed, grant more anti-fragility."""
        gains = {"minor": 0.1, "moderate": 0.3, "severe": 0.5}
        return gains.get(severity, 0.05)
