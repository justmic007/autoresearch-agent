#!/usr/bin/env python3
"""
Test all configured LLM providers with a simple 'Say OK' request.
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
        results[name] = f"✅  {response[:30]:<30} {latency}ms"
    except Exception as e:
        latency = round((time.time() - t0) * 1000)
        results[name] = f"❌  {type(e).__name__}: {str(e)[:50]} ({latency}ms)"


# ── Groq ──────────────────────────────────────────────────
def _groq():
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=10,
    )
    return r.choices[0].message.content.strip()


test("groq (llama-3.3-70b)", _groq)


# ── Gemini ────────────────────────────────────────────────
def _gemini():
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    for model in ["gemini-2.0-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
        try:
            r = client.models.generate_content(model=model, contents="Say OK only")
            return f"[{model}] {r.text.strip()}"
        except Exception:
            continue
    raise RuntimeError("All Gemini models exhausted/unavailable")


test("gemini", _gemini)


# ── NVIDIA NIM — DeepSeek V4 ──────────────────────────────
def _nvidia_deepseek():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
    )
    r = client.chat.completions.create(
        model="deepseek-ai/deepseek-v4-pro",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=20,
    )
    return r.choices[0].message.content.strip()


test("nvidia (deepseek-v4-pro)", _nvidia_deepseek)


# ── NVIDIA NIM — Gemma 4 31B ──────────────────────────────
def _nvidia_gemma():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"],
    )
    r = client.chat.completions.create(
        model="google/gemma-4-31b-it",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=20,
    )
    return r.choices[0].message.content.strip()


test("nvidia (gemma-4-31b)", _nvidia_gemma)


# ── SambaNova ─────────────────────────────────────────────
def _sambanova():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://api.sambanova.ai/v1",
        api_key=os.environ["SAMBANOVA_API_KEY"],
    )
    r = client.chat.completions.create(
        model="Meta-Llama-3.3-70B-Instruct",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=20,
    )
    return r.choices[0].message.content.strip()


test("sambanova (llama-3.3-70b)", _sambanova)


# ── Mistral ───────────────────────────────────────────────
def _mistral():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://api.mistral.ai/v1",
        api_key=os.environ["MISTRAL_API_KEY"],
    )
    r = client.chat.completions.create(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=15,
    )
    return r.choices[0].message.content.strip()


test("mistral (small-latest)", _mistral)


# ── Cerebras ──────────────────────────────────────────────
def _cerebras():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://api.cerebras.ai/v1",
        api_key=os.environ["CEREBRAS_API_KEY"],
    )
    r = client.chat.completions.create(
        model="llama3.1-8b",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=15,
    )
    return r.choices[0].message.content.strip()


test("cerebras (llama3.1-8b)", _cerebras)


# ── Cloudflare ────────────────────────────────────────────
def _cloudflare():
    import json, urllib.request

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    data = json.dumps({"messages": [{"role": "user", "content": "Say OK only"}], "max_tokens": 5}).encode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["result"]["response"].strip()


test("cloudflare (llama-3.3-70b-fp8)", _cloudflare)


# ── Hugging Face ──────────────────────────────────────────
def _huggingface():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://api-inference.huggingface.co/v1",
        api_key=os.environ["HUGGINGFACE_API_KEY"],
    )
    r = client.chat.completions.create(
        model="meta-llama/Llama-3.3-70B-Instruct",
        messages=[{"role": "user", "content": "Say OK only"}],
        max_tokens=5,
        timeout=20,
    )
    return r.choices[0].message.content.strip()


test("huggingface (llama-3.3-70b)", _huggingface)


# ── OpenRouter ────────────────────────────────────────────
def _openrouter():
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    for model in [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-3-27b-it:free",
    ]:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say OK only"}],
                max_tokens=5,
                timeout=20,
            )
            content = r.choices[0].message.content or ""
            if content.strip():
                return f"[{model.split('/')[1]}] {content.strip()}"
        except Exception:
            continue
    raise RuntimeError("All OpenRouter free models failed")


test("openrouter (free)", _openrouter)


# ── Print results ─────────────────────────────────────────
print()
print("Provider Health Check")
print("=" * 70)
for provider, status in results.items():
    print(f"  {provider:<28} {status}")
print("=" * 70)
working = sum(1 for s in results.values() if s.startswith("✅"))
print(f"  {working}/{len(results)} providers operational")
print()
if working < len(results):
    failed = [p for p, s in results.items() if not s.startswith("✅")]
    print(f"  Failed: {', '.join(failed)}")
    print()
