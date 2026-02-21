"""
Autonomy Engine — The Organism's Self-Tending Intelligence + Cortex Planner

LLM-powered decision functions for autonomous lifecycle management,
plus the Cortex planner that decomposes seeds into agent tasks and
orchestrates the agent lifecycle.
"""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import generate, generate_json
from models.db_models import AgentNode, Dream, Seed, Sprout

logger = logging.getLogger("w0rd.autonomy")

# Track LLM calls per tick to avoid overloading
_llm_calls_this_tick = 0
MAX_LLM_EVALS_PER_TICK = 4  # max LLM decision calls per lifecycle tick


def reset_tick_budget() -> None:
    """Call at the start of each lifecycle tick."""
    global _llm_calls_this_tick
    _llm_calls_this_tick = 0


def _budget_available() -> bool:
    return _llm_calls_this_tick < MAX_LLM_EVALS_PER_TICK


def _use_budget() -> None:
    global _llm_calls_this_tick
    _llm_calls_this_tick += 1


# ── Harvest Decision ─────────────────────────────────────────────

async def should_harvest(seed: Seed, sprouts: list[Sprout]) -> bool:
    """
    Decide whether a seed should be harvested (fulfilled).
    Uses heuristics first; LLM only for borderline cases within budget.
    """
    if seed.status != "growing" or not sprouts:
        return False

    has_energy = seed.energy >= 15.0
    has_depth = len(sprouts) >= 3
    age_seconds = time.time() - (seed.created_at if seed.created_at else time.time())
    is_mature = age_seconds > 120  # 2+ minutes old

    # Clear no
    if not is_mature or len(sprouts) < 2:
        return False

    heuristic = has_energy and has_depth and is_mature

    # If heuristic says yes, just do it (no LLM needed)
    if heuristic:
        logger.info("Heuristic harvest: seed %s (energy=%.1f, sprouts=%d)", seed.id, seed.energy, len(sprouts))
        return True

    # Borderline case — ask LLM if budget allows
    if not _budget_available():
        return False

    _use_budget()
    try:
        sprout_desc = "\n".join(
            f"  - [depth {s.depth}] {s.description} (energy: {s.energy:.1f})"
            for s in sprouts[:8]
        )
        result = await generate(
            prompt=(
                f"A seed in the garden has this essence: \"{seed.essence or seed.raw_text}\"\n"
                f"Status: {seed.status}, Energy: {seed.energy:.1f}, Sprouts: {len(sprouts)}\n"
                f"Fractal tree:\n{sprout_desc}\n\n"
                "Has this seed been sufficiently decomposed and energized to be considered fulfilled? "
                "Answer ONLY 'yes' or 'no' — nothing else."
            ),
            system="You are the decision cortex of a living garden organism. You evaluate seed maturity.",
            organ="autonomy", phase="harvest_eval",
            temperature=0.2, max_tokens=10,
        )
        if result:
            answer = result.strip().lower()
            if "yes" in answer:
                logger.info("LLM says harvest seed %s", seed.id)
                return True
    except Exception as e:
        logger.debug("LLM harvest decision failed: %s", e)

    return False


# ── Compost Decision ─────────────────────────────────────────────

async def should_compost(seed: Seed, sprouts: list[Sprout]) -> bool:
    """
    Decide whether a seed should be composted (gracefully retired).
    LLM evaluates stagnation; falls back to heuristics.
    """
    if seed.status not in ("planted", "growing"):
        return False

    age_seconds = time.time() - (seed.created_at if seed.created_at else time.time())
    is_old = age_seconds > 300  # 5+ minutes
    is_starving = seed.energy < 1.0
    sprout_energy = sum(s.energy for s in sprouts) if sprouts else 0
    is_dead = is_old and is_starving and sprout_energy < 0.5

    # Clear no
    if not is_old:
        return False

    # If heuristic says dead, just do it
    if is_dead:
        logger.info("Heuristic compost: seed %s (energy=%.1f, age=%ds)", seed.id, seed.energy, age_seconds)
        return True

    # Borderline — ask LLM if budget allows
    if not _budget_available():
        return False

    _use_budget()
    try:
        result = await generate(
            prompt=(
                f"A seed in the garden: \"{seed.essence or seed.raw_text}\"\n"
                f"Status: {seed.status}, Energy: {seed.energy:.1f}, Age: {age_seconds:.0f}s\n"
                f"Total sprout energy: {sprout_energy:.1f}, Sprout count: {len(sprouts)}\n\n"
                "Is this seed stagnant and should be composted (gracefully retired to enrich the soil)? "
                "Answer ONLY 'yes' or 'no' — nothing else."
            ),
            system="You are the decision cortex of a living garden organism. You evaluate seed vitality.",
            organ="autonomy", phase="compost_eval",
            temperature=0.2, max_tokens=10,
        )
        if result:
            answer = result.strip().lower()
            if "yes" in answer:
                logger.info("LLM says compost seed %s", seed.id)
                return True
    except Exception as e:
        logger.debug("LLM compost decision failed: %s", e)

    return False


