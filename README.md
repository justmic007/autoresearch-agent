# AutoResearch Agent

A production-grade multi-agent research system built with LangGraph, Claude, and FastAPI.

## Architecture

```
User query (POST /research)
        ↓
  Planner agent      — decomposes query into 3-5 subtasks (Claude)
        ↓
  Search agent       — calls Tavily for each subtask
        ↓
  RAG agent          — embeds results in ChromaDB, retrieves top-5 chunks
        ↓
  Writer agent       — synthesises structured report (Claude)
        ↓
  Critic agent       — scores quality 0-30 (Claude)
        ↓
  [if score < 20]    — routes back to Writer for one revision
        ↓
  Final report + metrics returned
```

**Stack:** FastAPI · LangGraph · Claude Sonnet · Tavily · ChromaDB · sentence-transformers · Redis · Docker · LangSmith · GitHub Actions

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/autoresearch-agent
cd autoresearch-agent
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Start infrastructure

```bash
# Start Redis + ChromaDB only (verify before adding app)
docker-compose up redis chromadb

# Check they're healthy
docker-compose ps
```

### 3. Install dependencies and run locally

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

### 4. Run the full stack

```bash
docker-compose up
```

### 5. Test it

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current state of AI regulation in the EU?"}'
```

## API

`POST /research`

Request:
```json
{ "query": "your research question" }
```

Response:
```json
{
  "thread_id": "uuid",
  "query": "...",
  "report": "## Executive Summary\n...",
  "quality_score": { "completeness": 8, "accuracy": 7, "coherence": 9, "total": 24 },
  "subtasks": ["subtask 1", "subtask 2", "subtask 3"],
  "duration_seconds": 14.3,
  "metrics": [
    { "agent": "planner", "latency_ms": 820, "tokens_used": 312 },
    { "agent": "search",  "latency_ms": 3100, "tokens_used": 0 },
    { "agent": "rag",     "latency_ms": 540,  "tokens_used": 0 },
    { "agent": "writer",  "latency_ms": 4200, "tokens_used": 2840 },
    { "agent": "critic",  "latency_ms": 980,  "tokens_used": 410 }
  ]
}
```

## Run tests

```bash
pytest tests/ -v
```

## Run benchmark eval

```bash
python -m app.eval.benchmark
```

Sample output:
```
Query                                                   Duration   Tokens  Quality  Revised
-----------------------------------------------------------------------------------------------
What is the current state of AI regulation in the EU?     13.2s     3621    26/30       no
What are the latest breakthroughs in battery tech...      14.8s     3890    24/30       no
How is generative AI impacting software engineering?      15.1s     4012    22/30      yes
-----------------------------------------------------------------------------------------------
AVERAGES                                                  14.4s     3841    24.0/30
```

## Observability

Traces are visible in [LangSmith](https://smith.langchain.com) under the `autoresearch-agent` project. Every agent call, tool invocation, and LLM request appears as a traced span with latency and token counts.