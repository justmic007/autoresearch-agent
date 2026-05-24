# Unit tests for planner and critic agents

"""
Unit tests — run with: pytest tests/ -v
These mock the Groq client so no API key is needed in CI.
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


# ---- planner ----

def test_planner_returns_subtasks():
    from app.agents import planner

    state = initial_state(
        query="What is the state of AI in healthcare?", thread_id="test-1"
    )

    fake_reply = json.dumps(
        {"subtasks": ["AI diagnostics 2024", "AI drug discovery", "FDA AI regulation"]}
    )

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


# ---- critic ----

def test_critic_scores_report():
    from app.agents import critic

    state = initial_state(query="Test", thread_id="test-3")
    state["report"] = "Some report content here."

    fake_reply = json.dumps(
        {
            "completeness": 8,
            "accuracy": 7,
            "coherence": 9,
            "feedback": "Add more primary sources.",
        }
    )

    with patch("app.agents.critic._try_groq", return_value=(fake_reply, 80)):
        result = critic.run(state)

    score = result["quality_score"]
    assert score["total"] == 24
    assert score["completeness"] == 8
    assert "feedback" in score


# ---- state ----

def test_initial_state_defaults():
    state = initial_state("my query", "thread-abc")
    assert state["query"] == "my query"
    assert state["subtasks"] == []
    assert state["revision_count"] == 0
    assert state["quality_score"] is None
    assert state["metrics"] == []
