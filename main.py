"""
w0rd — Living System Engine v3
The First Cell of a Planetary Organism

FastAPI application that wires all organs together into a living system.
Every endpoint is an act of tending the garden.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.consciousness import ConsciousnessPulse
from core.dreaming import DreamingEngine
from core.emotions import EmotionalCore
from core.energy import EnergyOrgan
from core.ethics import ImmuneWisdom
from core.fractal import VascularGrower
from core.gardener import GardenerOrgan
from core.healing import ScarTissue
from core.hormones import HormoneBus
from core.inner_voice import InnerVoice
from core.intent import SeedListener
from core.llm import ThinkingEvent, check_ollama, on_thinking, shutdown_llm_client
from core.memory import AutobiographicalMemory
from core.agents import AgentRegistry
from core.autonomy import (
    evaluate_mission, plan_mission, reset_tick_budget,
    should_compost, should_harvest, should_plant_dream, should_promote,
)
from core.capabilities import execute_capability
from core.prediction import PredictionEngine
from core.regeneration import SeasonalHeartbeat
from core.self_model import SelfModel
from core.symbiosis import MycelialNetwork
from db.database import async_session, get_session, init_db, shutdown_db
from models.db_models import (
    AgentNode,
    Dream,
    EmotionalState,
    EpisodicMemory,
    GardenState,
    HormoneLog,
    InnerThought,
    Prediction,
    PulseReport,
    Seed,
    SelfModelSnapshot,
    Sprout,
    SymbioticLink,
    WoundRecord,
)
from models.schemas import (
    AgentApprovalRequest,
    AgentNodeResponse,
    DreamResponse,
    EcosystemResponse,
    GardenOverview,
    GardenStateResponse,
    GardenerResponse,
    GardenerUpdateRequest,
    HormoneLogResponse,
    PlantManyRequest,
    PlantRequest,
    PulseResponse,
    SeedResponse,
    SoilRichnessResponse,
    SproutResponse,
    SymbioticLinkResponse,
    WaterRequest,
    WoundResponse,
)

# ── Logging ───────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("w0rd")

# ── Organism Assembly ─────────────────────────────────────────────

bus = HormoneBus()
seed_listener = SeedListener(bus)
grower = VascularGrower(bus)
energy_organ = EnergyOrgan(bus)
immune = ImmuneWisdom(bus)
healer = ScarTissue(bus)
mycelium = MycelialNetwork(bus)
heartbeat = SeasonalHeartbeat(bus)
dreamer = DreamingEngine(bus)
consciousness = ConsciousnessPulse(bus)
gardener_organ = GardenerOrgan(bus)
agent_registry = AgentRegistry(bus)

# ── Consciousness Layer ──────────────────────────────────────────
emotional_core = EmotionalCore(bus)
inner_voice = InnerVoice(bus)
autobio_memory = AutobiographicalMemory(bus)
prediction_engine = PredictionEngine(bus)
self_model = SelfModel(bus)

# ── WebSocket Connections ─────────────────────────────────────────

ws_connections: list[WebSocket] = []
ws_thinking_connections: list[WebSocket] = []


async def _broadcast_ws(event: str, data: dict) -> None:
    dead = []
    for ws in ws_connections:
        try:
            await ws.send_json({"event": event, "data": data, "timestamp": time.time()})
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_connections.remove(ws)


async def _broadcast_thinking(event: ThinkingEvent) -> None:
    dead = []
    msg = {"type": "thinking", **event.to_dict()}
    for ws in ws_thinking_connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_thinking_connections.remove(ws)
    # Also send to main ws as a thinking event
    await _broadcast_ws("thinking", event.to_dict())

on_thinking(_broadcast_thinking)


# Wire hormone bus to WebSocket broadcast
async def _hormone_to_ws(hormone) -> None:
    await _broadcast_ws(hormone.name, hormone.payload)

bus.subscribe("seed_planted", _hormone_to_ws)
bus.subscribe("tree_grown", _hormone_to_ws)
bus.subscribe("photosynthesis", _hormone_to_ws)
bus.subscribe("ethical_violation", _hormone_to_ws)
bus.subscribe("ethical_clearance", _hormone_to_ws)
bus.subscribe("healing_complete", _hormone_to_ws)
bus.subscribe("season_change", _hormone_to_ws)
bus.subscribe("dream_generated", _hormone_to_ws)
bus.subscribe("lucid_dream", _hormone_to_ws)
bus.subscribe("pollination", _hormone_to_ws)
bus.subscribe("quorum_reached", _hormone_to_ws)
bus.subscribe("pulse_generated", _hormone_to_ws)
bus.subscribe("wisdom_milestone", _hormone_to_ws)
bus.subscribe("apoptosis", _hormone_to_ws)
bus.subscribe("emergency_winter", _hormone_to_ws)
bus.subscribe("agent_spawned", _hormone_to_ws)
bus.subscribe("agent_working", _hormone_to_ws)
bus.subscribe("agent_completed", _hormone_to_ws)
bus.subscribe("agent_retired", _hormone_to_ws)

# Consciousness layer events
bus.subscribe("emotional_shift", _hormone_to_ws)
bus.subscribe("inner_thought", _hormone_to_ws)
bus.subscribe("core_memory_formed", _hormone_to_ws)
bus.subscribe("high_surprise", _hormone_to_ws)
bus.subscribe("low_surprise", _hormone_to_ws)
bus.subscribe("self_model_updated", _hormone_to_ws)


# ── Autonomous Lifecycle ──────────────────────────────────────────

LIFECYCLE_INTERVAL = 60          # seconds between ticks
SEASON_TURN_EVERY = 5            # turn season every N ticks (~5 min)
PULSE_EVERY = 3                  # consciousness pulse every N ticks
AUTO_WATER_ATTENTION = 2.0       # simulated attention seconds per auto-water

_lifecycle_task: asyncio.Task | None = None
_lifecycle_tick = 0


async def _lifecycle_loop() -> None:
    """Background loop — the organism's autonomous heartbeat.

    IMPORTANT: To avoid SQLite locking, each phase uses its own short-lived
    DB session.  LLM calls (which can take seconds) happen *between* sessions
    so no connection is held open during inference.
    """
    global _lifecycle_tick
    logger.info("Autonomous lifecycle started (interval=%ds)", LIFECYCLE_INTERVAL)

    while True:
        await asyncio.sleep(LIFECYCLE_INTERVAL)
        _lifecycle_tick += 1
        reset_tick_budget()
        logger.info("── Lifecycle tick %d ──", _lifecycle_tick)

        try:
            # ── Phase 1: Read state & auto-water (quick DB work, no LLM) ──
            seed_snapshots = []  # list of (seed_id, status, energy, essence, created_at, sprout_data)
            async with async_session() as session:
                state = await _get_garden_state(session)

                living = await session.execute(
                    select(Seed).where(
                        Seed.is_composted == False,
                        Seed.status.in_(["planted", "growing"]),
                    )
                )
                living_seeds = list(living.scalars().all())

                for seed in living_seeds:
                    await energy_organ.photosynthesize(session, seed, AUTO_WATER_ATTENTION)
                    await energy_organ.phloem_distribute(session, seed)
                    await energy_organ.mycorrhizal_redistribute(session, seed)

                # Promote planted → growing (no LLM needed)
                for seed in living_seeds:
                    if await should_promote(seed):
                        seed.status = "growing"
                        await _broadcast_ws("auto_promote", {
                            "seed_id": seed.id,
                            "essence": seed.essence or seed.raw_text,
                        })

                # Snapshot seed data for LLM decisions (done outside session)
                for seed in living_seeds:
                    if seed.status in ("planted", "growing"):
                        sprout_result = await session.execute(
                            select(Sprout).where(
                                Sprout.seed_id == seed.id,
                                Sprout.is_composted == False,
                            )
                        )
                        sprouts = list(sprout_result.scalars().all())
                        seed_snapshots.append({
                            "id": seed.id,
                            "status": seed.status,
                            "energy": seed.energy,
                            "essence": seed.essence or seed.raw_text,
                            "created_at": seed.created_at,
                            "sprouts": [
                                {"depth": s.depth, "description": s.description, "energy": s.energy}
                                for s in sprouts
                            ],
                        })

                await session.commit()

            if living_seeds:
                await _broadcast_ws("auto_water", {
                    "count": len(living_seeds),
                    "tick": _lifecycle_tick,
                })

            # ── Phase 2: LLM decisions (no DB session held) ──
            # Emotional bias influences decisions
            emo_bias = emotional_core.get_decision_bias()
            harvest_ids = []
            compost_ids = []

            for snap in seed_snapshots:
                # Build lightweight proxy objects for the decision functions
                seed_proxy = type("SeedProxy", (), snap)()
                sprout_proxies = [type("SproutProxy", (), s)() for s in snap["sprouts"]]

                if await should_harvest(seed_proxy, sprout_proxies):
                    harvest_ids.append(snap["id"])
                    logger.info("LLM decided: harvest seed %s", snap["id"])
                elif await should_compost(seed_proxy, sprout_proxies):
                    # Emotional gate: high anxiety/conservatism suppresses composting
                    if emo_bias.get("conservatism", 0) > 0.5 and random.random() < emo_bias["conservatism"] * 0.4:
                        logger.info("Emotional override: too anxious to compost seed %s", snap["id"])
                    else:
                        compost_ids.append(snap["id"])
                        logger.info("LLM decided: compost seed %s", snap["id"])

            # ── Phase 3: Apply harvest/compost decisions (quick DB) ──
            if harvest_ids or compost_ids:
                async with async_session() as session:
                    for sid in harvest_ids:
                        result = await session.execute(select(Seed).where(Seed.id == sid))
                        seed = result.scalar_one_or_none()
                        if seed and seed.status in ("planted", "growing"):
                            seed.status = "harvested"
                            await mycelium.pollinate(session, seed)
                            await _broadcast_ws("auto_harvest", {
                                "seed_id": seed.id,
                                "essence": seed.essence or seed.raw_text,
                            })

                    for sid in compost_ids:
                        result = await session.execute(select(Seed).where(Seed.id == sid))
                        seed = result.scalar_one_or_none()
                        if seed and seed.status in ("planted", "growing"):
                            seed.status = "composted"
                            seed.is_composted = True
                            await _broadcast_ws("auto_compost", {
                                "seed_id": seed.id,
                                "essence": seed.essence or seed.raw_text,
                            })

                    await session.commit()

            # ── Phase 3b: Agent Orchestration ──

            # Step 1: Retire completed agents first (free up capacity)
            async with async_session() as session:
                completed_agents = await agent_registry.get_completed(session)
                for agent in completed_agents:
                    await agent_registry.retire(session, agent.id, "task complete")
                if completed_agents:
                    logger.info("Retired %d completed agents", len(completed_agents))
                await session.commit()

            # Step 2: Execute idle agents (max 4 per tick)
            agent_exec_ids = []
            async with async_session() as session:
                idle_agents = await agent_registry.get_idle(session)
                for agent in idle_agents[:4]:
                    agent_exec_ids.append({
                        "id": agent.id,
                        "agent_type": agent.agent_type,
                        "task": agent.task_description,
                        "capability": json.loads(agent.capability or "{}"),
                    })
                    await agent_registry.start_work(session, agent.id)
                await session.commit()

            # Execute capabilities outside DB session (may involve LLM)
            for spec in agent_exec_ids:
                params = {"task": spec["task"], **spec["capability"]}
                cap_result = await execute_capability(spec["agent_type"], params)
                async with async_session() as session:
                    if cap_result.get("success"):
                        await agent_registry.complete(session, spec["id"], cap_result.get("result", ""))
                    else:
                        await agent_registry.fail(session, spec["id"], cap_result.get("error", "Unknown error"))
                    await session.commit()

            # Step 3: Retire newly completed agents
            async with async_session() as session:
                newly_completed = await agent_registry.get_completed(session)
                for agent in newly_completed:
                    await agent_registry.retire(session, agent.id, "task complete")
                await session.commit()

            # Step 4: Cortex planning — spawn new agents (limit to 2 seeds per tick)
            async with async_session() as session:
                growing_seeds = await session.execute(
                    select(Seed).where(Seed.status == "growing", Seed.is_composted == False)
                )
                seeds_planned = 0
                for seed in growing_seeds.scalars().all():
                    if seeds_planned >= 2:
                        break
                    existing = await agent_registry.get_for_seed(session, seed.id)
                    tasks = await plan_mission(seed, existing)
                    if tasks:
                        seeds_planned += 1
                        for task_spec in tasks:
                            await agent_registry.spawn(
                                session,
                                agent_type=task_spec["agent_type"],
                                task_description=task_spec["task"],
                                seed_id=seed.id,
                            )
                await session.commit()

            # ── Phase 4: Season turn (quick DB) ──
            if _lifecycle_tick % SEASON_TURN_EVERY == 0:
                async with async_session() as session:
                    new_season = await heartbeat.turn_season(session)
                    depleted = await energy_organ.apply_entropy(session, new_season)
                    if depleted > 0:
                        await healer.triage_and_heal(
                            session, "energy_famine",
                            {"depleted_count": depleted, "season": new_season},
                        )
                    await session.commit()
                    logger.info("Auto season turn → %s", new_season)

            # ── Phase 5: Mycelium maintenance (quick DB) ──
            async with async_session() as session:
                await mycelium.scan_and_link(session)
                await mycelium.share_nutrients(session)
                await mycelium.check_quorum(session)
                await session.commit()

            # ── Phase 6: Auto-dream (LLM + DB, separate sessions) ──
            if _lifecycle_tick % SEASON_TURN_EVERY == 0 or _lifecycle_tick % 4 == 0:
                # Generate dream (involves LLM) in its own session
                dream_data = None
                async with async_session() as session:
                    dream = await dreamer.dream(session)
                    if dream:
                        dream_data = {"id": dream.id, "insight": dream.insight, "perplexity": dream.perplexity, "temperature": dream.temperature, "planted": dream.planted}
                    await session.commit()

                # LLM decision outside session
                if dream_data:
                    dream_proxy = type("DreamProxy", (), dream_data)()
                    if await should_plant_dream(dream_proxy):
                        async with async_session() as session:
                            planted_seed = await dreamer.plant_dream(session, dream_data["id"])
                            if planted_seed:
                                await grower.grow(session, planted_seed)
                                await _broadcast_ws("auto_dream_planted", {
                                    "dream_id": dream_data["id"],
                                    "seed_id": planted_seed.id,
                                    "insight": dream_data["insight"],
                                })
                                logger.info("Auto-planted dream %s as seed %s", dream_data["id"], planted_seed.id)
                            await session.commit()

            # ── Phase 7: Auto-pulse (LLM + DB in own session) ──
            if _lifecycle_tick % PULSE_EVERY == 0:
                async with async_session() as session:
                    await consciousness.pulse(session)
                    await session.commit()
                await _broadcast_ws("auto_pulse", {"tick": _lifecycle_tick})

            # ── Phase 8: Consciousness Layer ──
            # 8a: Emotional state processing (every tick)
            async with async_session() as session:
                emo_state = await emotional_core.process_tick(session)
                await session.commit()
            emo_snapshot = emotional_core.snapshot_for_context()

            # 8b: Autobiographical memory (every tick — processes queued events)
            async with async_session() as session:
                new_memories = await autobio_memory.process_tick(session, emo_snapshot)
                await session.commit()

            # 8c: Inner monologue (every tick — LLM generates a thought)
            async with async_session() as session:
                thought = await inner_voice.think(session, emo_snapshot)
                await session.commit()

            # 8d: Predictions — make new ones and resolve old ones (every tick)
            async with async_session() as session:
                await prediction_engine.resolve_predictions(session)
                await prediction_engine.make_predictions(session)
                await session.commit()

            # 8e: Self-model introspection (every 10 ticks)
            if _lifecycle_tick % 10 == 0:
                async with async_session() as session:
                    snapshot = await self_model.introspect(session)
                    await session.commit()
                    if snapshot and snapshot.identity_narrative:
                        await _broadcast_ws("identity_update", {
                            "narrative": snapshot.identity_narrative,
                            "traits": json.loads(snapshot.personality_traits or "{}"),
                        })

            # 8f: Memory consolidation (during winter or every 20 ticks)
            if _lifecycle_tick % 20 == 0:
                async with async_session() as session:
                    pruned = await autobio_memory.consolidate(session)
                    await session.commit()

            # ── Flush slow-release hormones ──
            await bus.flush_slow_release()

            logger.info("── Tick %d complete ──", _lifecycle_tick)

        except Exception:
            logger.exception("Lifecycle tick %d failed", _lifecycle_tick)


# ── Lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _lifecycle_task
    await init_db()
    await bus.start()
    # Load prior emotional state from DB
    async with async_session() as session:
        await emotional_core.load_latest(session)
    _lifecycle_task = asyncio.create_task(_lifecycle_loop())
    logger.info("The organism awakens. Consciousness engaged.")
    yield
    if _lifecycle_task:
        _lifecycle_task.cancel()
        try:
            await _lifecycle_task
        except asyncio.CancelledError:
            pass
    await bus.stop()
    await shutdown_llm_client()
    await shutdown_db()
    logger.info("The organism rests. The garden gate closes.")


app = FastAPI(
    title="w0rd — Living System Engine",
    description="The first cell of a planetary organism. Plant wishes, tend the garden, watch it grow.",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────

def _seed_to_response(seed: Seed, sprouts: list[Sprout] | None = None) -> SeedResponse:
    sprout_responses = []
    if sprouts:
        sprout_responses = [
            SproutResponse(
                id=s.id, seed_id=s.seed_id, parent_id=s.parent_id,
                depth=s.depth, label=s.label, description=s.description,
                energy=s.energy, ethical_score=s.ethical_score,
                pressure=s.pressure, resonance=s.resonance,
                warmth=s.warmth, status=s.status, created_at=s.created_at,
            )
            for s in sprouts
        ]
    return SeedResponse(
        id=seed.id, raw_text=seed.raw_text, essence=seed.essence,
        themes=json.loads(seed.themes or "[]"),
        tone_valence=seed.tone_valence, tone_arousal=seed.tone_arousal,
        resonance=seed.resonance, energy=seed.energy,
        ethical_score=seed.ethical_score, vitality=seed.vitality,
        season_born=seed.season_born, version=seed.version,
        status=seed.status, created_at=seed.created_at,
        sprouts=sprout_responses,
    )


async def _get_garden_state(session: AsyncSession) -> GardenState:
    result = await session.execute(select(GardenState).where(GardenState.id == "garden"))
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=500, detail="Garden state not initialized")
    return state


# ══════════════════════════════════════════════════════════════════
# PLANTING & GROWING
# ══════════════════════════════════════════════════════════════════

@app.post("/plant", response_model=SeedResponse, tags=["Planting"])
async def plant_seed(req: PlantRequest, session: AsyncSession = Depends(get_session)):
    """Plant a raw wish into the soil."""
    state = await _get_garden_state(session)

    # Get or create gardener
    gardener = await gardener_organ.get_or_create(session, req.gardener_id)
    pheromone_bias = gardener_organ.get_pheromone_bias(gardener)

    # Listen to the wish
    seed = await seed_listener.listen(
        session, req.wish, gardener.id, pheromone_bias, state.season
    )

    # Grow the fractal tree
    sprouts = await grower.grow(session, seed)

    # Ethical evaluation of all sprouts
    for sprout in sprouts:
        await immune.evaluate_and_act(session, sprout)

    # Record gardener interaction
    themes = json.loads(seed.themes or "[]")
    await gardener_organ.record_interaction(session, gardener, themes)

    await session.commit()
    return _seed_to_response(seed, sprouts)


@app.post("/plant/many", response_model=list[SeedResponse], tags=["Planting"])
async def plant_many(req: PlantManyRequest, session: AsyncSession = Depends(get_session)):
    """Scatter multiple seeds at once."""
    results = []
    state = await _get_garden_state(session)
    gardener = await gardener_organ.get_or_create(session, req.gardener_id)
    pheromone_bias = gardener_organ.get_pheromone_bias(gardener)

    for wish in req.wishes:
        seed = await seed_listener.listen(session, wish, gardener.id, pheromone_bias, state.season)
        sprouts = await grower.grow(session, seed)
        for sprout in sprouts:
            await immune.evaluate_and_act(session, sprout)
        themes = json.loads(seed.themes or "[]")
        await gardener_organ.record_interaction(session, gardener, themes)
        results.append(_seed_to_response(seed, sprouts))

    await session.commit()
    return results


@app.get("/seed/{seed_id}", response_model=SeedResponse, tags=["Planting"])
async def get_seed(seed_id: str, session: AsyncSession = Depends(get_session)):
    """Observe a seed and its fractal tree."""
    result = await session.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    sprout_result = await session.execute(
        select(Sprout).where(Sprout.seed_id == seed_id).order_by(Sprout.depth, Sprout.created_at)
    )
    sprouts = list(sprout_result.scalars().all())
    return _seed_to_response(seed, sprouts)


@app.get("/seed/{seed_id}/lineage", tags=["Planting"])
async def get_seed_lineage(seed_id: str, session: AsyncSession = Depends(get_session)):
    """View a seed's full version history."""
    result = await session.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    return {"seed_id": seed.id, "version": seed.version, "lineage": json.loads(seed.lineage or "[]")}


