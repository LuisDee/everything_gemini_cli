"""Stdlib HTTP client for LLM calls via Gemini API or LiteLLM proxy.

Auto-detects backend:
  1. LiteLLM proxy at localhost:4000 (if reachable)
  2. Gemini REST API (if GEMINI_API_KEY set)

Uses only urllib (no third-party dependencies).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from typing import Any


def _get_litellm_key() -> str | None:
    """Try to get LiteLLM master key from pass."""
    try:
        result = subprocess.run(
            ["pass", "show", "api/litellm-master"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_gemini_key() -> str | None:
    """Get Gemini API key from env or pass."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        result = subprocess.run(
            ["pass", "show", "api/gemini"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _litellm_available() -> bool:
    """Check if LiteLLM proxy is reachable."""
    try:
        req = urllib.request.Request(
            "http://localhost:4000/health",
            method="GET",
        )
        urllib.request.urlopen(req, timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def call_llm(
    prompt: str,
    system: str = "",
    model: str = "claude-sonnet",
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Call an LLM and return the text response.

    Tries LiteLLM proxy first, falls back to Gemini REST API.
    """
    # Try LiteLLM proxy first
    if _litellm_available():
        return _call_litellm(prompt, system, model, max_tokens, temperature)

    # Fall back to Gemini API
    gemini_key = _get_gemini_key()
    if gemini_key:
        return _call_gemini(prompt, system, gemini_key, max_tokens, temperature)

    raise RuntimeError(
        "No LLM backend available. Start LiteLLM proxy or set GEMINI_API_KEY."
    )


def _call_litellm(
    prompt: str,
    system: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call LiteLLM proxy (OpenAI-compatible API)."""
    key = _get_litellm_key()
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(
        "http://localhost:4000/v1/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _call_gemini(
    prompt: str,
    system: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Gemini REST API directly."""
    model = "gemini-2.5-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent?key={api_key}"
    )

    contents: list[dict[str, Any]] = []
    if system:
        contents.append({
            "role": "user",
            "parts": [{"text": f"[System instruction] {system}"}],
        })
        contents.append({
            "role": "model",
            "parts": [{"text": "Understood."}],
        })
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}],
    })

    body = json.dumps({
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini API returned no candidates: {data}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def extract_tag(text: str, tag: str) -> str:
    """Extract content between <tag>...</tag> from text."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()
