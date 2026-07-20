"""Thin wrapper around the local Ollama HTTP API. No cloud calls, ever."""

import requests

OLLAMA_HOST = "http://localhost:11434"


def list_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except requests.RequestException:
        return []


def query_model(prompt: str, model: str, system_prompt: str = "", timeout: int = 60) -> str:
    """Single-turn, temperature-0 query. Returns the raw text response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    try:
        r = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.RequestException as e:
        return f"ERROR: {e}"
