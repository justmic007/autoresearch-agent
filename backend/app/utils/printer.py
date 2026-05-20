import json
import sys


def print_report(data: dict) -> None:
    q = data.get("quality_score", {})
    metrics = data.get("metrics", [])
    total_tokens = sum(m.get("tokens_used", 0) for m in metrics)

    # ── Header ────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print(f"  AUTORESEARCH AGENT — REPORT")
    print("═" * 70)
    print(f"  Query     : {data.get('query', '')}")
    print(f"  Thread ID : {data.get('thread_id', '')}")
    print(f"  Duration  : {data.get('duration_seconds', 0)}s")
    print(f"  Tokens    : {total_tokens}")
    print("═" * 70)

    # ── Report body ───────────────────────────────────────────
    print()
    print(data.get("report", ""))

    # ── Subtasks ──────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  SUBTASKS")
    print("─" * 70)
    for i, subtask in enumerate(data.get("subtasks", []), 1):
        print(f"  {i}. {subtask}")

    # ── Quality score ─────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  QUALITY SCORE")
    print("─" * 70)
    print(f"  Completeness : {q.get('completeness', 0)}/10")
    print(f"  Accuracy     : {q.get('accuracy', 0)}/10")
    print(f"  Coherence    : {q.get('coherence', 0)}/10")
    print(f"  Total        : {q.get('total', 0)}/30")
    print(f"  Feedback     : {q.get('feedback', '')}")

    # ── Per-agent metrics ─────────────────────────────────────
    print("\n" + "─" * 70)
    print("  AGENT METRICS")
    print("─" * 70)
    print(f"  {'Agent':<12} {'Latency':>10}   {'Tokens':>8}")
    print(f"  {'─'*12} {'─'*10}   {'─'*8}")
    for m in metrics:
        print(
            f"  {m['agent']:<12} {m['latency_ms']:>9.0f}ms" f"   {m['tokens_used']:>8}"
        )
    print("═" * 70 + "\n")


if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    print_report(data)
