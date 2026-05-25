#!/usr/bin/env python3
"""
Test all configured LLM providers matching exact model names in config.py
Run with: python -m app.utils.test_providers
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

results = {}


def test(name: str, fn):
    t0 = time.time()
    try:
        response = fn()
        latency = round((time.time() - t0) * 1000)
        results[name] = f"✅  {str(response)[:30]:<30} {latency}ms"
    except Exception as e:
        latency = round((time.time() - t0) * 1000)
        results[name] = f"❌  {type(e).__name__}: {str(e)[:50]} ({latency}ms)"


def _groq(model: str):
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=10,
    )
    return r.choices[0].message.content.strip()


def _openai_compat(base_url: str, api_key: str, model: str):
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=20,
    )
    return r.choices[0].message.content.strip()


def _gemini(model: str):
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    r = client.models.generate_content(model=model, contents="Say OK only")
    return r.text.strip()


# ── GROQ ──────────────────────────────────────────────────
test("groq llama-4-scout (169ms)",   lambda: _groq("meta-llama/llama-4-scout-17b-16e-instruct"))
test("groq qwen3-32b (424ms)",       lambda: _groq("qwen/qwen3-32b"))
test("groq llama-3.3-70b (1.4s)",    lambda: _groq("llama-3.3-70b-versatile"))

# ── GEMINI ────────────────────────────────────────────────
test("gemini 2.5-flash-lite",        lambda: _gemini("gemini-2.5-flash-lite"))

# ── NVIDIA NIM ────────────────────────────────────────────
test("nvidia deepseek-v4-flash",     lambda: _openai_compat(
    "https://integrate.api.nvidia.com/v1", os.environ["NVIDIA_API_KEY"], "deepseek-ai/deepseek-v4-flash"))
test("nvidia llama-3.3-70b",         lambda: _openai_compat(
    "https://integrate.api.nvidia.com/v1", os.environ["NVIDIA_API_KEY"], "meta/llama-3.3-70b-instruct"))

# ── SAMBANOVA ─────────────────────────────────────────────
test("sambanova DeepSeek-V3.2",      lambda: _openai_compat(
    "https://api.sambanova.ai/v1", os.environ["SAMBANOVA_API_KEY"], "DeepSeek-V3.2"))
test("sambanova Llama-3.3-70B",      lambda: _openai_compat(
    "https://api.sambanova.ai/v1", os.environ["SAMBANOVA_API_KEY"], "Meta-Llama-3.3-70B-Instruct"))
test("sambanova Llama-4-Maverick",   lambda: _openai_compat(
    "https://api.sambanova.ai/v1", os.environ["SAMBANOVA_API_KEY"], "Llama-4-Maverick-17B-128E-Instruct"))

# ── MISTRAL ───────────────────────────────────────────────
test("mistral small-latest",         lambda: _openai_compat(
    "https://api.mistral.ai/v1", os.environ["MISTRAL_API_KEY"], "mistral-small-latest"))

# ── CEREBRAS ──────────────────────────────────────────────
test("cerebras llama3.1-8b",         lambda: _openai_compat(
    "https://api.cerebras.ai/v1", os.environ["CEREBRAS_API_KEY"], "llama3.1-8b"))
test("cerebras qwen-3-235b",         lambda: _openai_compat(
    "https://api.cerebras.ai/v1", os.environ["CEREBRAS_API_KEY"], "qwen-3-235b-a22b-instruct-2507"))

# ── HUGGINGFACE / NOVITA ──────────────────────────────────
test("hf-novita llama-3.3-70b",      lambda: _openai_compat(
    "https://router.huggingface.co/novita/v3/openai", os.environ["HUGGINGFACE_API_KEY"], "meta-llama/llama-3.3-70b-instruct"))

# ── OPENROUTER ────────────────────────────────────────────
test("openrouter gemma-4-26b:free",  lambda: _openai_compat(
    "https://openrouter.ai/api/v1", os.environ["OPENROUTER_API_KEY"], "google/gemma-4-26b-a4b-it:free"))

# ── Print results ─────────────────────────────────────────
print()
print("Provider Health Check — matching config.py model names")
print("=" * 70)
for provider, status in results.items():
    print(f"  {provider:<35} {status}")
print("=" * 70)
working = sum(1 for s in results.values() if s.startswith("✅"))
print(f"  {working}/{len(results)} providers operational")
print()
if working < len(results):
    failed = [p for p, s in results.items() if not s.startswith("✅")]
    print(f"  Failed: {', '.join(failed)}")
    print()
