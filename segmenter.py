"""Splits raw contract text into segments the rule engine can scan.

Two strategies, in order of preference:
  1. Numbered sections (Section/Article/Clause/§) if the doc has them.
  2. Sentence-based fallback, with a hard cap on how much text can be
     buffered together — this is the fix for the "short sentence merges
     with 400 unrelated characters" bug from the previous version.
"""

import re

SECTION_PATTERN = re.compile(r"(?:Section|Article|Clause|§\s*\d+\.?\d*)[.\s]+\S+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
MAX_MERGE_CHARS = 350   # a short sentence can join a buffer, but never past this
MIN_SEGMENT_CHARS = 15


def segment_text(text: str) -> list[tuple[str, str]]:
    """Returns list of (section_ref, segment_text)."""
    sections = list(SECTION_PATTERN.finditer(text))
    if sections:
        out = []
        for i, m in enumerate(sections):
            start = m.start()
            end = sections[i + 1].start() if i + 1 < len(sections) else len(text)
            seg = text[start:end].strip().rstrip(".")
            if len(seg) >= MIN_SEGMENT_CHARS:
                out.append((f"Section {i + 1}", seg))
        return out

    out = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for p_idx, para in enumerate(paragraphs):
        sentences = SENTENCE_SPLIT.split(para)
        buffer = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            would_merge = len(s) < 30 and buffer and len(buffer) + len(s) < MAX_MERGE_CHARS
            if would_merge:
                buffer += " " + s
            else:
                if buffer:
                    out.append((f"Paragraph {p_idx + 1}", buffer.strip()))
                buffer = s
        if buffer:
            out.append((f"Paragraph {p_idx + 1}", buffer.strip()))

    return out if out else [("Document", text)]


def clip(text: str, limit: int = 300) -> str:
    """Word-boundary-safe truncation — never cuts a word in half."""
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(",.;: ") + "…"