@app.post("/seed/{seed_id}/water", response_model=SeedResponse, tags=["Planting"])
async def water_seed(seed_id: str, req: WaterRequest, session: AsyncSession = Depends(get_session)):
    """Water a seed — add energy through attention and feedback."""
    result = await session.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    await energy_organ.photosynthesize(session, seed, req.attention_seconds)
    await energy_organ.phloem_distribute(session, seed)
    await energy_organ.mycorrhizal_redistribute(session, seed)

    sprout_result = await session.execute(
        select(Sprout).where(Sprout.seed_id == seed_id).order_by(Sprout.depth)
    )
    sprouts = list(sprout_result.scalars().all())

    await session.commit()
    return _seed_to_response(seed, sprouts)


@app.post("/seed/{seed_id}/harvest", response_model=SeedResponse, tags=["Planting"])
async def harvest_seed(seed_id: str, session: AsyncSession = Depends(get_session)):
    """Harvest a seed — mark it as fulfilled."""
    result = await session.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    seed.status = "harvested"

    # Pollinate other seeds with this success
    await mycelium.pollinate(session, seed)

    await session.commit()
    return _seed_to_response(seed)


@app.post("/seed/{seed_id}/compost", response_model=SeedResponse, tags=["Planting"])
async def compost_seed(seed_id: str, session: AsyncSession = Depends(get_session)):
    """Compost a seed — gracefully retire it, memory preserved."""
    result = await session.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    seed.status = "composted"
    seed.is_composted = True
    await session.commit()
    return _seed_to_response(seed)


