"""Tests for the Vascular Grower — the branching tissue."""

import json
import math

import pytest

from core.fractal import PHI, VascularGrower, _phi_weight, _pressure_score
from core.hormones import HormoneBus
from core.intent import SeedListener


def test_phi_constant():
    assert abs(PHI - 1.6180339887) < 0.0001


def test_phi_weight_diminishes():
    w0 = _phi_weight(0, 10.0)
    w1 = _phi_weight(1, 10.0)
    w2 = _phi_weight(2, 10.0)
    assert w0 > w1 > w2 > 0


def test_pressure_score_range():
    p = _pressure_score(0, 0, 2)
    assert 0 < p <= 1.0
    p_deep = _pressure_score(3, 0, 2)
    assert p_deep < p  # deeper = lower pressure score


@pytest.mark.asyncio
async def test_grow_creates_sprouts(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "I want to create beautiful art and share it")
    await session.flush()

    grower = VascularGrower(bus)
    sprouts = await grower.grow(session, seed)
    await session.commit()

    assert len(sprouts) > 0
    assert seed.status == "growing"

    # Check tree structure
    depths = {s.depth for s in sprouts}
    assert 0 in depths  # at least root level


@pytest.mark.asyncio
async def test_grow_respects_energy_budget(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "tiny wish")
    seed.energy = 0.5  # very low energy
    await session.flush()

    grower = VascularGrower(bus, max_depth=3)
    sprouts = await grower.grow(session, seed)
    await session.commit()

    # Should produce fewer sprouts due to low energy
    assert len(sprouts) < 20


@pytest.mark.asyncio
async def test_grow_emits_hormone(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("tree_grown", handler)

    listener = SeedListener(bus)
    seed = await listener.listen(session, "I want to grow and learn")
    await session.flush()

    grower = VascularGrower(bus)
    await grower.grow(session, seed)
    await session.commit()

    assert len(received) == 1
    assert received[0].payload["seed_id"] == seed.id
    assert received[0].payload["sprout_count"] > 0


@pytest.mark.asyncio
async def test_apoptosis(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "test apoptosis")
    await session.flush()

    grower = VascularGrower(bus)
    sprouts = await grower.grow(session, seed)
    await session.flush()

    target = sprouts[0]
    await grower.trigger_apoptosis(session, target, reason="test")
    await session.commit()

    assert target.status == "composted"
    assert target.is_composted is True
    assert target.apoptosis_at is not None
