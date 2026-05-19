import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))

LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "autoresearch-agent")

MODEL_NAME = "claude-sonnet-4-6"
MAX_TOKENS = 4096

QUALITY_THRESHOLD = 20  # out of 30 — below this triggers a Writer revision
MAX_REVISIONS = 1
TOP_K_RAG_RESULTS = 5
