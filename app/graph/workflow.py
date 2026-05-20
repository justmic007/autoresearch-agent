# LangGraph state machine wiring all agents together the revision loop

import time
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import ResearchState, initial_state
from app.agents import planner, search, rag, writer, critic
from app.config import QUALITY_THRESHOLD, MAX_REVISIONS


def _should_revise(state: ResearchState) -> str:
    score = state.get("quality_score")
    revisions = state.get("revision_count", 0)
    if score and score["total"] < QUALITY_THRESHOLD and revisions <= MAX_REVISIONS:
        return "revise"
    return "done"


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner.run)
    graph.add_node("search", search.run)
    graph.add_node("rag", rag.run)
    graph.add_node("writer", writer.run)
    graph.add_node("critic", critic.run)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "search")
    graph.add_edge("search", "rag")
    graph.add_edge("rag", "writer")
    graph.add_edge("writer", "critic")

    graph.add_conditional_edges(
        "critic",
        _should_revise,
        {"revise": "writer", "done": END},
    )

    return graph


def get_compiled_graph():
    graph = build_graph()
    return graph.compile(checkpointer=MemorySaver())


def run_research(query: str, thread_id: str) -> ResearchState:
    """Blocking: run full pipeline and return final state."""
    app = get_compiled_graph()
    state = initial_state(query=query, thread_id=thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    final = app.invoke(state, config=config)
    final["finished_at"] = time.time()
    return final


def stream_research(query: str, thread_id: str):
    """
    Generator: yields SSE-formatted strings after each agent completes.

    Event types:
      - agent_done  : fired after each agent finishes
      - complete    : fired when full pipeline is done
      - error       : fired on exception
    """
    import json

    def emit(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Wrap each agent to emit an event after it runs
    agent_order = ["planner", "search", "rag", "writer", "critic"]
    results = {}

    try:
        state = initial_state(query=query, thread_id=thread_id)

        # ── Planner ──────────────────────────────────────────
        state = planner.run(state)
        results["planner"] = state
        yield emit(
            "agent_done",
            {
                "agent": "planner",
                "subtasks": state["subtasks"],
                "latency": state["metrics"][-1]["latency_ms"],
            },
        )

        # ── Search ───────────────────────────────────────────
        state = search.run(state)
        results["search"] = state
        yield emit(
            "agent_done",
            {
                "agent": "search",
                "sources": sum(len(r["results"]) for r in state["search_results"]),
                "latency": state["metrics"][-1]["latency_ms"],
            },
        )

        # ── RAG ──────────────────────────────────────────────
        state = rag.run(state)
        results["rag"] = state
        yield emit(
            "agent_done",
            {
                "agent": "rag",
                "chunks": len(state["rag_chunks"]),
                "latency": state["metrics"][-1]["latency_ms"],
            },
        )

        # ── Writer (with revision loop) ───────────────────────
        state = writer.run(state)
        yield emit(
            "agent_done",
            {
                "agent": "writer",
                "report": state["report"],
                "latency": state["metrics"][-1]["latency_ms"],
            },
        )

        # ── Critic ───────────────────────────────────────────
        state = critic.run(state)
        yield emit(
            "agent_done",
            {
                "agent": "critic",
                "quality_score": state["quality_score"],
                "latency": state["metrics"][-1]["latency_ms"],
            },
        )

        # ── Revision if needed ───────────────────────────────
        if _should_revise(state) == "revise":
            yield emit(
                "agent_done",
                {
                    "agent": "writer",
                    "status": "revising",
                    "latency": 0,
                },
            )
            state = writer.run(state)
            yield emit(
                "agent_done",
                {
                    "agent": "writer",
                    "report": state["report"],
                    "latency": state["metrics"][-1]["latency_ms"],
                },
            )
            state = critic.run(state)
            yield emit(
                "agent_done",
                {
                    "agent": "critic",
                    "quality_score": state["quality_score"],
                    "latency": state["metrics"][-1]["latency_ms"],
                },
            )

        # ── Final ────────────────────────────────────────────
        state["finished_at"] = time.time()
        total_tokens = sum(m.get("tokens_used", 0) for m in state["metrics"])

        yield emit(
            "complete",
            {
                "thread_id": thread_id,
                "query": query,
                "report": state["report"],
                "quality_score": state["quality_score"],
                "subtasks": state["subtasks"],
                "metrics": state["metrics"],
                "total_tokens": total_tokens,
                "duration_seconds": round(
                    state["finished_at"] - state["started_at"], 2
                ),
            },
        )

        # Persist to Upstash
        from app.memory.redis_state import save_job

        save_job(thread_id, state)

    except Exception as e:
        yield emit("error", {"message": str(e)})
