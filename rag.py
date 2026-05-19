# RAG agent - embeds search results and retrieves relevant chunks
import time
from app.tools.embedder import embed_and_store, retrieve
from app.graph.state import ResearchState, AgentMetrics


def _flatten_results(search_results: list[dict]) -> list[str]:
    """Convert nested search results into flat text chunks for embedding."""
    chunks = []
    for item in search_results:
        for result in item.get("results", []):
            content = result.get("content", "").strip()
            if content:
                chunks.append(f"[{result.get('title', '')}]\n{content}")
    return chunks


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()

    chunks = _flatten_results(state["search_results"])
    embed_and_store(state["thread_id"], chunks)
    rag_chunks = retrieve(state["query"], state["thread_id"])

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent="rag",
        latency_ms=round(latency_ms, 1),
        tokens_used=0,
    )

    return {
        **state,
        "rag_chunks": rag_chunks,
        "metrics": state["metrics"] + [metric],
    }
