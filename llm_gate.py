"""Stage 2: LLM verification gate.

Every Candidate must pass through here before becoming a Finding.
If the LLM call fails, we do NOT silently downgrade to a fake "Finding" —
we return None (dropped) and let the caller decide whether to show an
"unverified — LLM unavailable" note instead. This is the fix for the bug
where a failed verification call used to quietly become a mislabeled
'Verified' result in the old version of this tool.
"""

import json
import re

from models import Candidate, Finding
from categories import RISK_CATEGORIES, SEVERITY_MAP
from ollama_client import query_model

VERIFY_SYSTEM_PROMPT = (
    "You are a precise contract-clause verifier. You will be shown a short "
    "excerpt of contract text and a yes/no question about it. Base your answer "
    "ONLY on the text provided — do not use outside knowledge about the company "
    "or assume anything not stated. If the text is ambiguous or only tangentially "
    "related to the question, answer NO. Respond with strict JSON only, no other text."
)


def _build_prompt(clause_text: str, question: str) -> str:
    return f"""TEXT:
\"\"\"{clause_text}\"\"\"

QUESTION:
{question}

Respond with ONLY this JSON, no markdown, no extra text:
{{"answer": "YES" or "NO", "reason": "one sentence, grounded only in the TEXT above"}}"""


def _parse_response(raw: str) -> dict | None:
    # Models sometimes wrap JSON in prose or code fences — extract the first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if "answer" in data:
            return data
    except json.JSONDecodeError:
        return None
    return None


def verify(candidate: Candidate, model_name: str) -> Finding | None:
    """Returns a Finding if verified YES, None if verified NO or the call failed."""
    finding, _status = verify_with_status(candidate, model_name)
    return finding


def verify_with_status(candidate: Candidate, model_name: str) -> tuple[Finding | None, str]:
    """Same as verify(), but also returns a status string so callers (e.g. the
    debug view) can tell a genuine 'the LLM said no' apart from 'the call
    itself failed or returned unparseable output' — these look identical from
    verify()'s return value alone, which made earlier debugging ambiguous."""
    cat = RISK_CATEGORIES[candidate.category_key]
    prompt = _build_prompt(candidate.evidence.text, cat["verification_question"])

    raw = query_model(prompt, model=model_name, system_prompt=VERIFY_SYSTEM_PROMPT, timeout=60)
    if raw.startswith("ERROR"):
        return None, f"LLM_CALL_FAILED: {raw}"

    parsed = _parse_response(raw)
    if parsed is None:
        return None, f"UNPARSEABLE_RESPONSE: {raw[:150]}"

    answer = str(parsed.get("answer", "")).strip().upper()
    reason = str(parsed.get("reason", "")).strip()

    if answer != "YES":
        return None, f"REJECTED_BY_LLM: {reason}"

    severity = SEVERITY_MAP.get(cat["severity"], "low")
    confidence_pct = min(100, int(candidate.retrieval_confidence * 100))

    finding = Finding(
        category_key=candidate.category_key,
        severity=severity,
        confidence_pct=confidence_pct,
        verified=True,
        reason=reason or "Confirmed by model, no reason text returned.",
        evidence=candidate.evidence,
        interpretation=cat["interpretation"],
        impact_statement=cat["impact_statement"],
        suggested_action=cat["suggested_action"],
    )
    return finding, "VERIFIED"


def heuristic_only(candidate: Candidate) -> Finding:
    """Used when verification is off. Confidence is deliberately capped low,
    and verified=False so the UI can never claim this was LLM-checked."""
    cat = RISK_CATEGORIES[candidate.category_key]
    severity = SEVERITY_MAP.get(cat["severity"], "low")
    confidence_pct = int(20 + candidate.retrieval_confidence * 25)  # caps at ~45%

    return Finding(
        category_key=candidate.category_key,
        severity=severity,
        confidence_pct=confidence_pct,
        verified=False,
        reason="Keyword match only — not checked by a language model.",
        evidence=candidate.evidence,
        interpretation=cat["interpretation"],
        impact_statement=cat["impact_statement"],
        suggested_action=cat["suggested_action"],
    )
