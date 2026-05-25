# AutoResearch Agent

A production-grade multi-agent research system built with LangGraph and FastAPI.

## Architecture

```
User query (POST /research)
        ↓
  Planner agent      — decomposes query into 3-5 subtasks (Groq llama-4-scout)
        ↓
  Search agent       — calls Tavily in parallel for each subtask
        ↓
  RAG agent          — embeds results via Gemini embeddings, retrieves top-5 chunks
        ↓
  Writer agent       — synthesises structured report (SambaNova / Gemini / NVIDIA / Cerebras)
        ↓
  Critic agent       — scores quality 0-30 (Groq llama-3.3-70b)
        ↓
  [if score < 20]    — routes back to Writer for one revision
        ↓
  Final report + metrics returned
```

**Stack:** FastAPI · LangGraph · Groq · Gemini · SambaNova · NVIDIA NIM · Cerebras · Mistral · HuggingFace · OpenRouter · Tavily · Upstash Redis · Docker · LangSmith · GitHub Actions

## Agent Provider Chains

Each agent has a dedicated fallback chain to avoid rate limit contention.

**Planner** — needs fast, reliable JSON output
```
Groq llama-4-scout (169ms) → Groq qwen3-32b → Groq llama-3.3-70b → static fallback
```

**Writer** — ranked by output quality
```
SambaNova DeepSeek-V3.2 → Gemini 2.5-flash-lite → NVIDIA deepseek-v4-flash
→ Cerebras qwen3-235b → NVIDIA llama-3.3-70b → SambaNova llama-3.3-70b
→ SambaNova llama-4-maverick → Groq llama-3.3-70b → HF/novita llama-3.3-70b
→ Mistral small → OpenRouter gemma-4-26b → static fallback
```

**Critic** — needs accurate JSON scoring
```
Groq llama-3.3-70b → Groq llama-4-scout → Mistral small → static fallback (7/7/7)
```

All providers are free tier. Static fallbacks ensure the pipeline never crashes.

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/autoresearch-agent
cd autoresearch-backend
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Start infrastructure

```bash
make infra        # starts Redis via Docker
```

### 3. Install dependencies and run locally

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

make dev          # uvicorn with hot-reload on :8000
```

### 4. Run the full stack via Docker

```bash
make run
```

### 5. Test it

```bash
make query Q="What is the current state of AI regulation in the EU?"
```

## API

`POST /research` — blocking, returns full result

`POST /research/stream` — Server-Sent Events, streams agent progress in real time

`GET /research/{thread_id}` — fetch a stored job by ID

`DELETE /research/{thread_id}` — delete a job from Redis

`GET /jobs` — list all stored jobs

`GET /health` — health check

### Request
```json
{ "query": "your research question" }
```

### Response
```json
{
  "thread_id": "uuid",
  "query": "...",
  "report": "## Executive Summary\n...",
  "quality_score": { "completeness": 9, "accuracy": 8, "coherence": 9, "total": 26 },
  "subtasks": ["subtask 1", "subtask 2", "subtask 3"],
  "duration_seconds": 12.6,
  "metrics": [
    { "agent": "planner(groq-scout)",          "latency_ms": 420,  "tokens_used": 180 },
    { "agent": "search",                        "latency_ms": 4200, "tokens_used": 0   },
    { "agent": "rag",                           "latency_ms": 2400, "tokens_used": 0   },
    { "agent": "writer(sambanova-deepseek)",    "latency_ms": 3800, "tokens_used": 2700 },
    { "agent": "critic(groq-70b)",              "latency_ms": 980,  "tokens_used": 410 }
  ]
}
```

## Environment Variables

Required:
```
GROQ_API_KEY
GEMINI_API_KEY
TAVILY_API_KEY
UPSTASH_REDIS_URL
```

Optional (add more fallback depth):
```
NVIDIA_API_KEY
SAMBANOVA_API_KEY
MISTRAL_API_KEY
CEREBRAS_API_KEY
HUGGINGFACE_API_KEY
OPENROUTER_API_KEY
```

## Run tests

```bash
make test         # pytest tests/ -v  (16 tests, all mocked — no API keys needed)
```

## Run benchmark eval

```bash
make benchmark
```

Sample output:
```
Query                                                    Duration   Tokens   Quality  Revised
-----------------------------------------------------------------------------------------------
What is the current state of AI regulation in the EU?     16.1s     2913       26/30       no
What are the latest breakthroughs in battery tech?        11.6s     3062       26/30       no
How is generative AI impacting software engineering?      10.3s     3234       24/30       no
What is the state of nuclear fusion energy in 2025?       12.1s     3137       26/30       no
How are central banks responding to inflation?            13.1s     3130       26/30       no
-----------------------------------------------------------------------------------------------
AVERAGES                                                  12.6s     3095     25.6/30
```

## Observability

Traces are visible in [LangSmith](https://smith.langchain.com) under the `autoresearch-agent` project. Every agent call, tool invocation, and LLM request appears as a traced span with latency and token counts.
