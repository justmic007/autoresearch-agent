# Writer agent - synthesises final report from all gathered context
#
# Fallback chain (ranked by quality then reliability):
#   1. SambaNova DeepSeek-V3.2    — best reasoning, free
#   2. Gemini 2.5-flash-lite      — highest quality in benchmarks, 1,500 req/day
#   3. NVIDIA deepseek-v4-flash   — strong reasoning, no daily cap
#   4. Cerebras qwen3-235b        — large model, good prose, free
#   5. NVIDIA llama-3.3-70b       — no daily cap, reliable fallback
#   6. SambaNova llama-3.3-70b    — fast, good output length, free
#   7. SambaNova llama-4-maverick  — fastest, shorter output, free
#   8. Groq llama-3.3-70b         — fast, 1,000 req/day cap
#   9. HF/novita llama-3.3-70b    — free but slow (~11s)
#  10. Mistral small              — slowest (~9s), 1B tokens/month
#  11. OpenRouter gemma-4-26b     — free, last resort (rate-limited often)
#  12. Static fallback            — never fails
#
# Revision pass prepends: SambaNova DeepSeek-V3.2 → NVIDIA deepseek-v4-flash

import time
from app.graph.state import ResearchState, AgentMetrics
from app.config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    NVIDIA_API_KEY, NVIDIA_MODEL_WRITER, NVIDIA_MODEL_LLAMA,
    SAMBANOVA_API_KEY, SAMBANOVA_MODEL, SAMBANOVA_MODEL_DEEPSEEK, SAMBANOVA_MODEL_MAVERICK,
    CEREBRAS_API_KEY, CEREBRAS_MODEL_LARGE,
    HUGGINGFACE_API_KEY, HF_NOVITA_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    MISTRAL_API_KEY, MISTRAL_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_MODEL,
    MAX_TOKENS,
)

SYSTEM = """You are a professional research writer. Given a research question,
search results, and retrieved context, write a clear, well-structured report.

Your report MUST follow this exact structure:
## Executive Summary
(2-3 sentences summarising the key answer with at least one specific fact, number, or date)

## Key Findings
(3-5 bullet points — each MUST start with `*` and include a specific statistic, figure, date, or named entity
directly extracted from the provided sources. No vague generalisations. No numbered lists.)

## Analysis
(2-3 paragraphs of deeper analysis grounded in the source data.
Every claim must reference a specific source, number, or named organisation.)

## Sources
(list each source URL used)

CRITICAL RULES:
- Extract and use EXACT numbers, dates, percentages, and named entities from the context
- Never write vague phrases like "significant progress" or "many experts" — name them
- Every bullet point must contain at least one hard fact (number, date, name, or measurement)
- If a source contains specific data, you MUST include it"""

TIMEOUT = 30


def _build_context(state: ResearchState) -> str:
    lines = [f"Research question: {state['query']}\n"]
    lines.append("--- Retrieved context (RAG) ---")
    for chunk in state["rag_chunks"][:3]:
        lines.append(chunk[:400])
    lines.append("\n--- Search results ---")
    for item in state["search_results"]:
        lines.append(f"\nSubtask: {item['subtask']}")
        for r in item["results"][:2]:
            lines.append(f"  [{r['title']}] {r['url']}")
            lines.append(f"  {r['content'][:250]}")
    if state["revision_count"] > 0 and state.get("quality_score"):
        lines.append("\n--- Previous report feedback ---")
        lines.append(state["quality_score"]["feedback"])
    return "\n".join(lines)


def _call_openai_compatible(base_url: str, api_key: str, model: str, context: str) -> tuple[str, int]:
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": context},
        ],
        max_tokens=MAX_TOKENS,
        timeout=TIMEOUT,
    )
    report = response.choices[0].message.content.strip()
    tokens = response.usage.total_tokens if response.usage else 0
    return report, tokens


def _try_gemini(context: str) -> tuple[str, int]:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=context,
        config=types.GenerateContentConfig(system_instruction=SYSTEM),
    )
    tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
    return response.text.strip(), tokens


def _try_groq(context: str) -> tuple[str, int]:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": context},
        ],
        max_tokens=MAX_TOKENS,
        timeout=TIMEOUT,
    )
    tokens = response.usage.total_tokens if response.usage else 0
    return response.choices[0].message.content.strip(), tokens


