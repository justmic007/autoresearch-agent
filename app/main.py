# FastAPI main app with research endpoint
import uuid
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.graph.workflow import run_research

app = FastAPI(
    title="AutoResearch Agent",
    description="Multi-agent research system: Planner → Search → RAG → Writer → Critic",
    version="1.0.0",
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

    return ResearchResponse(
        thread_id=thread_id,
        query=req.query,
        report=result["report"],
        quality_score=result.get("quality_score", {}),
        subtasks=result.get("subtasks", []),
        duration_seconds=round(time.time() - t0, 2),
        metrics=result.get("metrics", []),
    )
