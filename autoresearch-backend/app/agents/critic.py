# Critic agent - scores report quality and triggers revision if needed
import json
import time
from google import genai
from google.genai import types
from app.config import MODEL_NAME, GEMINI_API_KEY
from app.graph.state import ResearchState, AgentMetrics, QualityScore

# ── Anthropic (commented out — swap back by uncommenting) ──
# from anthropic import Anthropic
# from app.config import MODEL_NAME, ANTHROPIC_API_KEY
# _client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Gemini client ──────────────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY)

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

    # ── Anthropic (commented out) ──────────────────────────
    # response = _client.messages.create(
    #     model=MODEL_NAME,
    #     max_tokens=256,
    #     system=SYSTEM,
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # raw = response.content[0].text.strip()
    # tokens = response.usage.input_tokens + response.usage.output_tokens

    # ── Gemini (active) ────────────────────────────────────
    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM),
    )
    raw = response.text.strip()
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

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
        tokens_used=tokens,
        # tokens_used=response.usage.input_tokens + response.usage.output_tokens,  # for Anthropic
    )

    return {
        **state,
        "quality_score": score,
        "metrics": state["metrics"] + [metric],
    }


# import json
# import time
# import google.generativeai as genai
# from app.config import MODEL_NAME, GEMINI_API_KEY
# from app.graph.state import ResearchState, AgentMetrics, QualityScore

# genai.configure(api_key=GEMINI_API_KEY)

# # ── Anthropic (commented out) ──────────────────────────────
# # from anthropic import Anthropic
# # from app.config import MODEL_NAME, ANTHROPIC_API_KEY
# # _client = Anthropic(api_key=ANTHROPIC_API_KEY)

# SYSTEM = """You are a research quality critic. Evaluate the given research report
# on three dimensions, each scored 0-10:

# - completeness: Does it fully answer the original question?
# - accuracy: Are claims grounded in the provided sources?
# - coherence: Is it well-structured and clearly written?

# Respond ONLY with a JSON object in this exact format:
# {
#   "completeness": 8,
#   "accuracy": 7,
#   "coherence": 9,
#   "feedback": "One sentence of the most important improvement needed."
# }

# No preamble, no markdown, no explanation."""


# def run(state: ResearchState) -> ResearchState:
#     t0 = time.time()

#     prompt = (
#         f"Original question: {state['query']}\n\nReport to evaluate:\n{state['report']}"
#     )

#     # ── Anthropic (commented out) ──────────────────────────
#     # response = _client.messages.create(
#     #     model=MODEL_NAME,
#     #     max_tokens=256,
#     #     system=SYSTEM,
#     #     messages=[{"role": "user", "content": prompt}],
#     # )

#     # raw = response.content[0].text.strip()

#     # ── Gemini (active) ────────────────────────────────────
#     model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM)
#     response = model.generate_content(prompt)
#     raw = response.text.strip()

#     # Strip markdown code fences if Claude wraps response in ```json ... ```
#     if raw.startswith("```"):
#         raw = raw.split("```")[1]
#         if raw.startswith("json"):
#             raw = raw[4:]
#         raw = raw.strip()

#     # Fallback if response is empty or unparseable
#     if not raw:
#         parsed = {
#             "completeness": 7,
#             "accuracy": 7,
#             "coherence": 7,
#             "feedback": "No feedback returned.",
#         }
#     else:
#         parsed = json.loads(raw)

#     score = QualityScore(
#         completeness=parsed["completeness"],
#         accuracy=parsed["accuracy"],
#         coherence=parsed["coherence"],
#         total=parsed["completeness"] + parsed["accuracy"] + parsed["coherence"],
#         feedback=parsed.get("feedback", ""),
#     )

#     latency_ms = (time.time() - t0) * 1000
#     metric = AgentMetrics(
#         agent="critic",
#         latency_ms=round(latency_ms, 1),
#         tokens=(
#             response.usage_metadata.total_token_count
#             if hasattr(response, "usage_metadata")
#             else 0
#         ),  # for Gemini
#         # tokens_used=response.usage.input_tokens + response.usage.output_tokens, # for Anthropic
#     )

#     return {
#         **state,
#         "quality_score": score,
#         "metrics": state["metrics"] + [metric],
#     }