@app.post("/seed/{seed_id}/resurrect", response_model=SeedResponse, tags=["Planting"])
async def resurrect_seed(seed_id: str, session: AsyncSession = Depends(get_session)):
    """Resurrect a composted seed — un-compost it."""
    result = await session.execute(select(Seed).where(Seed.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    if not seed.is_composted:
        raise HTTPException(status_code=400, detail="Seed is not composted")

    seed.status = "planted"
    seed.is_composted = False
    await session.commit()
    return _seed_to_response(seed)


# ══════════════════════════════════════════════════════════════════
# ECOSYSTEM & AWARENESS
# ══════════════════════════════════════════════════════════════════

@app.get("/garden", response_model=GardenOverview, tags=["Ecosystem"])
async def get_garden(session: AsyncSession = Depends(get_session)):
    """Survey the entire garden."""
    state = await _get_garden_state(session)
    state.tidal_phase = energy_organ.get_tidal_phase()

    result = await session.execute(
        select(Seed).where(Seed.is_composted == False).order_by(Seed.created_at.desc())
    )
    seeds = list(result.scalars().all())

    return GardenOverview(
        state=GardenStateResponse(
            total_energy=state.total_energy, vitality=state.vitality,
            season=state.season, tidal_phase=state.tidal_phase,
            cycle_count=state.cycle_count, wisdom_score=state.wisdom_score,
            antifragility_score=state.antifragility_score,
            dream_count=state.dream_count, soil_richness=state.soil_richness,
            last_pulse=state.last_pulse,
        ),
        seeds=[_seed_to_response(s) for s in seeds],
        seed_count=len(seeds),
    )


@app.get("/ecosystem", response_model=EcosystemResponse, tags=["Ecosystem"])
async def get_ecosystem(session: AsyncSession = Depends(get_session)):
    """Panoramic view of the full ecosystem."""
    state = await _get_garden_state(session)

    seed_count = (await session.execute(select(func.count(Seed.id)))).scalar() or 0
    sprout_count = (await session.execute(select(func.count(Sprout.id)))).scalar() or 0
    link_count = (await session.execute(select(func.count(SymbioticLink.id)))).scalar() or 0
    wound_count = (await session.execute(select(func.count(WoundRecord.id)))).scalar() or 0
    dream_count = (await session.execute(select(func.count(Dream.id)))).scalar() or 0

    # Recent hormone activity from bus history
    recent_hormones = [
        HormoneLogResponse(
            id=h.id, hormone_name=h.name, emitter_organ=h.emitter,
            payload=h.payload, processed=True, created_at=h.timestamp,
        )
        for h in bus.recent(10)
    ]

    return EcosystemResponse(
        state=GardenStateResponse(
            total_energy=state.total_energy, vitality=state.vitality,
            season=state.season, tidal_phase=energy_organ.get_tidal_phase(),
            cycle_count=state.cycle_count, wisdom_score=state.wisdom_score,
            antifragility_score=state.antifragility_score,
            dream_count=state.dream_count, soil_richness=state.soil_richness,
            last_pulse=state.last_pulse,
        ),
        seed_count=seed_count,
        sprout_count=sprout_count,
        link_count=link_count,
        wound_count=wound_count,
        dream_count=dream_count,
        recent_hormones=recent_hormones,
    )


@app.get("/pulse", response_model=PulseResponse, tags=["Ecosystem"])
async def get_pulse(session: AsyncSession = Depends(get_session)):
    """Feel the organism's heartbeat — return the latest pulse report."""
    result = await session.execute(
        select(PulseReport).order_by(PulseReport.created_at.desc()).limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        # No pulse yet — generate one
        report = await consciousness.pulse(session)
        await session.commit()
    return PulseResponse(
        id=report.id, cycle=report.cycle, summary=report.summary,
        thriving=json.loads(report.thriving),
        struggling=json.loads(report.struggling),
        healing=json.loads(report.healing),
        dreaming=json.loads(report.dreaming),
        emergent=json.loads(report.emergent),
        created_at=report.created_at,
    )


@app.get("/pulse/history", response_model=list[PulseResponse], tags=["Ecosystem"])
async def get_pulse_history(limit: int = 10, session: AsyncSession = Depends(get_session)):
    """Past pulse reports — the organism's medical records."""
    result = await session.execute(
        select(PulseReport).order_by(PulseReport.created_at.desc()).limit(limit)
    )
    reports = list(result.scalars().all())
    return [
        PulseResponse(
            id=r.id, cycle=r.cycle, summary=r.summary,
            thriving=json.loads(r.thriving), struggling=json.loads(r.struggling),
            healing=json.loads(r.healing), dreaming=json.loads(r.dreaming),
            emergent=json.loads(r.emergent), created_at=r.created_at,
        )
        for r in reports
    ]


@app.get("/soil", tags=["Ecosystem"])
async def get_soil(limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Dig into the compost/memory layer."""
    result = await session.execute(
        select(Seed).where(Seed.is_composted == True).order_by(Seed.created_at.desc()).limit(limit)
    )
    composted = list(result.scalars().all())
    return {"composted_seeds": [_seed_to_response(s) for s in composted], "count": len(composted)}


@app.get("/soil/richness", response_model=SoilRichnessResponse, tags=["Ecosystem"])
async def get_soil_richness(session: AsyncSession = Depends(get_session)):
    """Test the soil — how rich is the compost?"""
    composted_count = (await session.execute(
        select(func.count(Seed.id)).where(Seed.is_composted == True)
    )).scalar() or 0

    # Theme diversity across all seeds
    result = await session.execute(select(Seed.themes))
    all_themes_raw = [r[0] for r in result.all()]
    all_themes = set()
    for raw in all_themes_raw:
        for t in json.loads(raw or "[]"):
            all_themes.add(t)

    state = await _get_garden_state(session)
    age_days = (time.time() - (state.last_pulse or time.time())) / 86400

    richness = composted_count * 0.5 + len(all_themes) * 1.0 + age_days * 0.1

    return SoilRichnessResponse(
        richness=round(richness, 2),
        total_composted=composted_count,
        theme_diversity=len(all_themes),
        garden_age_days=round(age_days, 2),
    )


# ══════════════════════════════════════════════════════════════════
# UNDERGROUND & DREAMS
# ══════════════════════════════════════════════════════════════════

@app.get("/mycelium", response_model=list[SymbioticLinkResponse], tags=["Underground"])
async def get_mycelium(session: AsyncSession = Depends(get_session)):
    """Listen to the underground — view symbiotic links."""
    result = await session.execute(select(SymbioticLink).order_by(SymbioticLink.created_at.desc()))
    links = list(result.scalars().all())
    return [
        SymbioticLinkResponse(
            id=l.id, sprout_a_id=l.sprout_a_id, sprout_b_id=l.sprout_b_id,
            relationship_type=l.relationship_type, synergy_score=l.synergy_score,
            nutrient_flow=l.nutrient_flow, pollen_transferred=l.pollen_transferred,
            created_at=l.created_at,
        )
        for l in links
    ]


@app.get("/mycelium/pollen", tags=["Underground"])
async def get_pollen_map(session: AsyncSession = Depends(get_session)):
    """View recent cross-pollination events."""
    pollen_hormones = [h for h in bus.recent(50) if h.name == "pollination"]
    return {
        "recent_pollinations": [
            {"source_seed_id": h.payload.get("source_seed_id"), "pollinated_count": h.payload.get("pollinated_count"), "timestamp": h.timestamp}
            for h in pollen_hormones
        ]
    }


@app.get("/dreams", response_model=list[DreamResponse], tags=["Underground"])
async def get_dreams(session: AsyncSession = Depends(get_session)):
    """Morning review — see what the garden dreamed."""
    result = await session.execute(
        select(Dream).order_by(Dream.created_at.desc()).limit(20)
    )
    dreams = list(result.scalars().all())
    return [
        DreamResponse(
            id=d.id, source_seed_ids=json.loads(d.source_seed_ids),
            insight=d.insight, temperature=d.temperature,
            perplexity=d.perplexity, planted=d.planted, created_at=d.created_at,
        )
        for d in dreams
    ]


@app.post("/dreams/{dream_id}/plant", response_model=SeedResponse, tags=["Underground"])
async def plant_dream(dream_id: str, session: AsyncSession = Depends(get_session)):
    """Plant a dream — turn a dream-insight into a new seed."""
    seed = await dreamer.plant_dream(session, dream_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Dream not found or already planted")

    sprouts = await grower.grow(session, seed)
    await session.commit()
    return _seed_to_response(seed, sprouts)


@app.get("/wounds", response_model=list[WoundResponse], tags=["Underground"])
async def get_wounds(limit: int = 20, session: AsyncSession = Depends(get_session)):
    """View wound history and lessons learned."""
    result = await session.execute(
        select(WoundRecord).order_by(WoundRecord.created_at.desc()).limit(limit)
    )
    wounds = list(result.scalars().all())
    return [
        WoundResponse(
            id=w.id, wound_type=w.wound_type, severity=w.severity,
            source_hormone=w.source_hormone, healing_action=w.healing_action,
            scar_lesson=w.scar_lesson, antifragility_gained=w.antifragility_gained,
            created_at=w.created_at, healed_at=w.healed_at,
        )
        for w in wounds
    ]


# ══════════════════════════════════════════════════════════════════
# RHYTHM & IDENTITY
# ══════════════════════════════════════════════════════════════════

@app.post("/seasons/turn", tags=["Rhythm"])
async def turn_season(force: str | None = None, session: AsyncSession = Depends(get_session)):
    """Turn the season — advance the organism's lifecycle."""
    new_season = await heartbeat.turn_season(session, force)

    # Apply entropy during season turn
    depleted = await energy_organ.apply_entropy(session, new_season)

    # Process any wounds from energy depletion
    if depleted > 0:
        await healer.triage_and_heal(session, "energy_famine", {"depleted_count": depleted, "season": new_season})

    # Run mycelium scan
    await mycelium.scan_and_link(session)
    await mycelium.share_nutrients(session)
    await mycelium.check_quorum(session)

    # Flush slow-release hormones
    await bus.flush_slow_release()

    await session.commit()

    behavior = heartbeat.get_season_behavior(new_season)
    return {"season": new_season, "behavior": behavior}


@app.get("/seasons", tags=["Rhythm"])
async def get_seasons(session: AsyncSession = Depends(get_session)):
    """View current season and tidal phase."""
    state = await _get_garden_state(session)
    return {
        "season": state.season,
        "tidal_phase": energy_organ.get_tidal_phase(),
        "cycle_count": state.cycle_count,
        "behavior": heartbeat.get_season_behavior(state.season),
    }


@app.get("/gardener", response_model=GardenerResponse, tags=["Rhythm"])
async def get_gardener(gardener_id: str | None = None, session: AsyncSession = Depends(get_session)):
    """Look in the mirror — view your gardener profile."""
    gardener = await gardener_organ.get_or_create(session, gardener_id)
    await session.commit()
    return GardenerResponse(
        id=gardener.id, name=gardener.name,
        preference_vector=json.loads(gardener.preference_vector or "[]"),
        interaction_count=gardener.interaction_count,
        created_at=gardener.created_at,
    )


@app.put("/gardener", response_model=GardenerResponse, tags=["Rhythm"])
async def update_gardener(
    gardener_id: str, req: GardenerUpdateRequest, session: AsyncSession = Depends(get_session)
):
    """Self-tending — update your gardener preferences."""
    gardener = await gardener_organ.get_or_create(session, gardener_id)
    if req.name is not None:
        gardener.name = req.name
    if req.preference_vector is not None:
        gardener.preference_vector = json.dumps(req.preference_vector)
    await session.commit()
    return GardenerResponse(
        id=gardener.id, name=gardener.name,
        preference_vector=json.loads(gardener.preference_vector or "[]"),
        interaction_count=gardener.interaction_count,
        created_at=gardener.created_at,
    )


@app.get("/hormones/recent", response_model=list[HormoneLogResponse], tags=["Rhythm"])
async def get_recent_hormones(n: int = 20):
    """Blood test — view recent hormone signals."""
    return [
        HormoneLogResponse(
            id=h.id, hormone_name=h.name, emitter_organ=h.emitter,
            payload=h.payload, processed=True, created_at=h.timestamp,
        )
        for h in bus.recent(n)
    ]


# ══════════════════════════════════════════════════════════════════
# AGENTS
# ══════════════════════════════════════════════════════════════════

def _agent_to_response(agent: AgentNode) -> AgentNodeResponse:
    """Convert an AgentNode ORM object to a response schema."""
    return AgentNodeResponse(
        id=agent.id, name=agent.name, agent_type=agent.agent_type,
        status=agent.status, parent_id=agent.parent_id, seed_id=agent.seed_id,
        task_description=agent.task_description,
        capability=json.loads(agent.capability or "{}"),
        context=json.loads(agent.context or "{}"),
        result=agent.result or "", error=agent.error or "",
        created_at=agent.created_at,
        started_at=agent.started_at, completed_at=agent.completed_at,
        retired_at=agent.retired_at,
    )


@app.get("/agents", response_model=list[AgentNodeResponse], tags=["Agents"])
async def list_agents(
    include_retired: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """List all agent nodes. By default excludes retired agents."""
    if include_retired:
        result = await session.execute(select(AgentNode).order_by(AgentNode.created_at.desc()))
    else:
        result = await session.execute(
            select(AgentNode).where(AgentNode.status != "retired").order_by(AgentNode.created_at.desc())
        )
    return [_agent_to_response(a) for a in result.scalars().all()]


@app.get("/agents/{agent_id}", response_model=AgentNodeResponse, tags=["Agents"])
async def get_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    """Get details of a specific agent."""
    result = await session.execute(select(AgentNode).where(AgentNode.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return _agent_to_response(agent)


@app.post("/agents/{agent_id}/approve", response_model=AgentNodeResponse, tags=["Agents"])
async def approve_agent(
    agent_id: str, req: AgentApprovalRequest, session: AsyncSession = Depends(get_session),
):
    """Approve or deny a gated agent action (code_exec, file_write)."""
    agent = await agent_registry.approve(session, agent_id, req.approved)
    if not agent:
        raise HTTPException(404, "Agent not found or not awaiting approval")
    await session.commit()
    return _agent_to_response(agent)


@app.post("/agents/{agent_id}/retire", response_model=AgentNodeResponse, tags=["Agents"])
async def retire_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    """Manually retire an agent."""
    agent = await agent_registry.retire(session, agent_id, "manually retired by user")
    if not agent:
        raise HTTPException(404, "Agent not found or already retired")
    await session.commit()
    return _agent_to_response(agent)


# ══════════════════════════════════════════════════════════════════
# CONSCIOUSNESS
# ══════════════════════════════════════════════════════════════════

@app.get("/consciousness/emotions", tags=["Consciousness"])
async def get_emotions(session: AsyncSession = Depends(get_session)):
    """Feel the organism's current emotional state."""
    snapshot = emotional_core.snapshot_for_context()
    bias = emotional_core.get_decision_bias()
    # Recent emotional history
    result = await session.execute(
        select(EmotionalState).order_by(EmotionalState.created_at.desc()).limit(20)
    )
    history = [
        {
            "dominant": s.dominant_emotion, "intensity": s.intensity,
            "joy": s.joy, "curiosity": s.curiosity, "anxiety": s.anxiety,
            "pride": s.pride, "grief": s.grief, "wonder": s.wonder,
            "trigger": s.trigger_event, "created_at": s.created_at,
        }
        for s in result.scalars().all()
    ]
    return {
        "current": snapshot,
        "decision_bias": bias,
        "history": list(reversed(history)),
    }


@app.get("/consciousness/thoughts", tags=["Consciousness"])
async def get_thoughts(limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Listen to the organism's inner monologue."""
    stream = await inner_voice.get_recent_stream(session, limit)
    return {"thoughts": stream, "count": len(stream)}


@app.get("/consciousness/memories", tags=["Consciousness"])
async def get_memories(limit: int = 20, session: AsyncSession = Depends(get_session)):
    """Read the organism's autobiographical memories."""
    narrative = await autobio_memory.get_narrative_summary(session, limit)
    core = await autobio_memory.get_core_memories(session)
    return {
        "memories": narrative,
        "core_memories": [
            {
                "id": m.id, "narrative": m.narrative, "event_type": m.event_type,
                "valence": m.emotional_valence, "intensity": m.emotional_intensity,
                "recall_count": m.recall_count, "created_at": m.created_at,
            }
            for m in core
        ],
        "total": len(narrative),
        "core_count": len(core),
    }


@app.get("/consciousness/predictions", tags=["Consciousness"])
async def get_predictions(session: AsyncSession = Depends(get_session)):
    """View the organism's predictions and surprise levels."""
    # Active predictions
    active_result = await session.execute(
        select(Prediction).where(Prediction.resolved == False)
        .order_by(Prediction.created_at.desc())
    )
    active = [
        {
            "id": p.id, "type": p.prediction_type, "subject_id": p.subject_id,
            "predicted": p.predicted_outcome, "confidence": p.confidence,
            "created_at": p.created_at,
        }
        for p in active_result.scalars().all()
    ]
    # Recent resolved
    resolved_result = await session.execute(
        select(Prediction).where(Prediction.resolved == True)
        .order_by(Prediction.resolved_at.desc()).limit(20)
    )
    resolved = [
        {
            "id": p.id, "type": p.prediction_type, "predicted": p.predicted_outcome,
            "actual": p.actual_outcome, "surprise": p.surprise_score,
            "confidence": p.confidence, "resolved_at": p.resolved_at,
        }
        for p in resolved_result.scalars().all()
    ]
    stats = prediction_engine.get_stats()
    return {"active": active, "resolved": list(reversed(resolved)), "stats": stats}


@app.get("/consciousness/self", tags=["Consciousness"])
async def get_self_model(session: AsyncSession = Depends(get_session)):
    """The organism looks in the mirror — view its self-model."""
    latest = await self_model.get_latest(session)
    if not latest:
        return {"message": "No self-model yet — the organism is still learning who it is."}
    return latest


@app.get("/consciousness", tags=["Consciousness"])
async def get_consciousness_overview(session: AsyncSession = Depends(get_session)):
    """Full consciousness dashboard — emotions, thoughts, memories, predictions, identity."""
    emo = emotional_core.snapshot_for_context()
    thoughts = await inner_voice.get_recent_stream(session, 5)
    memories = await autobio_memory.get_narrative_summary(session, 5)
    core_mems = await autobio_memory.get_core_memories(session)
    pred_stats = prediction_engine.get_stats()
    self_latest = await self_model.get_latest(session)

    return {
        "emotions": emo,
        "decision_bias": emotional_core.get_decision_bias(),
        "recent_thoughts": thoughts,
        "recent_memories": memories,
        "core_memories": [{"narrative": m.narrative, "event_type": m.event_type} for m in core_mems[:5]],
        "prediction_stats": pred_stats,
        "self_model": self_latest,
        "tick": _lifecycle_tick,
    }


# ══════════════════════════════════════════════════════════════════
# REAL-TIME
# ══════════════════════════════════════════════════════════════════

@app.websocket("/ws/garden")
async def websocket_garden(websocket: WebSocket):
    """Sit in the garden — live stream of all organism events."""
    await websocket.accept()
    ws_connections.append(websocket)
    logger.info("Gardener connected to live stream")
    try:
        while True:
            # Keep connection alive, accept any messages as heartbeats
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong", "timestamp": time.time()})
    except WebSocketDisconnect:
        ws_connections.remove(websocket)
        logger.info("Gardener disconnected from live stream")


# ══════════════════════════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════════════════════════

@app.get("/lifecycle/status", tags=["System"])
async def lifecycle_status():
    """Check the autonomous lifecycle status."""
    return {
        "autonomous": True,
        "tick": _lifecycle_tick,
        "interval_seconds": LIFECYCLE_INTERVAL,
        "season_turn_every": SEASON_TURN_EVERY,
        "pulse_every": PULSE_EVERY,
        "running": _lifecycle_task is not None and not _lifecycle_task.done(),
    }


@app.get("/ollama/status", tags=["System"])
async def ollama_status():
    """Check Ollama LLM status and available models."""
    return await check_ollama()


@app.websocket("/ws/thinking")
async def websocket_thinking(websocket: WebSocket):
    """Stream the system's thinking process in real time."""
    await websocket.accept()
    ws_thinking_connections.append(websocket)
    logger.info("Thinking stream connected")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
    except WebSocketDisconnect:
        ws_thinking_connections.remove(websocket)
        logger.info("Thinking stream disconnected")


@app.get("/", tags=["Root"])
async def root():
    """The garden gate — welcome."""
    return {
        "name": "w0rd — Living System Engine",
        "version": "3.0.0",
        "message": "The w0rd is g00d. Plant a seed and watch it grow.",
        "endpoints": {
            "plant": "POST /plant",
            "garden": "GET /garden",
            "pulse": "GET /pulse",
            "dreams": "GET /dreams",
            "ecosystem": "GET /ecosystem",
            "docs": "GET /docs",
        },
    }
