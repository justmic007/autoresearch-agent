# LangGraph state machine wiring all agents together the revision loop

import time
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.redis import RedisSaver

from app.graph.state import ResearchState
from app.agents import planner, search, rag, writer, critic
from app.config import REDIS_URL, QUALITY_THRESHOLD, MAX_REVISIONS


def _should_revise(state: ResearchState) -> str:
    """
    Conditional edge: route back to writer for one revision
    if the quality score is below threshold and we haven't
    exceeded the max revision count.
    """
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
    """Return the graph compiled with Redis checkpointer for state persistence."""
    graph = build_graph()
    checkpointer = RedisSaver.from_conn_string(REDIS_URL)
    return graph.compile(checkpointer=checkpointer)


def run_research(query: str, thread_id: str) -> ResearchState:
    """Entry point: run the full research pipeline for a query."""
    from app.graph.state import initial_state

    app = get_compiled_graph()
    state = initial_state(query=query, thread_id=thread_id)

    config = {"configurable": {"thread_id": thread_id}}
    final = app.invoke(state, config=config)

    final["finished_at"] = time.time()
    return final
