"""
Vascular Grower — The Branching Tissue

Takes a Seed and grows it into a living fractal tree of Sprout nodes.
Golden-ratio (phi = 1.618) weighted branching with pressure-gradient growth.
Depth bounded by available energy — no infinite growth.
"""

from __future__ import annotations

import json
import logging
import math

from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from core.llm import generate_json
from models.db_models import Seed, Sprout

logger = logging.getLogger("w0rd.fractal")

PHI = (1 + math.sqrt(5)) / 2  # 1.6180339887...

# ── Decomposition Templates ──────────────────────────────────────
# Each depth level has a role in the fractal hierarchy:
# 0: Intentions (why)
# 1: Goals (what)
# 2: Tasks (how)
# 3: Actions (do)

DEPTH_LABELS = {
    0: "intention",
    1: "goal",
    2: "task",
    3: "action",
}

# Theme-aware decomposition patterns
DECOMPOSITION_PATTERNS: dict[str, list[list[str]]] = {
    "creativity": [
        ["Envision the creative spark", "Gather inspiration and materials"],
        ["Define the medium and form", "Sketch the first draft"],
        ["Refine and iterate", "Share with others for feedback"],
        ["Polish the final piece", "Release into the world"],
    ],
    "connection": [
        ["Understand the longing for connection", "Identify who to connect with"],
        ["Reach out with vulnerability", "Create shared experiences"],
        ["Deepen through honest conversation", "Build rituals of togetherness"],
        ["Sustain through consistent presence", "Celebrate the bond"],
    ],
    "health": [
        ["Listen to the body's signals", "Acknowledge what needs healing"],
        ["Research gentle approaches", "Choose one small daily practice"],
        ["Build the habit with compassion", "Track progress without judgment"],
        ["Integrate into lifestyle", "Share what works with others"],
    ],
    "growth": [
        ["Recognize the desire to evolve", "Name what growth looks like"],
        ["Find a teacher or resource", "Take the first uncomfortable step"],
        ["Practice consistently", "Reflect on what's changing"],
        ["Teach what you've learned", "Set the next horizon"],
    ],
    "general": [
        ["Clarify the true desire", "Feel into what matters most"],
        ["Break it into reachable pieces", "Identify the first step"],
        ["Take action with presence", "Adjust based on feedback"],
        ["Complete and celebrate", "Plant the next seed"],
    ],
}


def _get_pattern(themes: list[str]) -> list[list[str]]:
    """Select decomposition pattern based on primary theme."""
    for theme in themes:
        if theme in DECOMPOSITION_PATTERNS:
            return DECOMPOSITION_PATTERNS[theme]
    return DECOMPOSITION_PATTERNS["general"]


def _phi_weight(birth_order: int, parent_energy: float) -> float:
    """
    Golden-ratio energy distribution.
    Each sibling gets parent_energy / phi^birth_order.
    First child gets the most, naturally diminishing.
    """
    weight = parent_energy / (PHI ** birth_order)
    return round(max(weight, 0.1), 4)


def _pressure_score(depth: int, sibling_index: int, total_siblings: int) -> float:
    """
    Pressure-gradient: nodes at greater depth or later birth order
    have higher pressure (more unmet need), driving growth toward them.
    """
    depth_pressure = 1.0 / (1.0 + depth * 0.3)
    position_pressure = (sibling_index + 1) / max(total_siblings, 1)
    return round(depth_pressure * (1 - 0.3 * position_pressure), 4)


async def _llm_decompose(essence: str, themes: list[str]) -> list[list[str]] | None:
    """Use LLM to decompose a wish into a fractal tree of intentions/goals/tasks/actions."""
    theme_str = ", ".join(themes) if themes else "general"
    result = await generate_json(
        prompt=(
            f"A wish has been planted: \"{essence}\"\n"
            f"Themes: {theme_str}\n\n"
            "Decompose this into a fractal growth tree. Return JSON as an array of 4 arrays:\n"
            "- Level 0: 2 core intentions (WHY — the deep motivations)\n"
            "- Level 1: 2 concrete goals (WHAT — measurable outcomes)\n"
            "- Level 2: 2 practical tasks (HOW — specific steps)\n"
            "- Level 3: 2 immediate actions (DO — things to start today)\n\n"
            "Each item should be a vivid, specific sentence (8-15 words). "
            "Make them deeply personal and actionable, not generic.\n"
            "Return ONLY a JSON array of 4 arrays, no explanation.\n"
            'Example: [["intention1", "intention2"], ["goal1", "goal2"], ["task1", "task2"], ["action1", "action2"]]'
        ),
        system="You are the vascular growth tissue of a living organism. You decompose dreams into living branches.",
        organ="fractal", phase="decomposing",
        temperature=0.5, max_tokens=512,
    )
    if isinstance(result, list) and len(result) >= 2:
        # Validate structure: should be list of lists of strings
        validated = []
        for level in result[:4]:
            if isinstance(level, list):
                validated.append([str(item) for item in level[:4]])
            else:
                return None
        return validated
    return None


