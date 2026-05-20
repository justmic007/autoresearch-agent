# Search agent - calls Tavily for each subtask

import time
from concurrent.futures import ThreadPoolExecutor
from app.tools.tavily import search
from app.graph.state import ResearchState, AgentMetrics


def run(state: ResearchState) -> ResearchState:
    t0 = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(search, subtask, 4): subtask
            for subtask in state["subtasks"]
        }
        for future, subtask in futures.items():
            hits = future.result()
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
