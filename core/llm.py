"""
LLM Cortex — The Language Center

Async client for Ollama local inference. Provides streaming generation
with thinking-event callbacks so the frontend can visualize the system's
thought process in real time.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncIterator, Callable, Awaitable

import httpx

logger = logging.getLogger("w0rd.llm")

OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"


class ThinkingEvent:
    """A single unit of thought — streamed to the frontend."""

    __slots__ = ("organ", "phase", "token", "content", "timestamp", "meta")

    def __init__(
        self,
        organ: str,
        phase: str,
        token: str = "",
        content: str = "",
        meta: dict | None = None,
    ):
        self.organ = organ
        self.phase = phase
        self.token = token
        self.content = content
        self.timestamp = time.time()
        self.meta = meta or {}

    def to_dict(self) -> dict:
        return {
            "organ": self.organ,
            "phase": self.phase,
            "token": self.token,
            "content": self.content,
            "timestamp": self.timestamp,
            "meta": self.meta,
        }


# Type alias for thinking callbacks
ThinkingCallback = Callable[[ThinkingEvent], Awaitable[None]]

# Global thinking listeners
_thinking_listeners: list[ThinkingCallback] = []


def on_thinking(callback: ThinkingCallback) -> None:
    """Register a callback for thinking events."""
    _thinking_listeners.append(callback)


def remove_thinking_listener(callback: ThinkingCallback) -> None:
    """Remove a thinking callback."""
    if callback in _thinking_listeners:
        _thinking_listeners.remove(callback)


async def _emit_thinking(event: ThinkingEvent) -> None:
    """Broadcast a thinking event to all listeners."""
    for cb in _thinking_listeners:
        try:
            await cb(event)
        except Exception:
            pass


async def generate(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    organ: str = "cortex",
    phase: str = "generating",
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> str:
    """
    Generate text from Ollama with streaming thinking events.
    Returns the full response text.
    """
    await _emit_thinking(ThinkingEvent(
        organ=organ, phase="start",
        content=f"Thinking about: {prompt[:80]}...",
        meta={"model": model, "temperature": temperature},
    ))

    full_response = ""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            if system:
                payload["system"] = system

            async with client.stream(
                "POST", f"{OLLAMA_BASE}/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    token = chunk.get("response", "")
                    if token:
                        full_response += token
                        await _emit_thinking(ThinkingEvent(
                            organ=organ, phase=phase,
                            token=token, content=full_response,
                        ))

                    if chunk.get("done", False):
                        break

    except httpx.ConnectError:
        logger.warning("Ollama not reachable at %s — falling back to template", OLLAMA_BASE)
        await _emit_thinking(ThinkingEvent(
            organ=organ, phase="fallback",
            content="Ollama unavailable, using template fallback",
        ))
        return ""
    except Exception as e:
        logger.error("LLM generation failed: %s", e)
        await _emit_thinking(ThinkingEvent(
            organ=organ, phase="error",
            content=str(e),
        ))
        return ""

    await _emit_thinking(ThinkingEvent(
        organ=organ, phase="complete",
        content=full_response,
        meta={"total_tokens": len(full_response.split())},
    ))

    return full_response.strip()


async def generate_json(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    organ: str = "cortex",
    phase: str = "analyzing",
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> dict | list | None:
    """
    Generate structured JSON from Ollama.
    Attempts to parse the response as JSON, returns None on failure.
    """
    raw = await generate(
        prompt=prompt, system=system, model=model,
        organ=organ, phase=phase,
        temperature=temperature, max_tokens=max_tokens,
    )
    if not raw:
        return None

    # Try to extract JSON from the response
    try:
        # Look for JSON block in markdown code fences
        if "```json" in raw:
            start = raw.index("```json") + 7
            end = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        if "```" in raw:
            start = raw.index("```") + 3
            end = raw.index("```", start)
            return json.loads(raw[start:end].strip())
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        logger.debug("Failed to parse JSON from LLM response: %s", raw[:200])
        return None


async def check_ollama() -> dict:
    """Check if Ollama is running and which models are available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"status": "online", "models": models}
    except Exception as e:
        return {"status": "offline", "error": str(e), "models": []}
