"""
Agent Capabilities — What Agents Can Actually Do

Each capability is an async function that takes an AgentNode and params,
executes the work, and returns a result dict. Safe capabilities auto-execute;
gated capabilities require user approval first.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

from core.llm import generate, generate_json

logger = logging.getLogger("w0rd.capabilities")

# Workspace root for file operations (scoped for safety)
WORKSPACE_ROOT = Path(os.getenv("W0RD_WORKSPACE", "./workspace"))


# ── Capability Registry ──────────────────────────────────────────

_capabilities: dict[str, object] = {}


def capability(name: str):
    """Decorator to register a capability function."""
    def decorator(fn):
        _capabilities[name] = fn
        return fn
    return decorator


async def execute_capability(agent_type: str, params: dict) -> dict:
    """
    Execute a capability by name. Returns {"success": bool, "result": str, ...}
    """
    fn = _capabilities.get(agent_type)
    if not fn:
        return {"success": False, "result": "", "error": f"Unknown capability: {agent_type}"}
    try:
        return await fn(params)
    except Exception as e:
        logger.exception("Capability %s failed", agent_type)
        return {"success": False, "result": "", "error": str(e)}


# ── Safe Capabilities ────────────────────────────────────────────

@capability("analyze")
async def cap_analyze(params: dict) -> dict:
    """LLM-powered analysis/reasoning on provided data."""
    task = params.get("task", "")
    data = params.get("data", "")

    prompt = (
        f"You are an analytical agent in a living system. Your task:\n\n"
        f"{task}\n\n"
    )
    if data:
        prompt += f"Data to analyze:\n{data[:3000]}\n\n"
    prompt += "Provide a clear, structured analysis. Be concise and actionable."

    result = await generate(
        prompt=prompt,
        system="You are a precise analytical agent. Provide structured, actionable analysis.",
        organ="cortex", phase="analyzing",
        temperature=0.4, max_tokens=1024,
    )
    return {"success": bool(result), "result": result or "Analysis failed — LLM unavailable"}


@capability("summarize")
async def cap_summarize(params: dict) -> dict:
    """Condense text into key points."""
    text = params.get("text", "")
    max_points = params.get("max_points", 5)

    if not text:
        return {"success": False, "result": "", "error": "No text provided"}

    result = await generate(
        prompt=(
            f"Summarize the following into {max_points} key points:\n\n"
            f"{text[:4000]}\n\n"
            "Format as a numbered list. Be concise."
        ),
        system="You are a summarization agent. Extract the most important points.",
        organ="cortex", phase="summarizing",
        temperature=0.3, max_tokens=512,
    )
    return {"success": bool(result), "result": result or "Summarization failed"}


@capability("decompose")
async def cap_decompose(params: dict) -> dict:
    """Break a complex task into subtasks."""
    task = params.get("task", "")
    max_subtasks = params.get("max_subtasks", 6)

    if not task:
        return {"success": False, "result": "", "error": "No task provided"}

    result = await generate_json(
        prompt=(
            f"Break this task into {max_subtasks} or fewer concrete subtasks:\n\n"
            f"\"{task}\"\n\n"
            "Return a JSON array of objects, each with:\n"
            "- \"task\": description of the subtask\n"
            "- \"agent_type\": best agent type (analyze, code_gen, summarize, web_search, file_read, file_write)\n"
            "- \"priority\": \"high\", \"medium\", or \"low\"\n\n"
            "Return ONLY the JSON array."
        ),
        system="You are a task decomposition agent. Break complex tasks into actionable subtasks.",
        organ="cortex", phase="decomposing",
        temperature=0.3, max_tokens=1024,
    )

    if result and isinstance(result, list):
        return {
            "success": True,
            "result": json.dumps(result, indent=2),
            "subtasks": result,
        }

    # Fallback: return as text
    text_result = await generate(
        prompt=(
            f"Break this task into {max_subtasks} or fewer concrete subtasks:\n\n"
            f"\"{task}\"\n\n"
            "List each subtask with what type of agent should handle it."
        ),
        system="You are a task decomposition agent.",
        organ="cortex", phase="decomposing",
        temperature=0.3, max_tokens=512,
    )
    return {"success": bool(text_result), "result": text_result or "Decomposition failed"}


@capability("code_gen")
async def cap_code_gen(params: dict) -> dict:
    """Generate code based on requirements (does NOT execute)."""
    task = params.get("task", "")
    language = params.get("language", "python")
    context = params.get("context", "")

    prompt = (
        f"Generate {language} code for the following requirement:\n\n"
        f"{task}\n\n"
    )
    if context:
        prompt += f"Context/existing code:\n```\n{context[:2000]}\n```\n\n"
    prompt += (
        "Return ONLY the code in a code block. Include necessary imports. "
        "Make it production-ready, well-structured, and commented."
    )

    result = await generate(
        prompt=prompt,
        system=f"You are an expert {language} developer. Generate clean, working code.",
        organ="cortex", phase="coding",
        temperature=0.3, max_tokens=2048,
    )
    return {"success": bool(result), "result": result or "Code generation failed"}


@capability("planner")
async def cap_planner(params: dict) -> dict:
    """Create an execution plan for a mission."""
    mission = params.get("mission", "")
    constraints = params.get("constraints", "")

    prompt = (
        f"Create a detailed execution plan for this mission:\n\n"
        f"\"{mission}\"\n\n"
    )
    if constraints:
        prompt += f"Constraints: {constraints}\n\n"
    prompt += (
        "Include:\n"
        "1. Goal statement\n"
        "2. Step-by-step plan with agent types needed\n"
        "3. Success criteria\n"
        "4. Risk factors\n"
        "Be specific and actionable."
    )

    result = await generate(
        prompt=prompt,
        system="You are a strategic planning agent. Create clear, actionable plans.",
        organ="cortex", phase="planning",
        temperature=0.4, max_tokens=1024,
    )
    return {"success": bool(result), "result": result or "Planning failed"}


@capability("web_search")
async def cap_web_search(params: dict) -> dict:
    """Search the web for information. Currently a stub — returns LLM knowledge."""
    query = params.get("query", "")

    if not query:
        return {"success": False, "result": "", "error": "No query provided"}

    # For now, use LLM knowledge as a proxy for web search
    # TODO: integrate actual web search API (SearXNG, Brave, etc.)
    result = await generate(
        prompt=(
            f"Answer this question using your knowledge:\n\n"
            f"\"{query}\"\n\n"
            "Provide factual, well-sourced information. Note when you're uncertain."
        ),
        system="You are a research agent. Provide accurate, factual information.",
        organ="cortex", phase="researching",
        temperature=0.3, max_tokens=1024,
    )
    return {"success": bool(result), "result": result or "Search failed"}


@capability("file_read")
async def cap_file_read(params: dict) -> dict:
    """Read a file from the workspace directory."""
    filepath = params.get("path", "")

    if not filepath:
        return {"success": False, "result": "", "error": "No path provided"}

    # Scope to workspace
    target = (WORKSPACE_ROOT / filepath).resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT.resolve())):
        return {"success": False, "result": "", "error": "Path outside workspace"}

    if not target.exists():
        return {"success": False, "result": "", "error": f"File not found: {filepath}"}

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        # Truncate very large files
        if len(content) > 10000:
            content = content[:10000] + f"\n\n... [truncated, {len(content)} chars total]"
        return {"success": True, "result": content}
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}


# ── Gated Capabilities (require user approval) ───────────────────

@capability("code_exec")
async def cap_code_exec(params: dict) -> dict:
    """Execute Python code in a sandboxed subprocess."""
    code = params.get("code", "")
    timeout = min(params.get("timeout", 30), 60)  # max 60s

    if not code:
        return {"success": False, "result": "", "error": "No code provided"}

    # Write code to temp file and execute in subprocess
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(WORKSPACE_ROOT),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        output = stdout.decode("utf-8", errors="replace")
        errors = stderr.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            return {"success": True, "result": output, "stderr": errors}
        else:
            return {"success": False, "result": output, "error": errors}
    except asyncio.TimeoutError:
        proc.kill()
        return {"success": False, "result": "", "error": f"Execution timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@capability("file_write")
async def cap_file_write(params: dict) -> dict:
    """Write content to a file in the workspace directory."""
    filepath = params.get("path", "")
    content = params.get("content", "")

    if not filepath:
        return {"success": False, "result": "", "error": "No path provided"}

    # Scope to workspace
    target = (WORKSPACE_ROOT / filepath).resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT.resolve())):
        return {"success": False, "result": "", "error": "Path outside workspace"}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"success": True, "result": f"Written {len(content)} chars to {filepath}"}
    except Exception as e:
        return {"success": False, "result": "", "error": str(e)}
