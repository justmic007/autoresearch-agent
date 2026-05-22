# Writer agent - synthesises final report from all gathered context
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

SYSTEM = """You are a professional research writer. Given a research question,
search results, and retrieved context, write a clear, well-structured report.

Your report MUST follow this exact structure:
## Executive Summary
(2-3 sentences summarising the key answer)

## Key Findings
(3-5 bullet points, each a distinct insight)

## Analysis
(2-3 paragraphs of deeper analysis)

## Sources
(list each source URL used)

Be factual, cite specific details from the provided context, and be concise."""


def _build_context(state: ResearchState) -> str:
    lines = [f"Research question: {state['query']}\n"]

    lines.append("--- Retrieved context (RAG) ---")
    for chunk in state["rag_chunks"]:
        lines.append(chunk[:800])

    lines.append("\n--- Search results ---")
    for item in state["search_results"]:
        lines.append(f"\nSubtask: {item['subtask']}")
        for r in item["results"][:3]:
            lines.append(f"  [{r['title']}] {r['url']}")
            lines.append(f"  {r['content'][:400]}")

    if state["revision_count"] > 0 and state.get("quality_score"):
        lines.append(f"\n--- Previous report feedback ---")
        lines.append(state["quality_score"]["feedback"])

    return "\n".join(lines)


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()
    context = _build_context(state)

    # ── Anthropic (commented out) ──────────────────────────
    # response = _client.messages.create(
    #     model=MODEL_NAME,
    #     max_tokens=MAX_TOKENS,
    #     system=SYSTEM,
    #     messages=[{"role": "user", "content": context}],
    # )
    # report = response.content[0].text.strip()
    # tokens = response.usage.input_tokens + response.usage.output_tokens

    # ── Gemini (active) ────────────────────────────────────
    response = _client.models.generate_content(
        model=MODEL_NAME,
        contents=context,
        config=types.GenerateContentConfig(system_instruction=SYSTEM),
    )
    report = response.text.strip()
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent="writer",
        latency_ms=round(latency_ms, 1),
        tokens_used=tokens,
        # tokens_used=response.usage.input_tokens + response.usage.output_tokens,  # for Anthropic
    )

    return {
        **state,
        "report": report,
        "revision_count": state["revision_count"] + 1,
        "metrics": state["metrics"] + [metric],
    }


# import time
# from google import genai
# from google.genai import types
# from app.config import MODEL_NAME, GEMINI_API_KEY
# from app.graph.state import ResearchState, AgentMetrics

# _client = genai.Client(api_key=GEMINI_API_KEY)


# # # ── Anthropic (commented out) ──────────────────────────────
# # from anthropic import Anthropic
# # from app.config import MODEL_NAME, MAX_TOKENS, ANTHROPIC_API_KEY
# # _client = Anthropic(api_key=ANTHROPIC_API_KEY)

# SYSTEM = """You are a professional research writer. Given a research question,
# search results, and retrieved context, write a clear, well-structured report.

# Your report MUST follow this exact structure:
# ## Executive Summary
# (2-3 sentences summarising the key answer)

# ## Key Findings
# (3-5 bullet points, each a distinct insight)

# ## Analysis
# (2-3 paragraphs of deeper analysis)

# ## Sources
# (list each source URL used)

# Be factual, cite specific details from the provided context, and be concise."""


# def _build_context(state: ResearchState) -> str:
#     lines = [f"Research question: {state['query']}\n"]

#     lines.append("--- Retrieved context (RAG) ---")
#     for chunk in state["rag_chunks"]:
#         lines.append(chunk[:800])

#     lines.append("\n--- Search results ---")
#     for item in state["search_results"]:
#         lines.append(f"\nSubtask: {item['subtask']}")
#         for r in item["results"][:3]:
#             lines.append(f"  [{r['title']}] {r['url']}")
#             lines.append(f"  {r['content'][:400]}")

#     if state["revision_count"] > 0 and state.get("quality_score"):
#         lines.append(f"\n--- Previous report feedback ---")
#         lines.append(state["quality_score"]["feedback"])

#     return "\n".join(lines)


# def run(state: ResearchState) -> ResearchState:
#     t0 = time.time()
#     context = _build_context(state)

#     # ── Anthropic (commented out) ──────────────────────────
#     # response = _client.messages.create(
#     #     model=MODEL_NAME,
#     #     max_tokens=MAX_TOKENS,
#     #     system=SYSTEM,
#     #     messages=[{"role": "user", "content": context}],
#     # )

#     # report = response.content[0].text.strip()

#     # ── Gemini (active) ────────────────────────────────────
#     response = _client.models.generate_content(
#         model=MODEL_NAME,
#         contents=prompt,
#         config=types.GenerateContentConfig(system_instruction=SYSTEM),
#     )
#     report = response.text.strip()

#     latency_ms = (time.time() - t0) * 1000
#     metric = AgentMetrics(
#         agent="writer",
#         latency_ms=round(latency_ms, 1),
#         tokens_used=(
#             response.usage_metadata.total_token_count
#             if hasattr(response, "usage_metadata")
#             else 0
#         ),
#         # tokens_used=response.usage.input_tokens + response.usage.output_tokens, # for Anthropic
#     )

#     return {
#         **state,
#         "report": report,
#         "revision_count": state["revision_count"] + 1,
#         "metrics": state["metrics"] + [metric],
#     }
