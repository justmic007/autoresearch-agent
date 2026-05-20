from app.config import TOP_K_RAG_RESULTS

_store: dict[str, list[str]] = {}


def embed_and_store(thread_id: str, chunks: list[str]) -> None:
    if not chunks:
        return
    _store[thread_id] = chunks


def retrieve(query: str, thread_id: str, top_k: int = TOP_K_RAG_RESULTS) -> list[str]:
    chunks = _store.get(thread_id, [])
    if not chunks:
        return []
    query_words = set(query.lower().split())

    def score(chunk: str) -> int:
        return len(query_words & set(chunk.lower().split()))

    return sorted(chunks, key=score, reverse=True)[:top_k]


# # ChromaDB embedder -  store and retrieve document chunks

# import chromadb
# from sentence_transformers import SentenceTransformer
# from app.config import CHROMA_HOST, CHROMA_PORT, TOP_K_RAG_RESULTS

# _model = SentenceTransformer("all-MiniLM-L6-v2")
# _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
# _collection = _client.get_or_create_collection(
#     name="research_docs",
#     metadata={"hnsw:space": "cosine"},
# )


# def embed_and_store(thread_id: str, chunks: list[str]) -> None:
#     """Embed text chunks and store them under the given thread_id."""
#     if not chunks:
#         return
#     embeddings = _model.encode(chunks).tolist()
#     ids = [f"{thread_id}_{i}" for i in range(len(chunks))]
#     _collection.upsert(
#         ids=ids,
#         embeddings=embeddings,
#         documents=chunks,
#         metadatas=[{"thread_id": thread_id}] * len(chunks),
#     )


# def retrieve(query: str, thread_id: str, top_k: int = TOP_K_RAG_RESULTS) -> list[str]:
#     """Retrieve top-k most relevant chunks for a query within the thread."""
#     query_embedding = _model.encode([query]).tolist()
#     results = _collection.query(
#         query_embeddings=query_embedding,
#         n_results=top_k,
#         where={"thread_id": thread_id},
#     )
#     return results.get("documents", [[]])[0]