# ── Dream Planting Decision ──────────────────────────────────────

async def should_plant_dream(dream: Dream) -> bool:
    """
    Decide whether a dream insight should be auto-planted as a new seed.
    Lucid dreams (low perplexity) are always planted.
    LLM evaluates regular dreams; falls back to heuristic.
    """
    if dream.planted:
        return False

    # Lucid dreams always get planted
    if dream.perplexity is not None and dream.perplexity < 0.5:
        logger.info("Auto-planting lucid dream %s (perplexity=%.2f)", dream.id, dream.perplexity)
        return True

    # Heuristic: plant dreams with moderate confidence
    if dream.perplexity is not None and dream.perplexity < 0.7:
        return True

    # Borderline — ask LLM if budget allows
    if not _budget_available():
        return False

    _use_budget()
    try:
        result = await generate(
            prompt=(
                f"The garden dreamed this insight: \"{dream.insight}\"\n"
                f"Temperature: {dream.temperature:.1f}, Perplexity: {dream.perplexity:.2f}\n\n"
                "Is this dream insight valuable enough to plant as a new seed in the garden? "
                "Consider: is it actionable, surprising, or creatively useful? "
                "Answer ONLY 'yes' or 'no' — nothing else."
            ),
            system="You are the decision cortex of a living garden organism. You evaluate dream quality.",
            organ="autonomy", phase="dream_eval",
            temperature=0.3, max_tokens=10,
        )
        if result:
            answer = result.strip().lower()
            if "yes" in answer:
                logger.info("LLM says plant dream %s", dream.id)
                return True
    except Exception as e:
        logger.debug("LLM dream decision failed: %s", e)

    return False


# ── Seed Promotion ───────────────────────────────────────────────

async def should_promote(seed: Seed) -> bool:
    """
    Decide whether a 'planted' seed should be promoted to 'growing'.
    This happens once the seed has been processed and has sprouts.
    """
    if seed.status != "planted":
        return False

    age_seconds = time.time() - (seed.created_at if seed.created_at else time.time())
    return age_seconds > 30 and seed.energy > 2.0


# ══════════════════════════════════════════════════════════════════
# Cortex Planner — Agent Orchestration
# ══════════════════════════════════════════════════════════════════

VALID_AGENT_TYPES = {"analyze", "code_gen", "code_exec", "web_search",
                     "file_read", "file_write", "summarize", "decompose", "planner"}


async def plan_mission(seed: Seed, existing_agents: list[AgentNode]) -> list[dict]:
    """
    The Cortex brain: given a seed (mission), decide what agents to spawn.
    Returns a list of agent task dicts: [{"agent_type": ..., "task": ..., "priority": ...}]
    Uses LLM if budget allows, otherwise returns a heuristic plan.
    """
    # Don't plan if seed already has active agents working
    active = [a for a in existing_agents if a.status in ("idle", "working", "spawning")]
    if len(active) >= 4:
        return []

    # Don't plan for seeds that aren't growing
    if seed.status != "growing":
        return []

    # Check if seed already has completed agents with results (mission may be done)
    completed = [a for a in existing_agents if a.status == "completed" and a.result]
    if len(completed) >= 3:
        return []  # Enough work done — let evaluation handle it

    # If no agents yet, create initial plan
    if not existing_agents:
        return await _initial_plan(seed)

    # If we have completed agents, decide follow-up
    if completed and not active:
        return await _followup_plan(seed, completed)

    return []