class VascularGrower:
    """Grows Seeds into fractal Sprout trees using phi-weighted branching."""

    def __init__(self, bus: HormoneBus, max_depth: int = 3):
        self.bus = bus
        self.max_depth = max_depth

    async def grow(self, session: AsyncSession, seed: Seed) -> list[Sprout]:
        """
        Grow a full fractal tree from a seed.
        Returns all created sprouts.
        """
        themes = json.loads(seed.themes or '["general"]')

        # Try LLM decomposition first, fall back to templates
        llm_pattern = await _llm_decompose(seed.essence or seed.raw_text, themes)
        pattern = llm_pattern if llm_pattern else _get_pattern(themes)

        all_sprouts: list[Sprout] = []

        # Energy budget: deeper levels cost exponentially more
        available_energy = seed.energy

        # Grow the tree level by level
        parent_ids: list[str | None] = [None]  # root level has no parent
        parent_energies: list[float] = [available_energy]

        for depth in range(min(self.max_depth + 1, len(pattern))):
            level_descriptions = pattern[depth] if depth < len(pattern) else ["Continue growing"]
            next_parent_ids: list[str] = []
            next_parent_energies: list[float] = []

            for parent_idx, (parent_id, parent_energy) in enumerate(zip(parent_ids, parent_energies)):
                # Energy cost for this depth level
                depth_cost = PHI ** depth
                if parent_energy < depth_cost:
                    continue  # Not enough energy to branch here

                for sibling_idx, desc in enumerate(level_descriptions):
                    child_energy = _phi_weight(sibling_idx, parent_energy / len(level_descriptions))
                    pressure = _pressure_score(depth, sibling_idx, len(level_descriptions))

                    depth_label = DEPTH_LABELS.get(depth, "sprout")
                    label = f"{depth_label}_{depth}_{sibling_idx}"

                    sprout = Sprout(
                        seed_id=seed.id,
                        parent_id=parent_id,
                        depth=depth,
                        label=label,
                        description=desc,
                        energy=child_energy,
                        ethical_score=seed.ethical_score,
                        pressure=pressure,
                        resonance=seed.resonance,
                        status="budding",
                    )
                    session.add(sprout)
                    await session.flush()

                    all_sprouts.append(sprout)
                    next_parent_ids.append(sprout.id)
                    next_parent_energies.append(child_energy)

            parent_ids = next_parent_ids
            parent_energies = next_parent_energies

            if not parent_ids:
                break  # No energy left to grow deeper

        # Update seed status
        seed.status = "growing"
        await session.flush()

        await self.bus.signal(
            "tree_grown",
            payload={
                "seed_id": seed.id,
                "sprout_count": len(all_sprouts),
                "max_depth_reached": max((s.depth for s in all_sprouts), default=0),
            },
            emitter="fractal",
        )

        logger.info(
            "Grew %d sprouts for seed %s (max depth %d)",
            len(all_sprouts),
            seed.id,
            max((s.depth for s in all_sprouts), default=0),
        )
        return all_sprouts

    async def trigger_apoptosis(
        self, session: AsyncSession, sprout: Sprout, reason: str = "energy_depleted"
    ) -> None:
        """Programmed cell death — gracefully terminate a sprout."""
        import time

        sprout.status = "composted"
        sprout.is_composted = True
        sprout.apoptosis_at = time.time()
        await session.flush()

        await self.bus.signal(
            "apoptosis",
            payload={"sprout_id": sprout.id, "seed_id": sprout.seed_id, "reason": reason},
            emitter="fractal",
        )

        logger.info("Apoptosis: sprout %s (%s) — %s", sprout.id, sprout.label, reason)
