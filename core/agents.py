"""
Agent Registry — The Spawning Ground

Manages the lifecycle of dynamic agent nodes: spawn, execute, complete, retire.
The Cortex uses this registry to create worker agents that accomplish real tasks.
Each agent has a type, capability, and task — and reports results back.
"""

from __future__ import annotations

import json
import logging
import time

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from models.db_models import AgentNode

logger = logging.getLogger("w0rd.agents")

# Agent types and their descriptions
AGENT_TYPES = {
    "analyze":    "Reason about data, evaluate options, draw conclusions",
    "code_gen":   "Generate code snippets based on requirements",
    "code_exec":  "Execute Python code in a sandboxed subprocess",
    "web_search": "Search the web for information",
    "file_read":  "Read files from the workspace",
    "file_write": "Write files to the workspace",
    "summarize":  "Condense large text into key points",
    "decompose":  "Break a complex task into subtasks",
    "planner":    "Create execution plans for missions",
}

# Capabilities that require user approval before execution
GATED_CAPABILITIES = {"code_exec", "file_write"}

# Safe capabilities that can auto-execute
SAFE_CAPABILITIES = {"analyze", "code_gen", "web_search", "file_read", "summarize", "decompose", "planner"}

MAX_CONCURRENT_AGENTS = 8


class AgentRegistry:
    """
    The organism's agent spawning and management system.

    - spawn(): create a new agent node
    - start_work(): transition agent to working state
    - complete(): mark agent as done with results
    - retire(): gracefully retire an agent
    - get_active(): list all non-retired agents
    """

    def __init__(self, bus: HormoneBus):
        self.bus = bus
        self._agent_counter: dict[str, int] = {}  # type → count for naming

    def _next_name(self, agent_type: str) -> str:
        """Generate a sequential name like 'analyzer_03'."""
        count = self._agent_counter.get(agent_type, 0) + 1
        self._agent_counter[agent_type] = count
        return f"{agent_type}_{count:02d}"

    # ── Spawn ──────────────────────────────────────────────────────

    async def spawn(
        self,
        session: AsyncSession,
        agent_type: str,
        task_description: str,
        seed_id: str | None = None,
        parent_id: str | None = None,
        capability_config: dict | None = None,
    ) -> AgentNode | None:
        """
        Spawn a new agent node. Returns None if at capacity or invalid type.
        """
        if agent_type not in AGENT_TYPES:
            logger.warning("Unknown agent type: %s", agent_type)
            return None

        # Check capacity
        active_count = await self._count_active(session)
        if active_count >= MAX_CONCURRENT_AGENTS:
            logger.debug("Agent capacity reached (%d/%d), skipping %s",
                          active_count, MAX_CONCURRENT_AGENTS, agent_type)
            return None

        name = self._next_name(agent_type)
        initial_status = "awaiting_approval" if agent_type in GATED_CAPABILITIES else "idle"

        agent = AgentNode(
            name=name,
            agent_type=agent_type,
            status=initial_status,
            seed_id=seed_id,
            parent_id=parent_id,
            task_description=task_description,
            capability=json.dumps(capability_config or {}),
        )
        session.add(agent)
        await session.flush()

        await self.bus.signal(
            "agent_spawned",
            payload={
                "agent_id": agent.id,
                "name": agent.name,
                "agent_type": agent_type,
                "seed_id": seed_id,
                "task": task_description,
                "status": initial_status,
            },
            emitter="agents",
        )

        logger.info("Spawned agent %s (%s) for seed %s: %s",
                     name, agent_type, seed_id, task_description[:80])
        return agent

    # ── State Transitions ──────────────────────────────────────────

    async def start_work(self, session: AsyncSession, agent_id: str) -> AgentNode | None:
        """Transition agent from idle → working."""
        agent = await self._get_agent(session, agent_id)
        if not agent or agent.status not in ("idle", "spawning"):
            return None

        agent.status = "working"
        agent.started_at = time.time()
        await session.flush()

        await self.bus.signal(
            "agent_working",
            payload={"agent_id": agent.id, "name": agent.name, "agent_type": agent.agent_type},
            emitter="agents",
        )
        return agent

    async def complete(
        self,
        session: AsyncSession,
        agent_id: str,
        result: str,
        context_update: dict | None = None,
    ) -> AgentNode | None:
        """Mark agent as completed with results."""
        agent = await self._get_agent(session, agent_id)
        if not agent:
            return None

        agent.status = "completed"
        agent.result = result
        agent.completed_at = time.time()

        if context_update:
            ctx = json.loads(agent.context or "{}")
            ctx.update(context_update)
            agent.context = json.dumps(ctx)

        await session.flush()

        await self.bus.signal(
            "agent_completed",
            payload={
                "agent_id": agent.id,
                "name": agent.name,
                "agent_type": agent.agent_type,
                "seed_id": agent.seed_id,
                "result_preview": result[:200],
            },
            emitter="agents",
        )

        logger.info("Agent %s completed: %s", agent.name, result[:100])
        return agent

    async def fail(self, session: AsyncSession, agent_id: str, error: str) -> AgentNode | None:
        """Mark agent as failed."""
        agent = await self._get_agent(session, agent_id)
        if not agent:
            return None

        agent.status = "completed"
        agent.error = error
        agent.completed_at = time.time()
        await session.flush()

        logger.warning("Agent %s failed: %s", agent.name, error[:100])
        return agent

    async def retire(self, session: AsyncSession, agent_id: str, reason: str = "") -> AgentNode | None:
        """Retire an agent — remove it from the active pool."""
        agent = await self._get_agent(session, agent_id)
        if not agent or agent.status == "retired":
            return None

        agent.status = "retired"
        agent.retired_at = time.time()
        await session.flush()

        await self.bus.signal(
            "agent_retired",
            payload={"agent_id": agent.id, "name": agent.name, "reason": reason},
            emitter="agents",
        )

        logger.info("Retired agent %s: %s", agent.name, reason or "mission complete")
        return agent

    async def approve(self, session: AsyncSession, agent_id: str, approved: bool) -> AgentNode | None:
        """Handle user approval for gated capabilities."""
        agent = await self._get_agent(session, agent_id)
        if not agent or agent.status != "awaiting_approval":
            return None

        if approved:
            agent.status = "idle"
            logger.info("Agent %s approved by user", agent.name)
        else:
            agent.status = "retired"
            agent.retired_at = time.time()
            agent.error = "Denied by user"
            logger.info("Agent %s denied by user", agent.name)

        await session.flush()
        return agent

    # ── Queries ────────────────────────────────────────────────────

    async def get_active(self, session: AsyncSession) -> list[AgentNode]:
        """Get all non-retired agents."""
        result = await session.execute(
            select(AgentNode).where(AgentNode.status != "retired")
        )
        return list(result.scalars().all())

    async def get_for_seed(self, session: AsyncSession, seed_id: str) -> list[AgentNode]:
        """Get all active agents working on a specific seed."""
        result = await session.execute(
            select(AgentNode).where(
                AgentNode.seed_id == seed_id,
                AgentNode.status != "retired",
            )
        )
        return list(result.scalars().all())

    async def get_idle(self, session: AsyncSession) -> list[AgentNode]:
        """Get agents ready to work."""
        result = await session.execute(
            select(AgentNode).where(AgentNode.status == "idle")
        )
        return list(result.scalars().all())

    async def get_completed(self, session: AsyncSession) -> list[AgentNode]:
        """Get agents that finished but haven't been retired yet."""
        result = await session.execute(
            select(AgentNode).where(AgentNode.status == "completed")
        )
        return list(result.scalars().all())

    async def get_awaiting_approval(self, session: AsyncSession) -> list[AgentNode]:
        """Get agents waiting for user approval."""
        result = await session.execute(
            select(AgentNode).where(AgentNode.status == "awaiting_approval")
        )
        return list(result.scalars().all())

    # ── Internal ───────────────────────────────────────────────────

    async def _get_agent(self, session: AsyncSession, agent_id: str) -> AgentNode | None:
        result = await session.execute(select(AgentNode).where(AgentNode.id == agent_id))
        return result.scalar_one_or_none()

    async def _count_active(self, session: AsyncSession) -> int:
        result = await session.execute(
            select(func.count(AgentNode.id)).where(AgentNode.status.notin_(["retired", "completed"]))
        )
        return result.scalar() or 0
