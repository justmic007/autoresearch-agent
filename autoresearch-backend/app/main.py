# FastAPI main app with research endpoint
import uuid
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.graph.workflow import run_research, stream_research
from app.memory.redis_state import save_job, load_job, list_jobs

app = FastAPI(
    title="AutoResearch Agent",
    description="Multi-agent research system: Planner → Search → RAG → Writer → Critic",
    version="1.0.0",
)

# ── CORS — allows Next.js frontend to call this API ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    thread_id: str
    query: str
    report: str
    quality_score: dict
    subtasks: list[str]
    duration_seconds: float
    metrics: list[dict]


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Blocking endpoint (used by CLI / make query-pretty) ───────
@app.post("/research", response_model=ResearchResponse)
def research(req: ResearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    thread_id = str(uuid.uuid4())
    t0 = time.time()

    try:
        result = run_research(query=req.query, thread_id=thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result["finished_at"] = time.time()
    save_job(thread_id, result)

    return ResearchResponse(
        thread_id=thread_id,
        query=req.query,
        report=result["report"],
        quality_score=result.get("quality_score", {}),
        subtasks=result.get("subtasks", []),
        duration_seconds=round(time.time() - t0, 2),
        metrics=result.get("metrics", []),
    )


# ── Streaming endpoint (used by Next.js frontend) ─────────────
@app.post("/research/stream")
def research_stream(req: ResearchRequest):
    """
    Server-Sent Events stream.
    Emits an event after each agent completes, then a final
    'complete' event with the full report and metrics.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    thread_id = str(uuid.uuid4())

    return StreamingResponse(
        stream_research(query=req.query, thread_id=thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
            "X-Thread-ID": thread_id,
        },
    )


# ── Job persistence endpoints ─────────────────────────────────
@app.get("/research/{thread_id}")
def get_job(thread_id: str):
    job = load_job(thread_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
def get_jobs():
    return list_jobs()


# ── Delete a specific job ─────────────────────────────────────
@app.delete("/research/{thread_id}")
def delete_job_endpoint(thread_id: str):
    from app.memory.redis_state import delete_job
    deleted = delete_job(thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": thread_id}
