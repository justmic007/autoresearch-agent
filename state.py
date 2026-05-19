# Shared LangGraph state schema - the backbone all agents read/write

from typing import TypedDict, Optional
import time


class AgentMetrics(TypedDict):
    agent: str
    latency_ms: float
    tokens_used: int


class QualityScore(TypedDict):
    completeness: int  # 0-10
    accuracy: int  # 0-10
    coherence: int  # 0-10
    total: int  # 0-30
    feedback: str


class ResearchState(TypedDict):
    # --- Input ---
    query: str
    thread_id: str

    # --- Planner output ---
    subtasks: list[str]

    # --- Search agent output ---
    search_results: list[dict]  # [{subtask, results: [{title, url, content}]}]

    # --- RAG agent output ---
    rag_chunks: list[str]

    # --- Writer output ---
    report: str
    revision_count: int

    # --- Critic output ---
    quality_score: Optional[QualityScore]

    # --- Observability ---
    metrics: list[AgentMetrics]
    started_at: float
    finished_at: Optional[float]


def initial_state(query: str, thread_id: str) -> ResearchState:
    return ResearchState(
        query=query,
        thread_id=thread_id,
        subtasks=[],
        search_results=[],
        rag_chunks=[],
        report="",
        revision_count=0,
        quality_score=None,
        metrics=[],
        started_at=time.time(),
        finished_at=None,
    )