def _static_fallback(context: str) -> tuple[str, int]:
    report = (
        "## Executive Summary\n"
        "Report generation encountered provider limitations. "
        "The research pipeline completed data retrieval but could not synthesise "
        "a full report at this time. Please try again shortly.\n\n"
        "## Key Findings\n"
        "- All AI writing providers are temporarily rate-limited\n"
        "- Search and retrieval completed successfully\n"
        "- Please retry in a few minutes\n\n"
        "## Analysis\n"
        "This is an automated fallback response. The underlying research data "
        "was retrieved successfully. Provider rate limits have been reached across "
        "all configured writing models.\n\n"
        "## Sources\n"
        "Sources retrieved but report synthesis unavailable."
    )
    return report, 0


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()
    context = _build_context(state)
    is_revision = state["revision_count"] > 0 and state.get("quality_score") is not None

    providers: list[tuple[str, callable]] = []

    # Revision pass — best reasoning models first
    if is_revision:
        if SAMBANOVA_API_KEY:
            providers.append(("sambanova-deepseek", lambda c: _call_openai_compatible(
                "https://api.sambanova.ai/v1", SAMBANOVA_API_KEY, SAMBANOVA_MODEL_DEEPSEEK, c)))
        if NVIDIA_API_KEY:
            providers.append(("nvidia-deepseek", lambda c: _call_openai_compatible(
                "https://integrate.api.nvidia.com/v1", NVIDIA_API_KEY, NVIDIA_MODEL_WRITER, c)))

    # Primary chain
    if SAMBANOVA_API_KEY:
        providers.append(("sambanova-deepseek", lambda c: _call_openai_compatible(
            "https://api.sambanova.ai/v1", SAMBANOVA_API_KEY, SAMBANOVA_MODEL_DEEPSEEK, c)))
    providers.append(("gemini", _try_gemini))
    if NVIDIA_API_KEY:
        providers.append(("nvidia-deepseek", lambda c: _call_openai_compatible(
            "https://integrate.api.nvidia.com/v1", NVIDIA_API_KEY, NVIDIA_MODEL_WRITER, c)))
    if CEREBRAS_API_KEY:
        providers.append(("cerebras-qwen3", lambda c: _call_openai_compatible(
            "https://api.cerebras.ai/v1", CEREBRAS_API_KEY, CEREBRAS_MODEL_LARGE, c)))
    if NVIDIA_API_KEY:
        providers.append(("nvidia-llama", lambda c: _call_openai_compatible(
            "https://integrate.api.nvidia.com/v1", NVIDIA_API_KEY, NVIDIA_MODEL_LLAMA, c)))
    if SAMBANOVA_API_KEY:
        providers.append(("sambanova-llama", lambda c: _call_openai_compatible(
            "https://api.sambanova.ai/v1", SAMBANOVA_API_KEY, SAMBANOVA_MODEL, c)))
        providers.append(("sambanova-maverick", lambda c: _call_openai_compatible(
            "https://api.sambanova.ai/v1", SAMBANOVA_API_KEY, SAMBANOVA_MODEL_MAVERICK, c)))
    providers.append(("groq", _try_groq))
    if HUGGINGFACE_API_KEY:
        providers.append(("hf-novita", lambda c: _call_openai_compatible(
            "https://router.huggingface.co/novita/v3/openai", HUGGINGFACE_API_KEY, HF_NOVITA_MODEL, c)))
    if MISTRAL_API_KEY:
        providers.append(("mistral", lambda c: _call_openai_compatible(
            "https://api.mistral.ai/v1", MISTRAL_API_KEY, MISTRAL_MODEL, c)))
    if OPENROUTER_API_KEY:
        providers.append(("openrouter-gemma", lambda c: _call_openai_compatible(
            "https://openrouter.ai/api/v1", OPENROUTER_API_KEY, OPENROUTER_MODEL, c)))
    providers.append(("static-fallback", _static_fallback))

    # Deduplicate (revision prepends may duplicate)
    seen, unique = set(), []
    for name, fn in providers:
        if name not in seen:
            seen.add(name)
            unique.append((name, fn))
    providers = unique

    report, tokens, provider = "", 0, "unknown"

    for name, fn in providers:
        try:
            result, tok = fn(context)
            if result and len(result.strip()) > 100:
                report, tokens, provider = result, tok, name
                print(f"[writer] using {name}")
                break
            print(f"[writer] {name} returned insufficient content — trying next")
        except Exception as e:
            print(f"[writer] {name} failed ({type(e).__name__}: {e}) — trying next")

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent=f"writer({provider})",
        latency_ms=round(latency_ms, 1),
        tokens_used=tokens,
    )
    return {
        **state,
        "report": report,
        "revision_count": state["revision_count"] + 1,
        "metrics": state["metrics"] + [metric],
    }
