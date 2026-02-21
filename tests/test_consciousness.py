"""Tests for Consciousness Pulse — self-awareness."""

import json

import pytest

from core.consciousness import ConsciousnessPulse
from core.hormones import HormoneBus
from models.db_models import Seed


@pytest.mark.asyncio
async def test_pulse_generates_report(session, bus):
    pulse = ConsciousnessPulse(bus)
    report = await pulse.pulse(session)
    await session.commit()

    assert report is not None
    assert report.summary != ""
    assert report.cycle >= 0


@pytest.mark.asyncio
async def test_pulse_detects_thriving(session, bus):
    seed = Seed(
        raw_text="thriving seed",
        essence="thriving",
        themes=json.dumps(["growth"]),
        energy=20.0,
        status="growing",
    )
    session.add(seed)
    await session.commit()

    pulse = ConsciousnessPulse(bus)
    report = await pulse.pulse(session)
    await session.commit()

    thriving = json.loads(report.thriving)
    assert len(thriving) >= 1


@pytest.mark.asyncio
async def test_pulse_detects_struggling(session, bus):
    seed = Seed(
        raw_text="struggling seed",
        essence="struggling",
        themes=json.dumps(["health"]),
        energy=1.0,
        status="growing",
    )
    session.add(seed)
    await session.commit()

    pulse = ConsciousnessPulse(bus)
    report = await pulse.pulse(session)
    await session.commit()

    struggling = json.loads(report.struggling)
    assert len(struggling) >= 1


@pytest.mark.asyncio
async def test_pulse_summary_mentions_season(session, bus):
    pulse = ConsciousnessPulse(bus)
    report = await pulse.pulse(session)
    await session.commit()

    assert "spring" in report.summary.lower() or "garden" in report.summary.lower()


@pytest.mark.asyncio
async def test_pulse_emits_hormone(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("pulse_generated", handler)

    pulse = ConsciousnessPulse(bus)
    await pulse.pulse(session)
    await session.commit()

    assert len(received) >= 1
    assert "report_id" in received[0].payload