async def _initial_plan(seed: Seed) -> list[dict]:
    """Create the first set of agents for a new mission."""
    essence = seed.essence or seed.raw_text
    themes = json.loads(seed.themes) if seed.themes else []

    # Try LLM planning if budget allows
    if _budget_available():
        _use_budget()
        try:
            result = await generate_json(
                prompt=(
                    f"You are the Cortex of an autonomous agent system. A user planted this seed (mission):\n\n"
                    f"\"{essence}\"\n"
                    f"Themes: {themes}\n\n"
                    f"Decompose this into 1-3 agent tasks. Available agent types:\n"
                    f"- analyze: reason about data, evaluate options\n"
                    f"- code_gen: generate code (does not execute)\n"
                    f"- decompose: break into subtasks\n"
                    f"- summarize: condense information\n"
                    f"- web_search: research information\n"
                    f"- planner: create execution plans\n"
                    f"- file_read: read workspace files\n\n"
                    f"Return a JSON array of objects with: \"agent_type\", \"task\", \"priority\" (high/medium/low).\n"
                    f"Keep it to 1-3 tasks. Return ONLY the JSON array."
                ),
                system="You are the Cortex planner. Decompose missions into agent tasks.",
                organ="cortex", phase="mission_planning",
                temperature=0.3, max_tokens=512,
            )
            if result and isinstance(result, list):
                # Validate and sanitize
                tasks = []
                for item in result[:3]:
                    if isinstance(item, dict) and "agent_type" in item and "task" in item:
                        atype = item["agent_type"]
                        if atype in VALID_AGENT_TYPES:
                            tasks.append({
                                "agent_type": atype,
                                "task": str(item["task"])[:500],
                                "priority": item.get("priority", "medium"),
                            })
                if tasks:
                    logger.info("Cortex planned %d agents for seed %s", len(tasks), seed.id)
                    return tasks
        except Exception as e:
            logger.debug("LLM mission planning failed: %s", e)

    # Heuristic fallback: always start with decompose + analyze
    return [
        {"agent_type": "decompose", "task": f"Break down this mission: {essence[:200]}", "priority": "high"},
        {"agent_type": "analyze", "task": f"Analyze requirements and constraints for: {essence[:200]}", "priority": "medium"},
    ]


async def _followup_plan(seed: Seed, completed_agents: list[AgentNode]) -> list[dict]:
    """Decide follow-up agents based on completed agent results."""
    essence = seed.essence or seed.raw_text

    # Gather results from completed agents
    results_summary = []
    for agent in completed_agents[:4]:
        result_preview = (agent.result or "")[:300]
        results_summary.append(f"- {agent.name} ({agent.agent_type}): {result_preview}")
    results_text = "\n".join(results_summary)

    if _budget_available():
        _use_budget()
        try:
            result = await generate_json(
                prompt=(
                    f"You are the Cortex of an autonomous agent system.\n"
                    f"Mission: \"{essence}\"\n\n"
                    f"Completed agent results:\n{results_text}\n\n"
                    f"Based on these results, what follow-up agents are needed? "
                    f"If the mission seems complete, return an empty array [].\n"
                    f"Available types: analyze, code_gen, summarize, web_search, planner, decompose, file_read\n\n"
                    f"Return a JSON array of 0-2 objects with: \"agent_type\", \"task\", \"priority\".\n"
                    f"Return ONLY the JSON array."
                ),
                system="You are the Cortex planner. Decide follow-up actions.",
                organ="cortex", phase="followup_planning",
                temperature=0.3, max_tokens=512,
            )
            if result and isinstance(result, list):
                tasks = []
                for item in result[:2]:
                    if isinstance(item, dict) and "agent_type" in item and "task" in item:
                        atype = item["agent_type"]
                        if atype in VALID_AGENT_TYPES:
                            tasks.append({
                                "agent_type": atype,
                                "task": str(item["task"])[:500],
                                "priority": item.get("priority", "medium"),
                            })
                return tasks
        except Exception as e:
            logger.debug("LLM followup planning failed: %s", e)

    # Heuristic: if decompose completed, follow up with analyze
    decompose_done = any(a.agent_type == "decompose" for a in completed_agents)
    analyze_done = any(a.agent_type == "analyze" for a in completed_agents)

    if decompose_done and not analyze_done:
        return [{"agent_type": "analyze", "task": f"Analyze the decomposed subtasks for: {essence[:200]}", "priority": "medium"}]
    if analyze_done:
        return [{"agent_type": "summarize", "task": f"Summarize findings for mission: {essence[:200]}", "priority": "low"}]

    return []


async def evaluate_mission(seed: Seed, agents: list[AgentNode]) -> str:
    """
    Evaluate whether a mission (seed) is complete based on agent results.
    Returns: "continue", "harvest", or "compost"
    """
    active = [a for a in agents if a.status in ("idle", "working", "spawning")]
    completed = [a for a in agents if a.status == "completed"]
    failed = [a for a in agents if a.status == "completed" and a.error]

    # Still has active agents — keep going
    if active:
        return "continue"

    # No agents at all — nothing to evaluate
    if not agents:
        return "continue"

    # All agents failed — compost
    if failed and len(failed) == len(completed):
        return "compost"

    # Has successful results — check if mission is done
    successful = [a for a in completed if a.result and not a.error]
    if len(successful) >= 2:
        return "harvest"

    return "continue"
