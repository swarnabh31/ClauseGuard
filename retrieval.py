"""Stage 1: candidate generation — keyword matching + optional semantic retrieval.

Two independent retrieval paths feed the same candidate pool:
  - Keyword matching: fast, precise for clauses that use standard boilerplate
    phrasing, but misses paraphrases (e.g. Google writing "Google's total
    liability... is limited to the greater of $500..." instead of the
    literal string "limit our liability").
  - Semantic (embedding) matching: catches paraphrases by comparing each
    segment's embedding against a reference embedding of the category's
    description. Requires an embedding model (nomic-embed-text) running
    locally via Ollama; silently skipped if unavailable.

Both paths still go through exclude_keywords suppression and, downstream,
the LLM verification gate — retrieval only produces candidates, never a
final answer.
"""

from models import Candidate, Evidence
from segmenter import segment_text, clip
from categories import RISK_CATEGORIES
from embeddings import embed, cosine_similarity

SEMANTIC_THRESHOLD = 0.40  # was 0.55 — real nomic-embed-text scores for genuine
# paraphrase matches (tested via prefix fix above) tend to run lower than
# same-wording matches. Still a guess, not calibrated — see README re: eval set.
_category_embedding_cache: dict[str, list[float] | None] = {}


def _is_excluded(seg_lower: str, cat: dict) -> bool:
    return any(kw in seg_lower for kw in cat.get("exclude_keywords", []))


def _keyword_candidates(segments: list[tuple[str, str]]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for section_ref, seg_text in segments:
        s_lower = seg_text.lower()
        for cat_key, cat in RISK_CATEGORIES.items():
            hits = [kw for kw in cat["keywords"] if kw in s_lower]
            if not hits or _is_excluded(s_lower, cat):
                continue
            coverage = len(hits) / len(cat["keywords"])
            retrieval_conf = min(1.0, coverage * 1.3 + 0.2)
            candidates.append(Candidate(
                category_key=cat_key,
                evidence=Evidence(text=clip(seg_text), section_ref=section_ref),
                keyword_hits=hits,
                retrieval_confidence=retrieval_conf,
            ))
    return candidates


def _category_reference_embedding(cat_key: str, cat: dict, embed_model: str) -> list[float] | None:
    cache_key = f"{embed_model}:{cat_key}"
    if cache_key not in _category_embedding_cache:
        reference_text = f"{cat['label']}. {cat['interpretation']}"
        _category_embedding_cache[cache_key] = embed(reference_text, model=embed_model, task="search_query")
    return _category_embedding_cache[cache_key]


def _semantic_candidates(
    segments: list[tuple[str, str]],
    embed_model: str,
    threshold: float = SEMANTIC_THRESHOLD,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    cat_embeddings = {
        cat_key: _category_reference_embedding(cat_key, cat, embed_model)
        for cat_key, cat in RISK_CATEGORIES.items()
    }
    if all(v is None for v in cat_embeddings.values()):
        return []  # embedding model unavailable — fail silent, keyword path still runs

    for section_ref, seg_text in segments:
        if len(seg_text) < 15:
            continue
        s_lower = seg_text.lower()
        seg_emb = embed(seg_text, model=embed_model)
        if seg_emb is None:
            continue
        for cat_key, cat in RISK_CATEGORIES.items():
            ref_emb = cat_embeddings.get(cat_key)
            if ref_emb is None or _is_excluded(s_lower, cat):
                continue
            sim = cosine_similarity(seg_emb, ref_emb)
            if sim >= threshold:
                candidates.append(Candidate(
                    category_key=cat_key,
                    evidence=Evidence(text=clip(seg_text), section_ref=section_ref),
                    keyword_hits=["<semantic match, no literal keyword>"],
                    retrieval_confidence=sim,
                ))
    return candidates


TOP_K = 3


def find_candidates(text: str, embed_model: str | None = None) -> dict[str, list[Candidate]]:
    """Returns at most TOP_K candidates per category, sorted by confidence descending.
    The LLM gate downstream tries each in order until one passes — this gives the
    correct clause a chance even when a higher-scoring-but-wrong neighbor wins
    the raw similarity contest (the core bug this fixes)."""
    segments = segment_text(text)
    candidates = _keyword_candidates(segments)

    if embed_model:
        candidates += _semantic_candidates(segments, embed_model)

    groups: dict[str, list[Candidate]] = {}
    for c in candidates:
        groups.setdefault(c.category_key, []).append(c)

    result: dict[str, list[Candidate]] = {}
    for k, lst in groups.items():
        lst.sort(key=lambda x: x.retrieval_confidence, reverse=True)
        result[k] = lst[:TOP_K]

    return result
