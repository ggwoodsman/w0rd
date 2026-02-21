"""Integration tests for the full organism — the Garden Gate API."""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "w0rd" in data["name"]
    assert data["version"] == "3.0.0"


@pytest.mark.asyncio
async def test_plant_and_observe():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Plant a seed
        resp = await client.post("/plant", json={"wish": "I want to create beautiful art and share joy"})
        assert resp.status_code == 200
        seed = resp.json()
        assert seed["id"]
        assert seed["essence"]
        assert len(seed["themes"]) > 0
        assert seed["status"] == "growing"
        assert len(seed["sprouts"]) > 0
        seed_id = seed["id"]

        # Observe the seed
        resp = await client.get(f"/seed/{seed_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == seed_id


@pytest.mark.asyncio
async def test_plant_many():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/plant/many", json={
            "wishes": ["I want peace", "I want to learn", "I want to connect"]
        })
        assert resp.status_code == 200
        seeds = resp.json()
        assert len(seeds) == 3


@pytest.mark.asyncio
async def test_water_seed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/plant", json={"wish": "grow and flourish"})
        seed_id = resp.json()["id"]
        initial_energy = resp.json()["energy"]

        resp = await client.post(f"/seed/{seed_id}/water", json={
            "attention_seconds": 10.0, "energy_boost": 5.0
        })
        assert resp.status_code == 200
        assert resp.json()["energy"] >= initial_energy


@pytest.mark.asyncio
async def test_harvest_seed():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/plant", json={"wish": "complete this task"})
        seed_id = resp.json()["id"]

        resp = await client.post(f"/seed/{seed_id}/harvest")
        assert resp.status_code == 200
        assert resp.json()["status"] == "harvested"


@pytest.mark.asyncio
async def test_compost_and_resurrect():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/plant", json={"wish": "temporary idea"})
        seed_id = resp.json()["id"]

        # Compost
        resp = await client.post(f"/seed/{seed_id}/compost")
        assert resp.status_code == 200
        assert resp.json()["status"] == "composted"

        # Resurrect
        resp = await client.post(f"/seed/{seed_id}/resurrect")
        assert resp.status_code == 200
        assert resp.json()["status"] == "planted"


@pytest.mark.asyncio
async def test_garden_overview():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/garden")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "seeds" in data
        assert data["state"]["season"] in ["spring", "summer", "autumn", "winter"]


@pytest.mark.asyncio
async def test_ecosystem():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/ecosystem")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "seed_count" in data
        assert "sprout_count" in data


@pytest.mark.asyncio
async def test_pulse():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/pulse")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert len(data["summary"]) > 0


@pytest.mark.asyncio
async def test_seasons():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/seasons")
        assert resp.status_code == 200
        assert resp.json()["season"] in ["spring", "summer", "autumn", "winter"]

        # Turn season
        resp = await client.post("/seasons/turn")
        assert resp.status_code == 200
        assert "season" in resp.json()


@pytest.mark.asyncio
async def test_gardener():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/gardener")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data


@pytest.mark.asyncio
async def test_mycelium():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/mycelium")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dreams():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/dreams")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_soil_richness():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/soil/richness")
        assert resp.status_code == 200
        data = resp.json()
        assert "richness" in data
        assert "theme_diversity" in data


@pytest.mark.asyncio
async def test_hormones_recent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Plant something first to generate hormones
        await client.post("/plant", json={"wish": "generate some hormones"})
        resp = await client.get("/hormones/recent")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_seed_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/seed/nonexistent")
        assert resp.status_code == 404
