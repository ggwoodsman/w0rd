"""Tests for Phloem & Mycorrhizal Flow — the circulatory system."""

import pytest

from core.energy import EnergyOrgan
from core.fractal import VascularGrower
from core.hormones import HormoneBus
from core.intent import SeedListener


@pytest.mark.asyncio
async def test_photosynthesis_adds_energy(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "I want to grow strong")
    initial_energy = seed.energy
    await session.flush()

    organ = EnergyOrgan(bus)
    gained = await organ.photosynthesize(session, seed, attention_seconds=5.0)
    await session.commit()

    assert gained > 0
    assert seed.energy > initial_energy


@pytest.mark.asyncio
async def test_entropy_decay(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "test entropy")
    await session.flush()

    grower = VascularGrower(bus)
    sprouts = await grower.grow(session, seed)
    initial_energies = [s.energy for s in sprouts]
    await session.flush()

    organ = EnergyOrgan(bus)
    await organ.apply_entropy(session, season="summer")
    await session.commit()

    for s, initial in zip(sprouts, initial_energies):
        assert s.energy <= initial


@pytest.mark.asyncio
async def test_entropy_slower_in_winter(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "test winter decay")
    await session.flush()

    grower = VascularGrower(bus)
    sprouts = await grower.grow(session, seed)
    await session.flush()

    organ = EnergyOrgan(bus, decay_rate=0.1)

    # Summer decay
    summer_sprout = sprouts[0]
    summer_before = summer_sprout.energy
    await organ.apply_entropy(session, season="summer")
    summer_loss = summer_before - summer_sprout.energy

    # Reset
    summer_sprout.energy = summer_before
    await session.flush()

    # Winter decay
    await organ.apply_entropy(session, season="winter")
    winter_loss = summer_before - summer_sprout.energy

    assert winter_loss < summer_loss


@pytest.mark.asyncio
async def test_tidal_coefficient_range(bus):
    organ = EnergyOrgan(bus)
    coeff = organ._tidal_coefficient()
    assert 0.5 <= coeff <= 1.5


@pytest.mark.asyncio
async def test_phloem_distribute(session, bus):
    listener = SeedListener(bus)
    seed = await listener.listen(session, "I want to create and share beauty")
    seed.energy = 50.0
    await session.flush()

    grower = VascularGrower(bus)
    sprouts = await grower.grow(session, seed)
    await session.flush()

    organ = EnergyOrgan(bus)
    await organ.phloem_distribute(session, seed)
    await session.commit()

    # Seed should have less energy after distribution
    assert seed.energy < 50.0
    # Sprouts should have gained energy
    total_sprout_energy = sum(s.energy for s in sprouts)
    assert total_sprout_energy > 0
