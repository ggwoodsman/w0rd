"""Tests for the Hormone Bus — the nervous system."""

import pytest
import pytest_asyncio

from core.hormones import Hormone, HormoneBus, HormoneType


@pytest.mark.asyncio
async def test_emit_and_subscribe():
    bus = HormoneBus()
    await bus.start()
    received = []

    async def handler(h: Hormone):
        received.append(h)

    bus.subscribe("test_signal", handler)
    await bus.signal("test_signal", {"key": "value"}, emitter="test")

    assert len(received) == 1
    assert received[0].name == "test_signal"
    assert received[0].payload == {"key": "value"}
    await bus.stop()


@pytest.mark.asyncio
async def test_cascade_depth_prevention():
    bus = HormoneBus(max_cascade_depth=2)
    await bus.start()
    received = []

    async def handler(h: Hormone):
        received.append(h)

    bus.subscribe("deep", handler)

    # Depth 1 — should work
    await bus.emit(Hormone(name="deep", depth=1))
    assert len(received) == 1

    # Depth 3 — should be suppressed
    await bus.emit(Hormone(name="deep", depth=3))
    assert len(received) == 1  # still 1
    await bus.stop()


@pytest.mark.asyncio
async def test_slow_release():
    bus = HormoneBus()
    await bus.start()
    received = []

    async def handler(h: Hormone):
        received.append(h)

    bus.subscribe("slow", handler)
    await bus.signal("slow", {"x": 1}, hormone_type=HormoneType.SLOW_RELEASE)

    # Not dispatched yet
    assert len(received) == 0

    # Flush
    flushed = await bus.flush_slow_release()
    assert flushed == 1
    assert len(received) == 1
    await bus.stop()


@pytest.mark.asyncio
async def test_history():
    bus = HormoneBus()
    await bus.start()
    await bus.signal("a", emitter="test")
    await bus.signal("b", emitter="test")
    await bus.signal("a", emitter="test")

    assert len(bus.history) == 3
    assert len(bus.history_for("a")) == 2
    assert len(bus.recent(2)) == 2
    await bus.stop()


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = HormoneBus()
    await bus.start()
    received = []

    async def handler(h: Hormone):
        received.append(h)

    bus.subscribe("unsub_test", handler)
    await bus.signal("unsub_test")
    assert len(received) == 1

    bus.unsubscribe("unsub_test", handler)
    await bus.signal("unsub_test")
    assert len(received) == 1  # no new delivery
    await bus.stop()
