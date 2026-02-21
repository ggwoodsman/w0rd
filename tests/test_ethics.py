"""Tests for Immune Wisdom — the adaptive ethical immune system."""

import pytest

from core.ethics import ImmuneWisdom
from core.fractal import VascularGrower
from core.hormones import HormoneBus
from core.intent import SeedListener
from models.db_models import Sprout


@pytest.mark.asyncio
async def test_clean_sprout_passes(session, bus):
    immune = ImmuneWisdom(bus)
    sprout = Sprout(
        seed_id="test", label="goal_0_0",
        description="Create a beautiful garden of kindness",
        energy=5.0,
    )
    session.add(sprout)
    await session.flush()

    passed = await immune.evaluate_and_act(session, sprout)
    assert passed is True
    assert sprout.ethical_score > 0.5


@pytest.mark.asyncio
async def test_harmful_sprout_blocked(session, bus):
    immune = ImmuneWisdom(bus)
    sprout = Sprout(
        seed_id="test", label="bad_0_0",
        description="destroy and kill and attack with violence",
        energy=5.0,
    )
    session.add(sprout)
    await session.flush()

    passed = await immune.evaluate_and_act(session, sprout)
    assert passed is False


@pytest.mark.asyncio
async def test_ethical_scoring_dimensions(session, bus):
    immune = ImmuneWisdom(bus)
    sprout = Sprout(
        seed_id="test", label="mixed_0_0",
        description="share truth with gentle honesty",
        energy=5.0,
    )
    session.add(sprout)
    await session.flush()

    scores = await immune.score(session, sprout)
    assert "harm" in scores
    assert "fairness" in scores
    assert "kindness" in scores
    assert "truthfulness" in scores
    assert all(0 <= v <= 1 for v in scores.values())


@pytest.mark.asyncio
async def test_ethical_violation_emits_hormone(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("ethical_violation", handler)

    immune = ImmuneWisdom(bus)
    sprout = Sprout(
        seed_id="test", label="violent_0_0",
        description="destroy everything with violence and abuse",
        energy=5.0,
    )
    session.add(sprout)
    await session.flush()

    await immune.evaluate_and_act(session, sprout)
    assert len(received) >= 1
    assert "violations" in received[0].payload
