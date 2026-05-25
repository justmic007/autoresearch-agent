# Unit tests for planner, critic, search, rag, and writer agents

"""
Unit tests — run with: pytest tests/ -v
These mock external clients so no API key is needed in CI.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from app.graph.state import initial_state


# ---- helpers ----

def _mock_groq_response(text: str, total_tokens=80):
    msg = MagicMock()
    msg.choices[0].message.content = text
    msg.usage.total_tokens = total_tokens
    return msg


def _state_with_subtasks(subtasks=None):
    state = initial_state(query="What is quantum computing?", thread_id="test-search-1")
    state["subtasks"] = subtasks or ["quantum computing basics", "quantum hardware 2024"]
    return state


def _state_with_search_results():
    state = _state_with_subtasks()
    state["search_results"] = [
        {"subtask": "quantum computing basics", "results": [
            {"title": "Intro to QC", "url": "https://example.com/qc", "content": "Quantum computers use qubits."},
            {"title": "QC Overview", "url": "https://example.com/qc2", "content": "Superposition enables parallelism."},
        ]},
    ]
    return state


# ---- planner ----

def test_planner_returns_subtasks():
    from app.agents import planner
    state = initial_state(query="What is the state of AI in healthcare?", thread_id="test-1")
    with patch("app.agents.planner._try_groq", return_value=(
        ["AI diagnostics 2024", "AI drug discovery", "FDA AI regulation"], 80
    )):
        result = planner.run(state)
    assert len(result["subtasks"]) == 3
    assert result["subtasks"][0] == "AI diagnostics 2024"
    assert len(result["metrics"]) == 1
    assert "planner" in result["metrics"][0]["agent"]


def test_planner_records_latency():
    from app.agents import planner
    state = initial_state(query="Test query", thread_id="test-2")
    with patch("app.agents.planner._try_groq", return_value=(["a", "b"], 40)):
        result = planner.run(state)
    assert result["metrics"][0]["latency_ms"] >= 0


def test_planner_falls_back_to_static():
    from app.agents import planner
    state = initial_state(query="What is fusion energy?", thread_id="test-planner-fallback")
    with patch("app.agents.planner._try_groq", side_effect=Exception("API down")):
        result = planner.run(state)
    assert len(result["subtasks"]) == 3
    assert "static-fallback" in result["metrics"][0]["agent"]


# ---- critic ----

def test_critic_scores_report():
    from app.agents import critic
    state = initial_state(query="Test", thread_id="test-3")
    state["report"] = "Some report content here."
    fake_reply = json.dumps({
        "completeness": 8, "accuracy": 7, "coherence": 9,
        "feedback": "Add more primary sources.",
    })
    with patch("app.agents.critic._try_groq", return_value=(fake_reply, 80)):
        result = critic.run(state)
    score = result["quality_score"]
    assert score["total"] == 24
    assert score["completeness"] == 8
    assert "feedback" in score


def test_critic_falls_back_to_static():
    from app.agents import critic
    state = initial_state(query="Test", thread_id="test-critic-fallback")
    state["report"] = "Some report."
    with patch("app.agents.critic._try_groq", side_effect=Exception("API down")), \
         patch("app.agents.critic._call_openai_compatible", side_effect=Exception("API down")):
        result = critic.run(state)
    score = result["quality_score"]
    assert score["total"] == 21
    assert score["completeness"] == 7


# ---- search ----

def test_search_returns_results_per_subtask():
    from app.agents import search
    state = _state_with_subtasks(["quantum computing basics", "quantum hardware 2024"])
    fake_results = [{"title": "T", "url": "https://x.com", "content": "content"}]
    with patch("app.agents.search.search", return_value=fake_results):
        result = search.run(state)
    assert len(result["search_results"]) == 2
    assert result["search_results"][0]["results"] == fake_results


def test_search_records_metric():
    from app.agents import search
    state = _state_with_subtasks(["one subtask"])
    with patch("app.agents.search.search", return_value=[]):
        result = search.run(state)
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["agent"] == "search"
    assert result["metrics"][0]["tokens_used"] == 0
    assert result["metrics"][0]["latency_ms"] >= 0


def test_search_handles_empty_subtasks():
    from app.agents import search
    state = initial_state(query="What is quantum computing?", thread_id="test-search-empty")
    state["subtasks"] = []
    result = search.run(state)
    assert result["search_results"] == []
    assert len(result["metrics"]) == 1


# ---- rag ----

def test_rag_stores_and_retrieves_chunks():
    from app.agents import rag
    from app.tools import embedder
    state = _state_with_search_results()
    state["thread_id"] = "test-rag-1"

    with patch("app.tools.embedder._embed_batch", return_value=None):
        result = rag.run(state)

    assert len(result["rag_chunks"]) > 0
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["agent"] == "rag"


def test_rag_returns_empty_for_no_results():
    from app.agents import rag
    state = initial_state(query="test", thread_id="test-rag-empty")
    state["search_results"] = []
    result = rag.run(state)
    assert result["rag_chunks"] == []


def test_embedder_keyword_fallback():
    from app.tools.embedder import embed_and_store, retrieve
    thread_id = "test-embed-fallback"
    chunks = [
        "quantum computers use qubits for computation",
        "climate change affects global temperatures",
        "quantum entanglement enables teleportation",
    ]
    embed_and_store(thread_id, chunks)
    with patch("app.tools.embedder._embed_batch", return_value=None):
        results = retrieve("quantum computing qubits", thread_id, top_k=2)
    assert len(results) == 2
    assert any("quantum" in r for r in results)


def test_embedder_semantic_retrieval():
    from app.tools.embedder import embed_and_store, retrieve
    thread_id = "test-embed-semantic"
    chunks = ["AI regulation in Europe", "battery technology advances", "fusion energy progress"]
    embed_and_store(thread_id, chunks)

    fake_vecs = [
        [1.0, 0.0, 0.0],   # query
        [0.9, 0.1, 0.0],   # AI regulation — most similar
        [0.0, 1.0, 0.0],   # battery
        [0.0, 0.0, 1.0],   # fusion
    ]
    with patch("app.tools.embedder._embed_batch", return_value=fake_vecs):
        results = retrieve("AI policy", thread_id, top_k=1)
    assert results[0] == "AI regulation in Europe"


# ---- writer ----

def test_writer_returns_report():
    from app.agents import writer
    state = _state_with_search_results()
    state["rag_chunks"] = ["Quantum computers use qubits instead of classical bits."]
    state["revision_count"] = 0

    with patch("app.agents.writer._call_openai_compatible", return_value=("## Report\nContent here with enough text to pass the length check.", 200)):
        result = writer.run(state)

    assert len(result["report"]) > 0
    assert result["revision_count"] == 1
    assert len(result["metrics"]) == 1
    assert "writer" in result["metrics"][0]["agent"]


def test_writer_increments_revision_count():
    from app.agents import writer
    state = _state_with_search_results()
    state["rag_chunks"] = []
    state["revision_count"] = 1
    state["quality_score"] = {"completeness": 7, "accuracy": 7, "coherence": 7, "total": 21, "feedback": "needs work"}

    with patch("app.agents.writer._call_openai_compatible", return_value=("## Revised Report\n" + "x" * 200, 300)):
        result = writer.run(state)

    assert result["revision_count"] == 2


def test_writer_falls_back_to_static():
    from app.agents import writer
    state = _state_with_search_results()
    state["rag_chunks"] = []
    state["revision_count"] = 0

    with patch("app.agents.writer._call_openai_compatible", side_effect=Exception("rate limit")), \
         patch("app.agents.writer._try_gemini", side_effect=Exception("quota")), \
         patch("app.agents.writer._try_groq", side_effect=Exception("rate limit")):
        result = writer.run(state)

    assert "static-fallback" in result["metrics"][0]["agent"]
    assert "Executive Summary" in result["report"]


# ---- state ----

def test_initial_state_defaults():
    state = initial_state("my query", "thread-abc")
    assert state["query"] == "my query"
    assert state["subtasks"] == []
    assert state["revision_count"] == 0
    assert state["quality_score"] is None
    assert state["metrics"] == []
