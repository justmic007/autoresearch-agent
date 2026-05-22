# Planner agent - decomposes query into subtasks

import json
import time
from google import genai
from google.genai import types
from app.config import MODEL_NAME, GEMINI_API_KEY
from app.graph.state import ResearchState, AgentMetrics

# ── Anthropic (commented out — swap back by uncommenting) ──
# from anthropic import Anthropic
# from app.config import MODEL_NAME, MAX_TOKENS, ANTHROPIC_API_KEY
# _client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Gemini client ──────────────────────────────────────────
_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM = """You are a research planner. Given a research question, break it into
3 to 5 specific, searchable subtasks. Each subtask should be a focused search query
that together fully cover the original question.

Respond ONLY with a JSON object in this exact format:
{"subtasks": ["subtask 1", "subtask 2", "subtask 3"]}

No preamble, no markdown, no explanation."""


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()

    # ── Anthropic (commented out) ──────────────────────────
    # response = _client.messages.create(
    #     model=MODEL_NAME,
    #     max_tokens=512,
    #     system=SYSTEM,
    #     messages=[{"role": "user", "content": f"Research question: {state['query']}"}],
    # )
    # raw    = response.content[0].text.strip()
    # tokens = response.usage.input_tokens + response.usage.output_tokens

    # ── Gemini (active) ────────────────────────────────────
    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=f"Research question: {state['query']}",
        config=types.GenerateContentConfig(system_instruction=SYSTEM),
    )
    raw = response.text.strip()
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

    # Clean up response (remove markdown code blocks if present)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    parsed = json.loads(raw)
    subtasks = parsed.get("subtasks", [])

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent="planner",
        latency_ms=round(latency_ms, 1),
        tokens_used=tokens,
    )

    return {
        **state,
        "subtasks": subtasks,
        "metrics": state["metrics"] + [metric],
    }


# import json
# import time
# import google.generativeai as genai
# from app.config import MODEL_NAME, GEMINI_API_KEY
# from app.graph.state import ResearchState, AgentMetrics

# # from anthropic import Anthropic
# # from app.config import MODEL_NAME, MAX_TOKENS, ANTHROPIC_API_KEY

# genai.configure(api_key=GEMINI_API_KEY)
# # _client = Anthropic(api_key=ANTHROPIC_API_KEY)


# SYSTEM = """You are a research planner. Given a research question, break it into
# 3 to 5 specific, searchable subtasks. Each subtask should be a focused search query
# that together fully cover the original question.

# Respond ONLY with a JSON object in this exact format:
# {"subtasks": ["subtask 1", "subtask 2", "subtask 3"]}

# No preamble, no markdown, no explanation."""


# def run(state: ResearchState) -> ResearchState:
#     t0 = time.time()
#     # ── Anthropic (commented out) ──────────────────────────
#     # response = _client.messages.create(
#     #     model=MODEL_NAME,
#     #     max_tokens=512,
#     #     system=SYSTEM,
#     #     messages=[{"role": "user", "content": f"Research question: {state['query']}"}],
#     # )

#     # raw = response.content[0].text.strip()

#     # ── Gemini (active) ────────────────────────────────────
#     model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM)
#     response = model.generate_content(f"Research question: {state['query']}")
#     raw = response.text.strip()

#     # Clean up Gemini response (remove markdown code blocks)
#     if raw.startswith("```"):
#         raw = raw.split("```")[1]
#         if raw.startswith("json"):
#             raw = raw[4:]
#         raw = raw.strip()

#     parsed = json.loads(raw)
#     subtasks = parsed.get("subtasks", [])

#     latency_ms = (time.time() - t0) * 1000
#     metric = AgentMetrics(
#         agent="planner",
#         latency_ms=round(latency_ms, 1),
#         # tokens_used=response.usage.input_tokens + response.usage.output_tokens, # for Anthropic
#         tokens_used=(
#             response.usage_metadata.total_token_count
#             if hasattr(response, "usage_metadata")
#             else 0
#         ),  # for Gemini
#     )

#     return {
#         **state,
#         "subtasks": subtasks,
#         "metrics": state["metrics"] + [metric],
#     }
