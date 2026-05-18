# ChromaDB embedder -  store and retrieve document chunks
import chromadb
from sentence_transformers import SentenceTransformer
from app.config import CHROMA_HOST, CHROMA_PORT, TOP_K_RAG_RESULTS

_model = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
_collection = _client.get_or_create_collection(
    name="research_docs",
    metadata={"hnsw:space": "cosine"},
)


def embed_and_store(thread_id: str, chunks: list[str]) -> None:
    """Embed text chunks and store them under the given thread_id."""
    if not chunks:
        return
    embeddings = _model.encode(chunks).tolist()
    ids = [f"{thread_id}_{i}" for i in range(len(chunks))]
    _collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"thread_id": thread_id}] * len(chunks),
    )


def retrieve(query: str, thread_id: str, top_k: int = TOP_K_RAG_RESULTS) -> list[str]:
    """Retrieve top-k most relevant chunks for a query within the thread."""
    query_embedding = _model.encode([query]).tolist()
    results = _collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"thread_id": thread_id},
    )
    return results.get("documents", [[]])[0]
