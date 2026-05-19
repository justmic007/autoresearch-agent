# Search agent - calls Tavily for each subtask

import time
from app.tools.tavily import search
from app.graph.state import ResearchState, AgentMetrics


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()
    results = []

    for subtask in state["subtasks"]:
        hits = search(subtask, max_results=4)
        results.append({"subtask": subtask, "results": hits})

    latency_ms = (time.time() - t0) * 1000
    metric = AgentMetrics(
        agent="search",
        latency_ms=round(latency_ms, 1),
        tokens_used=0,  # no LLM call in this agent
    )

    return {
        **state,
        "search_results": results,
        "metrics": state["metrics"] + [metric],
    }
