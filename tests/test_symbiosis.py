"""Tests for the Mycelial Network — the underground intelligence."""

import json

import pytest

from core.hormones import HormoneBus
from core.symbiosis import MycelialNetwork, _cosine_similarity, _theme_overlap
from models.db_models import Seed


def test_cosine_similarity_identical():
    assert abs(_cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001


def test_cosine_similarity_orthogonal():
    assert abs(_cosine_similarity([1, 0, 0], [0, 1, 0])) < 0.001


def test_cosine_similarity_empty():
    assert _cosine_similarity([], []) == 0.0


def test_theme_overlap_full():
    assert _theme_overlap(["a", "b"], ["a", "b"]) == 1.0


def test_theme_overlap_partial():
    overlap = _theme_overlap(["a", "b", "c"], ["b", "c", "d"])
    assert 0 < overlap < 1


def test_theme_overlap_none():
    assert _theme_overlap(["a"], ["b"]) == 0.0


@pytest.mark.asyncio
async def test_scan_and_link_with_similar_seeds(session, bus):
    seed_a = Seed(
        raw_text="I want to create art",
        essence="create art",
        themes=json.dumps(["creativity", "growth"]),
        embedding=json.dumps([0.5, 0.3, 0.8]),
    )
    seed_b = Seed(
        raw_text="I want to design beautiful things",
        essence="design beauty",
        themes=json.dumps(["creativity", "nature"]),
        embedding=json.dumps([0.4, 0.35, 0.75]),
    )
    session.add_all([seed_a, seed_b])
    await session.commit()

    network = MycelialNetwork(bus)
    links = await network.scan_and_link(session)
    await session.commit()

    assert len(links) >= 1
    assert links[0].relationship_type in ("mutualism", "commensalism", "parasitism")


@pytest.mark.asyncio
async def test_scan_no_links_for_dissimilar(session, bus):
    seed_a = Seed(
        raw_text="math equations",
        essence="math",
        themes=json.dumps(["wisdom"]),
        embedding=json.dumps([1.0, 0.0, 0.0]),
    )
    seed_b = Seed(
        raw_text="ocean swimming",
        essence="swim",
        themes=json.dumps(["health"]),
        embedding=json.dumps([0.0, 0.0, 1.0]),
    )
    session.add_all([seed_a, seed_b])
    await session.commit()

    network = MycelialNetwork(bus)
    links = await network.scan_and_link(session)
    await session.commit()

    # Orthogonal embeddings + no theme overlap = no link
    assert len(links) == 0


@pytest.mark.asyncio
async def test_quorum_sensing(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("quorum_reached", handler)

    for i in range(4):
        session.add(Seed(
            raw_text=f"creative seed {i}",
            essence=f"creative {i}",
            themes=json.dumps(["creativity"]),
        ))
    await session.commit()

    network = MycelialNetwork(bus)
    quorum_themes = await network.check_quorum(session)

    assert "creativity" in quorum_themes
    assert len(received) >= 1


@pytest.mark.asyncio
async def test_pollination(session, bus):
    completed = Seed(
        raw_text="completed creative seed",
        essence="completed",
        themes=json.dumps(["creativity", "growth"]),
        status="harvested",
    )
    living = Seed(
        raw_text="living seed with partial overlap",
        essence="living",
        themes=json.dumps(["creativity", "health"]),
        energy=5.0,
        status="growing",
    )
    session.add_all([completed, living])
    await session.commit()

    network = MycelialNetwork(bus)
    count = await network.pollinate(session, completed)
    await session.commit()

    assert count >= 1
    assert living.energy > 5.0  # got a pollen boost
