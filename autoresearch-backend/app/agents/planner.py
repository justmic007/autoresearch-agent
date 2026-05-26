# Planner agent - decomposes query into subtasks
#
# Fallback chain:
#   1. Groq llama-4-scout   — 169ms, fastest, JSON mode
#   2. Groq qwen3-32b       — 424ms, strong structured output, JSON mode
#   3. Groq llama-3.3-70b   — 1.4s,  reliable, JSON mode
#   4. Static fallback      — never fails

import json
import time
from app.graph.state import ResearchState, AgentMetrics
from app.config import GROQ_API_KEY, GROQ_MODEL_FAST, GROQ_MODEL

SYSTEM = """You are a research planner. Given a research question, break it into
3 to 5 specific, searchable subtasks. Each subtask should be a focused search query
that together fully cover the original question.

Respond ONLY with a JSON object in this exact format:
{"subtasks": ["subtask 1", "subtask 2", "subtask 3"]}

No preamble, no markdown, no explanation."""

TIMEOUT = 25
GROQ_MODEL_QWEN = "qwen/qwen3-32b"


def _parse_subtasks(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if "<think>" in raw:
        raw = raw[raw.rfind("</think>") + 8 :].strip()
    try:
        parsed = json.loads(raw)
        subtasks = parsed.get("subtasks", [])
        if isinstance(subtasks, list) and len(subtasks) > 0:
            return [str(s) for s in subtasks]
    except json.JSONDecodeError:
        pass
    return []


def _try_groq(query: str, model: str) -> tuple[list[str], int]:
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)

    # qwen3 doesn't support json_object response format
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Research question: {query}"},
        ],
        temperature=0.1,
        max_tokens=512,
        timeout=TIMEOUT,
    )
    if "qwen" not in model.lower():
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    raw = response.choices[0].message.content.strip()
    tokens = response.usage.total_tokens if response.usage else 0
    return _parse_subtasks(raw), tokens


def _static_fallback(query: str) -> tuple[list[str], int]:
    q = query.strip().rstrip("?")
    return [
        f"{q} overview definition and background",
        f"{q} key facts current state and developments",
        f"{q} analysis implications and future outlook",
    ], 0


def run(state: ResearchState) -> ResearchState:
    query = state["query"]
    t0 = time.time()

    providers: list[tuple[str, callable]] = [
        ("groq-scout", lambda q: _try_groq(q, GROQ_MODEL_FAST)),
        ("groq-qwen3", lambda q: _try_groq(q, GROQ_MODEL_QWEN)),
        ("groq-70b", lambda q: _try_groq(q, GROQ_MODEL)),
        ("static-fallback", _static_fallback),
    ]

    subtasks, tokens, provider = [], 0, "unknown"

    for name, fn in providers:
        try:
            result, tok = fn(query)
            if result:
                subtasks, tokens, provider = result, tok, name
                print(f"[planner] using {name}")
                break
            print(f"[planner] {name} returned empty — trying next")
        except Exception as e:
            print(f"[planner] {name} failed ({type(e).__name__}: {e}) — trying next")

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent=f"planner({provider})",
        latency_ms=round(latency_ms, 1),
        tokens_used=tokens,
    )
    return {**state, "subtasks": subtasks, "metrics": state["metrics"] + [metric]}
