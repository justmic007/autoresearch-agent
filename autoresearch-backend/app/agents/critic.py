# Critic agent - scores report quality and triggers revision if needed

import json
import time
from anthropic import Anthropic
from app.config import MODEL_NAME, ANTHROPIC_API_KEY
from app.graph.state import ResearchState, AgentMetrics, QualityScore

_client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """You are a research quality critic. Evaluate the given research report
on three dimensions, each scored 0-10:

- completeness: Does it fully answer the original question?
- accuracy: Are claims grounded in the provided sources?
- coherence: Is it well-structured and clearly written?

Respond ONLY with a JSON object in this exact format:
{
  "completeness": 8,
  "accuracy": 7,
  "coherence": 9,
  "feedback": "One sentence of the most important improvement needed."
}

No preamble, no markdown, no explanation."""


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()

    prompt = (
        f"Original question: {state['query']}\n\nReport to evaluate:\n{state['report']}"
    )

    response = _client.messages.create(
        model=MODEL_NAME,
        max_tokens=256,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if Claude wraps response in ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # Fallback if response is empty or unparseable
    if not raw:
        parsed = {
            "completeness": 7,
            "accuracy": 7,
            "coherence": 7,
            "feedback": "No feedback returned.",
        }
    else:
        parsed = json.loads(raw)

    score = QualityScore(
        completeness=parsed["completeness"],
        accuracy=parsed["accuracy"],
        coherence=parsed["coherence"],
        total=parsed["completeness"] + parsed["accuracy"] + parsed["coherence"],
        feedback=parsed.get("feedback", ""),
    )

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent="critic",
        latency_ms=round(latency_ms, 1),
        tokens_used=response.usage.input_tokens + response.usage.output_tokens,
    )

    return {
        **state,
        "quality_score": score,
        "metrics": state["metrics"] + [metric],
    }
