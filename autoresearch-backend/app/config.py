import os
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# ── Active providers (all confirmed working) ───────────────────────────────────
# ==============================================================================

# Gemini — 1,500 req/day free
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-2.5-flash-lite"                          # 786ms ✅

# Groq — 1,000 req/day free per model, fastest provider
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL_FAST = "meta-llama/llama-4-scout-17b-16e-instruct"  # 169ms ✅
GROQ_MODEL = "llama-3.3-70b-versatile"                         # 1.4s  ✅
GROQ_MODEL_CRITIC = "meta-llama/llama-4-scout-17b-16e-instruct"

# NVIDIA NIM — no daily cap, 40 RPM
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL_WRITER = "deepseek-ai/deepseek-v4-flash"          # 3.5s  ✅
NVIDIA_MODEL_LLAMA = "meta/llama-3.3-70b-instruct"             # 916ms ✅

# SambaNova — free, strong models
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
SAMBANOVA_MODEL = "Meta-Llama-3.3-70B-Instruct"                # 1.9s  ✅
SAMBANOVA_MODEL_DEEPSEEK = "DeepSeek-V3.2"                     # 1.7s  ✅
SAMBANOVA_MODEL_MAVERICK = "Llama-4-Maverick-17B-128E-Instruct" # 1.4s ✅

# Mistral — 1B tokens/month free
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL = "mistral-small-latest"                         # 1.0s  ✅

# Cerebras — fast inference, free
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = "llama3.1-8b"                                 # 1.7s  ✅
CEREBRAS_MODEL_LARGE = "qwen-3-235b-a22b-instruct-2507"        # 3.1s  ✅

# HuggingFace router (novita backend) — free
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
HF_NOVITA_MODEL = "meta-llama/llama-3.3-70b-instruct"          # 816ms ✅
HF_NOVITA_MODEL_SMALL = "meta-llama/llama-3.1-8b-instruct"     # 1.6s  ✅

# OpenRouter — gemma-4-26b is the most reliable free model
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"            # 922ms ✅

# ==============================================================================
# ── Thresholds & limits ────────────────────────────────────────────────────────
# ==============================================================================
QUALITY_THRESHOLD = 20  # below this → trigger revision
MAX_REVISIONS = 1
TOP_K_RAG_RESULTS = 5
MAX_TOKENS = 2048

# ==============================================================================
# ── Infrastructure ─────────────────────────────────────────────────────────────
# ==============================================================================
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))
UPSTASH_REDIS_URL = os.environ["UPSTASH_REDIS_URL"]

# ==============================================================================
# ── Observability ──────────────────────────────────────────────────────────────
# ==============================================================================
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "autoresearch-agent")
