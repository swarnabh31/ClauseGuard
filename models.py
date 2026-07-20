"""Core data structures shared across the pipeline.

Design note: `Finding.verified` and `Finding.reason` are NOT optional.
Every finding must say (a) whether an LLM actually checked it, and
(b) why, in the model's own words. This is what stops the UI from ever
showing a heuristic guess with a "Verified" badge.
"""

from dataclasses import dataclass, field


@dataclass
class Evidence:
    text: str            # clipped, word-boundary-safe excerpt
    section_ref: str = ""


@dataclass
class Candidate:
    """Stage 1 output — a keyword hit, not yet trusted."""
    category_key: str
    evidence: Evidence
    keyword_hits: list[str]
    retrieval_confidence: float  # 0-1, keyword strength only


@dataclass
class Finding:
    """Stage 2 output — the only thing the UI is allowed to render as a result."""
    category_key: str
    severity: str                 # critical | high | medium | low
    confidence_pct: int           # 0-100
    verified: bool                # True only if an LLM actually checked THIS finding
    reason: str                   # model's own justification, always shown to the user
    evidence: Evidence
    interpretation: str
    impact_statement: str
    suggested_action: str
