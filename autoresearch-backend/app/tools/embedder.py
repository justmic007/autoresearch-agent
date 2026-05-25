# RAG embedder — uses Gemini embedding-001 for semantic similarity
# Falls back to keyword scoring if Gemini is unavailable

import numpy as np
from app.config import TOP_K_RAG_RESULTS, GEMINI_API_KEY

_store: dict[str, list[str]] = {}


def _cosine(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / norm) if norm > 0 else 0.0


def _embed_batch(texts: list[str]) -> list[list[float]] | None:
    """Embed a batch of texts in a single Gemini API call. Returns None on failure."""
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
        )
        return [e.values for e in result.embeddings]
    except Exception as e:
        print(f"[embedder] Gemini embedding failed ({type(e).__name__}: {e}) — falling back to keyword")
        return None


def _keyword_score(query: str, chunk: str) -> int:
    query_words = set(query.lower().split())
    return len(query_words & set(chunk.lower().split()))


def embed_and_store(thread_id: str, chunks: list[str]) -> None:
    if not chunks:
        return
    _store[thread_id] = chunks


def retrieve(query: str, thread_id: str, top_k: int = TOP_K_RAG_RESULTS) -> list[str]:
    chunks = _store.get(thread_id, [])
    if not chunks:
        return []

    # Embed query + all chunks in one batch call
    vecs = _embed_batch([query] + chunks)

    if vecs is not None:
        query_vec, chunk_vecs = vecs[0], vecs[1:]
        scored = sorted(
            range(len(chunks)),
            key=lambda i: _cosine(query_vec, chunk_vecs[i]),
            reverse=True,
        )
    else:
        # Keyword fallback
        query_words = set(query.lower().split())
        scored = sorted(
            range(len(chunks)),
            key=lambda i: _keyword_score(query, chunks[i]),
            reverse=True,
        )

    return [chunks[i] for i in scored[:top_k]]
