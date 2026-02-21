"""Tests for Scar Tissue — the wound-healing and resilience layer."""

import pytest

from core.healing import ScarTissue
from core.hormones import HormoneBus


@pytest.mark.asyncio
async def test_minor_wound_healing(session, bus):
    healer = ScarTissue(bus)
    wound = await healer.triage_and_heal(
        session, "apoptosis", {"sprout_id": "test_sprout", "reason": "energy_depleted"}
    )
    await session.commit()

    assert wound is not None
    assert wound.severity == "minor"
    assert wound.antifragility_gained == 0.1
    assert wound.healed_at is not None


@pytest.mark.asyncio
async def test_moderate_wound_healing(session, bus):
    healer = ScarTissue(bus)
    wound = await healer.triage_and_heal(
        session, "ethical_violation",
        {"violations": ["harm", "fairness"], "sprout_id": "test"}
    )
    await session.commit()

    assert wound is not None
    assert wound.severity == "moderate"
    assert wound.antifragility_gained == 0.3


@pytest.mark.asyncio
async def test_severe_wound_triggers_emergency_winter(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("emergency_winter", handler)

    healer = ScarTissue(bus)
    wound = await healer.triage_and_heal(
        session, "ethical_violation",
        {"violations": ["harm", "fairness", "consent"], "sprout_id": "test"}
    )
    await session.commit()

    assert wound is not None
    assert wound.severity == "severe"
    assert wound.antifragility_gained == 0.5
    assert len(received) >= 1


@pytest.mark.asyncio
async def test_healing_emits_complete_hormone(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("healing_complete", handler)

    healer = ScarTissue(bus)
    await healer.triage_and_heal(session, "apoptosis", {"sprout_id": "test"})
    await session.commit()

    assert len(received) >= 1
    assert "wound_id" in received[0].payload


@pytest.mark.asyncio
async def test_energy_famine_severity(session, bus):
    healer = ScarTissue(bus)

    # Minor famine
    wound = await healer.triage_and_heal(
        session, "energy_famine", {"depleted_count": 2}
    )
    assert wound.severity == "minor"

    # Moderate famine
    wound = await healer.triage_and_heal(
        session, "energy_famine", {"depleted_count": 7}
    )
    assert wound.severity == "moderate"

    # Severe famine
    wound = await healer.triage_and_heal(
        session, "energy_famine", {"depleted_count": 15}
    )
    assert wound.severity == "severe"
    await session.commit()
