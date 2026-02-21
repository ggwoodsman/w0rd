"""Tests for the Dreaming Engine — the subconscious."""

import json

import pytest

from core.dreaming import DreamingEngine, _centroid, _generate_insight, _perplexity, _perturb
from core.hormones import HormoneBus
from models.db_models import Seed


def test_centroid():
    vectors = [[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]]
    c = _centroid(vectors)
    assert len(c) == 3
    assert abs(c[0] - 2.0) < 0.001
    assert abs(c[1] - 2.0) < 0.001


def test_centroid_empty():
    assert _centroid([]) == []


def test_perturb_changes_vector():
    v = [1.0, 2.0, 3.0]
    p = _perturb(v, temperature=1.0)
    assert len(p) == 3
    # With temperature > 0, at least one value should differ
    assert any(abs(a - b) > 0.0001 for a, b in zip(v, p))


def test_perplexity_identical():
    v = [1.0, 2.0, 3.0]
    assert _perplexity(v, v) == 0.0


def test_perplexity_different():
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    p = _perplexity(v1, v2)
    assert p > 0


def test_generate_insight_single_theme():
    insight = _generate_insight(["creativity"], 0.5)
    assert len(insight) > 0
    assert "creativity" in insight.lower()


def test_generate_insight_multiple_themes():
    insight = _generate_insight(["creativity", "connection", "health"], 0.7)
    assert len(insight) > 0


def test_generate_insight_empty():
    insight = _generate_insight([], 0.5)
    assert "quiet" in insight.lower() or "potential" in insight.lower()


@pytest.mark.asyncio
async def test_dream_returns_none_without_material(session, bus):
    dreamer = DreamingEngine(bus)
    dream = await dreamer.dream(session)
    assert dream is None  # no completed seeds yet


@pytest.mark.asyncio
async def test_dream_with_completed_seeds(session, bus):
    # Create some completed seeds
    for i in range(3):
        seed = Seed(
            raw_text=f"test seed {i}",
            essence=f"essence {i}",
            themes=json.dumps(["creativity", "growth"]),
            status="harvested",
        )
        session.add(seed)
    await session.commit()

    dreamer = DreamingEngine(bus)
    dream = await dreamer.dream(session)
    await session.commit()

    assert dream is not None
    assert dream.insight != ""
    assert dream.planted is False


@pytest.mark.asyncio
async def test_plant_dream(session, bus):
    seed = Seed(
        raw_text="completed seed",
        essence="completed",
        themes=json.dumps(["wisdom"]),
        status="harvested",
    )
    session.add(seed)
    await session.commit()

    dreamer = DreamingEngine(bus)
    dream = await dreamer.dream(session)
    await session.commit()

    assert dream is not None

    new_seed = await dreamer.plant_dream(session, dream.id)
    await session.commit()

    assert new_seed is not None
    assert new_seed.status == "planted"
    assert dream.planted is True


@pytest.mark.asyncio
async def test_dream_emits_hormone(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("dream_generated", handler)
    bus.subscribe("lucid_dream", handler)

    seed = Seed(
        raw_text="dream material",
        essence="material",
        themes=json.dumps(["nature"]),
        status="harvested",
    )
    session.add(seed)
    await session.commit()

    dreamer = DreamingEngine(bus)
    await dreamer.dream(session)
    await session.commit()

    assert len(received) >= 1
