# Benchmark script - runs 5 test queries and prints a metrics table

"""
Run this after the app is up:
    python -m app.eval.benchmark

Outputs a table of latency, token cost, and quality scores
across 5 test queries.
"""

import json
import time
import uuid
from app.graph.workflow import run_research

TEST_QUERIES = [
    "What is the current state of AI regulation in the European Union?",
    "What are the latest breakthroughs in battery technology for electric vehicles?",
    "How is generative AI impacting the software engineering job market?",
    "What is the state of nuclear fusion energy development in 2025?",
    "How are central banks responding to persistent inflation globally?",
]


def run_benchmark():
    results = []
    print(
        f"\n{'Query':<55} {'Duration':>9} {'Tokens':>8} {'Quality':>9} {'Revised':>8}"
    )
    print("-" * 95)

    for query in TEST_QUERIES:
        thread_id = str(uuid.uuid4())
        t0 = time.time()

        state = run_research(query=query, thread_id=thread_id)
        duration = round(time.time() - t0, 1)

        total_tokens = sum(m.get("tokens_used", 0) for m in state.get("metrics", []))
        quality = state.get("quality_score", {}).get("total", 0)
        revised = "yes" if state.get("revision_count", 0) > 1 else "no"
        short_q = query[:52] + "..." if len(query) > 52 else query

        print(
            f"{short_q:<55} {duration:>8}s {total_tokens:>8} {quality:>8}/30 {revised:>8}"
        )
        results.append(
            {
                "query": query,
                "duration_s": duration,
                "tokens_used": total_tokens,
                "quality_total": quality,
                "revised": revised == "yes",
            }
        )

    avg_dur = sum(r["duration_s"] for r in results) / len(results)
    avg_tokens = sum(r["tokens_used"] for r in results) / len(results)
    avg_quality = sum(r["quality_total"] for r in results) / len(results)

    print("-" * 95)
    print(
        f"{'AVERAGES':<55} {avg_dur:>8.1f}s {avg_tokens:>8.0f} {avg_quality:>8.1f}/30"
    )

    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to eval_results.json")


if __name__ == "__main__":
    run_benchmark()
