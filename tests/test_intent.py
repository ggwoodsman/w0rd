"""Tests for the Seed Listener — the sensory membrane."""

import json

import pytest

from core.hormones import HormoneBus
from core.intent import SeedListener, _detect_themes, _detect_tone, _extract_essence, _tokenize


def test_tokenize():
    tokens = _tokenize("I want to CREATE something Beautiful!")
    assert "create" in tokens
    assert "beautiful" in tokens
    assert "i" in tokens


def test_extract_essence():
    assert _extract_essence("I want to heal the world. And dance.") == "I want to heal the world"
    assert _extract_essence("short") == "short"


def test_detect_themes_creativity():
    tokens = _tokenize("I want to create art and design something beautiful")
    themes = _detect_themes(tokens)
    assert "creativity" in themes


def test_detect_themes_connection():
    tokens = _tokenize("I want to connect with my community and share love")
    themes = _detect_themes(tokens)
    assert "connection" in themes


def test_detect_themes_with_pheromone_bias():
    tokens = _tokenize("I want something new")
    themes_no_bias = _detect_themes(tokens)
    themes_biased = _detect_themes(tokens, pheromone_bias={"health": 5.0})
    assert "health" in themes_biased


def test_detect_tone_positive():
    tokens = _tokenize("I feel joy and love and hope")
    valence, arousal = _detect_tone(tokens)
    assert valence > 0


def test_detect_tone_negative():
    tokens = _tokenize("I feel pain and fear and loneliness")
    valence, arousal = _detect_tone(tokens)
    assert valence < 0


def test_detect_tone_high_arousal():
    tokens = _tokenize("urgent passionate burning intense")
    valence, arousal = _detect_tone(tokens)
    assert arousal > 0.5


@pytest.mark.asyncio
async def test_seed_listener_creates_seed(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "I want to grow a beautiful garden of ideas")
    await session.commit()

    assert seed.id is not None
    assert seed.essence != ""
    assert seed.energy > 0
    themes = json.loads(seed.themes)
    assert len(themes) > 0
    assert seed.status == "planted"


@pytest.mark.asyncio
async def test_seed_listener_emits_hormone(session, bus):
    received = []

    async def handler(h):
        received.append(h)

    bus.subscribe("seed_planted", handler)
    listener = SeedListener(bus)
    await listener.listen(session, "I dream of creating something wonderful")
    await session.commit()

    assert len(received) == 1
    assert "seed_id" in received[0].payload
