# src/agent/agent.py — ReAct Travel Agent
# Thought → Action → Observation loop, works with the existing LLMProvider interface.

import os, re, json, inspect, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.agent.tools import TOOLS
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger          # structured JSON logger → logs/
from src.telemetry.metrics import tracker        # perf tracker with real cost calc

# ── System Prompt (auto-built from tool signatures) ───────────────────────────

def _build_tool_docs() -> str:
    return "\n".join(
        f"  {name}{inspect.signature(fn)}  — {inspect.getdoc(fn) or ''}"
        for name, fn in TOOLS.items()
    )

SYSTEM_PROMPT = f"""You are a travel assistant. Reason step-by-step using these tools:
{_build_tool_docs()}

Each reply must be ONLY a raw JSON object — no markdown fences, no prose:
  {{ "thought": "...", "action": "tool_name", "action_input": {{ ... }} }}
Or to finish:
  {{ "thought": "...", "action": "Final Answer", "action_input": {{ "answer": "..." }} }}

CRITICAL RULES:
- tax_rate must be a decimal: 0.10 means 10%, NEVER pass 10
- action must be EXACTLY one of: {list(TOOLS.keys())} or "Final Answer"
- Never wrap your output in markdown fences or add any prose before/after the JSON
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """Strip ``` fences, then extract outermost { ... }"""
    text = re.sub(r"```(?:json)?|```", "", raw).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in output: {raw[:200]}")
    return json.loads(match.group(0))

def _build_prompt(history: list[dict]) -> str:
    """Flatten conversation history into a single prompt string."""
    lines = []
    for m in history:
        role = m["role"].capitalize()
        lines.append(f"{role}: {m['content']}")
    lines.append("Assistant:")
    return "\n\n".join(lines)

# ── ReAct Loop ────────────────────────────────────────────────────────────────

def run_agent(query: str, provider: LLMProvider = None, max_steps: int = 10) -> str:
    history = [{"role": "user", "content": query}]

    # Fresh tracker per run so session_summary() reflects only this run
    from src.telemetry.metrics import PerformanceTracker
    run_tracker = PerformanceTracker()

    logger.log_event("AGENT_START", {
        "provider": provider.__class__.__name__,
        "query": query
    })

    for step in range(1, max_steps + 1):
        prompt = _build_prompt(history)
        result = provider.generate(prompt, system_prompt=SYSTEM_PROMPT)

        raw     = result["content"]
        usage   = result["usage"]
        latency = result["latency_ms"]

        # ── Track metrics via PerformanceTracker (writes to logs/ via logger) ─
        run_tracker.track_request(
            provider = result.get("provider", provider.__class__.__name__),
            model    = provider.model_name,
            usage    = usage,
            latency_ms = latency,
        )

        try:
            parsed = _parse_json(raw)
        except (ValueError, json.JSONDecodeError) as e:
            logger.log_event("PARSE_ERROR", {
                "step": step, "error": str(e), "raw": raw[:300]
            })
            history.append({"role": "assistant", "content": raw})
            history.append({"role": "user", "content": "Invalid JSON. Reply with ONLY a raw JSON object."})
            continue

        action       = parsed.get("action", "")
        action_input = parsed.get("action_input", {})

        logger.log_event("AGENT_STEP", {
            "step": step,
            "thought": parsed.get("thought", ""),
            "action": action
        })

        # ── Termination ───────────────────────────────────────────────────────
        if action == "Final Answer":
            answer = (
                action_input.get("answer", str(action_input))
                if isinstance(action_input, dict) else str(action_input)
            )
            logger.log_event("AGENT_FINISH", {"steps": step, "answer": answer[:300]})

            # ── Session summary: total tokens, cost, avg latency ──────────────
            run_tracker.session_summary()
            return answer

        # ── Tool dispatch ─────────────────────────────────────────────────────
        tool = TOOLS.get(action)
        if tool is None:
            observation = f"Unknown tool '{action}'. Valid tools: {list(TOOLS)}"
            logger.log_event("HALLUCINATION", {"step": step, "bad_tool": action})
        else:
            try:
                observation = str(
                    tool(**action_input) if isinstance(action_input, dict) else tool(action_input)
                )
            except Exception as e:
                observation = f"Tool error: {e}"
                logger.log_event("TOOL_ERROR", {
                    "step": step, "tool": action, "error": str(e)
                })

        # ── Inject Observation back into history (the ReAct feedback loop) ────
        history.append({"role": "assistant", "content": raw})
        history.append({"role": "user",      "content": f"Observation: {observation}"})

    logger.log_event("TIMEOUT", {"max_steps": max_steps})
    run_tracker.session_summary()
    return f"[Timeout] Agent did not finish within {max_steps} steps."


if __name__ == "__main__":
    from dotenv import load_dotenv
    from src.core.llm_provider import get_provider
    load_dotenv()

    provider = get_provider()   # reads DEFAULT_PROVIDER from .env

    query = (
        "I want to fly from Hanoi to Tokyo on 2025-09-15, stay 3 nights. "
        "Check the weather, find the cheapest flight and a 4-star hotel, "
        "then calculate the total cost with 10% tax."
    )
    print(f"\nQuery: {query}\n{'='*60}")
    print(run_agent(query, provider=provider))