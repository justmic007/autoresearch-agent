# Planner agent - decomposes query into subtasks

import json
import time
from anthropic import Anthropic
from app.config import MODEL_NAME, MAX_TOKENS, ANTHROPIC_API_KEY
from app.graph.state import ResearchState, AgentMetrics

_client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """You are a research planner. Given a research question, break it into
3 to 5 specific, searchable subtasks. Each subtask should be a focused search query
that together fully cover the original question.

Respond ONLY with a JSON object in this exact format:
{"subtasks": ["subtask 1", "subtask 2", "subtask 3"]}

No preamble, no markdown, no explanation."""


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()

    response = _client.messages.create(
        model=MODEL_NAME,
        max_tokens=512,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Research question: {state['query']}"}],
    )

    raw = response.content[0].text.strip()
    parsed = json.loads(raw)
    subtasks = parsed.get("subtasks", [])

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent="planner",
        latency_ms=round(latency_ms, 1),
        tokens_used=response.usage.input_tokens + response.usage.output_tokens,
    )

    return {
        **state,
        "subtasks": subtasks,
        "metrics": state["metrics"] + [metric],
    }
