"""Local embedding helpers via Ollama's /api/embeddings endpoint.

No cloud calls — same principle as the rest of the stack.

IMPORTANT: nomic-embed-text is an asymmetric retrieval model — it expects
task prefixes to produce reliable similarity scores. Without them, cosine
similarity between a short category description and a long contract clause
can come out inconsistently low even for genuine matches. See:
https://ollama.com/library/nomic-embed-text
"""

import math
import requests

from ollama_client import OLLAMA_HOST


def embed(text: str, model: str = "nomic-embed-text", task: str = "search_document") -> list[float] | None:
    """task: 'search_document' for the text being searched (contract segments),
    'search_query' for the thing you're searching WITH (category descriptions)."""
    prefixed = f"{task}: {text}" if model == "nomic-embed-text" else text
    try:
        r = requests.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": model, "prompt": prefixed},
            timeout=30,
        )
        r.raise_for_status()
        vec = r.json().get("embedding")
        return vec if vec else None
    except requests.RequestException:
        return None


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
