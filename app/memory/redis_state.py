# Redis memory state
import json
import redis
import os
from dotenv import load_dotenv

load_dotenv()

_client = redis.from_url(
    os.environ["UPSTASH_REDIS_URL"],
    decode_responses=True,
    # ssl_cert_reqs=None,  # Upstash free tier uses self-signed cert
)

NAMESPACE = "autoresearch"
TTL_SECONDS = 86400  # 24 hours


def _key(thread_id: str) -> str:
    return f"{NAMESPACE}:job:{thread_id}"


def save_job(thread_id: str, state: dict) -> None:
    """Persist a completed research job to Upstash Redis."""
    payload = {
        "thread_id": thread_id,
        "query": state.get("query", ""),
        "report": state.get("report", ""),
        "quality_score": state.get("quality_score", {}),
        "subtasks": state.get("subtasks", []),
        "metrics": state.get("metrics", []),
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
    }
    _client.setex(_key(thread_id), TTL_SECONDS, json.dumps(payload))


def load_job(thread_id: str) -> dict | None:
    """Retrieve a completed job by thread_id. Returns None if not found."""
    raw = _client.get(_key(thread_id))
    return json.loads(raw) if raw else None


def list_jobs() -> list[dict]:
    """List all stored jobs (summary only — no full report)."""
    keys = _client.keys(f"{NAMESPACE}:job:*")
    jobs = []
    for key in keys:
        raw = _client.get(key)
        if raw:
            data = json.loads(raw)
            jobs.append(
                {
                    "thread_id": data["thread_id"],
                    "query": data["query"],
                    "quality_score": data.get("quality_score", {}).get("total", 0),
                    "finished_at": data.get("finished_at"),
                }
            )
    return sorted(jobs, key=lambda x: x["finished_at"] or 0, reverse=True)


def delete_job(thread_id: str) -> bool:
    """Delete a job. Returns True if it existed."""
    return _client.delete(_key(thread_id)) > 0
