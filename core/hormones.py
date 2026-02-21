"""
Hormone Bus — The Nervous/Endocrine System

Async pub/sub event bus enabling organic, decoupled communication between
all organs. Any organ can emit a hormone signal and any other organ can
subscribe to it. Supports instant and slow-release hormone types.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger("w0rd.hormones")


class HormoneType(str, Enum):
    INSTANT = "instant"
    SLOW_RELEASE = "slow_release"


@dataclass
class Hormone:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    emitter: str = "unknown"
    hormone_type: HormoneType = HormoneType.INSTANT
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    depth: int = 0


# Type alias for subscriber callbacks
HormoneCallback = Callable[[Hormone], Coroutine[Any, Any, None]]


class HormoneBus:
    """
    The organism's async event signaling system.

    - emit(): broadcast a hormone to all subscribers
    - subscribe(): register a callback for a hormone name
    - Cascade prevention via configurable max_depth
    - Slow-release hormones are batched and flushed on demand
    - Full hormone history for consciousness to analyze
    """

    def __init__(self, max_cascade_depth: int = 8):
        self._subscribers: dict[str, list[HormoneCallback]] = {}
        self._slow_release_queue: asyncio.Queue[Hormone] = asyncio.Queue()
        self._history: list[Hormone] = []
        self._max_depth = max_cascade_depth
        self._running = False
        self._flush_task: asyncio.Task | None = None

    # ── Subscription ──────────────────────────────────────────────

    def subscribe(self, hormone_name: str, callback: HormoneCallback) -> None:
        if hormone_name not in self._subscribers:
            self._subscribers[hormone_name] = []
        self._subscribers[hormone_name].append(callback)
        logger.debug("Subscribed to '%s': %s", hormone_name, callback.__qualname__)

    def unsubscribe(self, hormone_name: str, callback: HormoneCallback) -> None:
        if hormone_name in self._subscribers:
            self._subscribers[hormone_name] = [
                cb for cb in self._subscribers[hormone_name] if cb is not callback
            ]

    # ── Emission ──────────────────────────────────────────────────

    async def emit(self, hormone: Hormone) -> None:
        if hormone.depth > self._max_depth:
            logger.warning(
                "Cascade depth %d exceeded max %d for '%s' — suppressing",
                hormone.depth,
                self._max_depth,
                hormone.name,
            )
            return

        self._history.append(hormone)

        if hormone.hormone_type == HormoneType.SLOW_RELEASE:
            await self._slow_release_queue.put(hormone)
            logger.debug("Queued slow-release hormone: %s", hormone.name)
            return

        await self._dispatch(hormone)

    async def _dispatch(self, hormone: Hormone) -> None:
        callbacks = self._subscribers.get(hormone.name, [])
        if not callbacks:
            return

        logger.debug(
            "Dispatching '%s' from %s to %d subscribers",
            hormone.name,
            hormone.emitter,
            len(callbacks),
        )

        tasks = [asyncio.create_task(cb(hormone)) for cb in callbacks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Subscriber %s raised %s on hormone '%s': %s",
                    callbacks[i].__qualname__,
                    type(result).__name__,
                    hormone.name,
                    result,
                )

    # ── Slow-Release Flush ────────────────────────────────────────

    async def flush_slow_release(self) -> int:
        """Process all queued slow-release hormones. Returns count flushed."""
        flushed = 0
        while not self._slow_release_queue.empty():
            try:
                hormone = self._slow_release_queue.get_nowait()
                await self._dispatch(hormone)
                flushed += 1
            except asyncio.QueueEmpty:
                break
        if flushed:
            logger.info("Flushed %d slow-release hormones", flushed)
        return flushed

    # ── Convenience Emitters ──────────────────────────────────────

    async def signal(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        emitter: str = "unknown",
        hormone_type: HormoneType = HormoneType.INSTANT,
        parent_depth: int = 0,
    ) -> None:
        """Convenience method to emit a hormone without constructing one."""
        await self.emit(
            Hormone(
                name=name,
                payload=payload or {},
                emitter=emitter,
                hormone_type=hormone_type,
                depth=parent_depth + 1,
            )
        )

    # ── History & Introspection ───────────────────────────────────

    @property
    def history(self) -> list[Hormone]:
        return list(self._history)

    def recent(self, n: int = 50) -> list[Hormone]:
        return self._history[-n:]

    def history_for(self, hormone_name: str) -> list[Hormone]:
        return [h for h in self._history if h.name == hormone_name]

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def subscriber_count(self) -> dict[str, int]:
        return {name: len(cbs) for name, cbs in self._subscribers.items()}

    # ── Lifecycle ─────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        logger.info("Hormone Bus started")

    async def stop(self) -> None:
        self._running = False
        await self.flush_slow_release()
        logger.info("Hormone Bus stopped")
