# Critic agent - scores report quality and triggers revision if needed
#
# Fallback chain (dedicated — does NOT compete with Planner or Writer):
#   1. Groq llama-4-scout   — 169ms, fastest, JSON mode
#   2. Groq llama-3.3-70b   — 1.4s,  JSON mode, higher quality scoring
#   3. Mistral small        — 1.0s,  good analytical reasoning
#   4. Static fallback      — returns neutral 7/7/7, never fails

import json
import time
from app.graph.state import ResearchState, AgentMetrics, QualityScore
from app.config import (
    GROQ_API_KEY, GROQ_MODEL_FAST, GROQ_MODEL,
    MISTRAL_API_KEY, MISTRAL_MODEL,
)

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

TIMEOUT = 25


def _parse_score(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if "<think>" in raw:
        raw = raw[raw.rfind("</think>") + 8:].strip()
    try:
        parsed = json.loads(raw)
        if all(k in parsed for k in ["completeness", "accuracy", "coherence", "feedback"]):
            return parsed
    except (json.JSONDecodeError, KeyError):
        pass
    return {"completeness": 7, "accuracy": 7, "coherence": 7,
            "feedback": "Unable to parse critic response — neutral score assigned."}


def _try_groq(prompt: str, model: str) -> tuple[str, int]:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=256,
        response_format={"type": "json_object"},
        timeout=TIMEOUT,
    )
    raw = response.choices[0].message.content.strip()
    tokens = response.usage.total_tokens if response.usage else 0
    return raw, tokens


def _call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> tuple[str, int]:
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=256,
        timeout=TIMEOUT,
    )
    raw = response.choices[0].message.content.strip()
    tokens = response.usage.total_tokens if response.usage else 0
    return raw, tokens


def _static_fallback(prompt: str) -> tuple[str, int]:
    return (
        json.dumps({"completeness": 7, "accuracy": 7, "coherence": 7,
                    "feedback": "Automated score — critic providers temporarily unavailable."}),
        0,
    )


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()
    prompt = (
        f"Original question: {state['query']}\n\n"
        f"Report to evaluate:\n{state['report']}"
    )

    providers: list[tuple[str, callable]] = [
        ("groq-scout", lambda p: _try_groq(p, GROQ_MODEL_FAST)),
        ("groq-70b",   lambda p: _try_groq(p, GROQ_MODEL)),
    ]
    if MISTRAL_API_KEY:
        providers.append(("mistral", lambda p: _call_openai_compatible(
            "https://api.mistral.ai/v1", MISTRAL_API_KEY, MISTRAL_MODEL, p)))
    providers.append(("static-fallback", _static_fallback))

    raw, tokens, provider = "", 0, "unknown"

    for name, fn in providers:
        try:
            result, tok = fn(prompt)
            if result and result.strip():
                raw, tokens, provider = result, tok, name
                print(f"[critic] using {name}")
                break
            print(f"[critic] {name} returned empty — trying next")
        except Exception as e:
            print(f"[critic] {name} failed ({type(e).__name__}: {e}) — trying next")

    parsed = _parse_score(raw)
    score = QualityScore(
        completeness=parsed["completeness"],
        accuracy=parsed["accuracy"],
        coherence=parsed["coherence"],
        total=parsed["completeness"] + parsed["accuracy"] + parsed["coherence"],
        feedback=parsed.get("feedback", ""),
    )

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent=f"critic({provider})",
        latency_ms=round(latency_ms, 1),
        tokens_used=tokens,
    )
    return {**state, "quality_score": score, "metrics": state["metrics"] + [metric]}
