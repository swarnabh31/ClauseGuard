"""Top-level pipeline: text -> Findings -> score. No Streamlit imports here,
so this module is independently testable (see test_pipeline.py)."""

from models import Finding
from categories import RISK_CATEGORIES, SEVERITY_ORDER
from retrieval import find_candidates
from llm_gate import verify, verify_with_status, heuristic_only


def analyze(
    text: str,
    model_name: str | None = None,
    use_verification: bool = True,
    embed_model: str | None = "nomic-embed-text",
) -> list[Finding]:
    candidate_groups = find_candidates(text, embed_model=embed_model)
    findings: list[Finding] = []

    for candidates in candidate_groups.values():
        if use_verification and model_name:
            for c in candidates:
                f = verify(c, model_name)
                if f is not None:
                    findings.append(f)
                    break
        else:
            findings.append(heuristic_only(candidates[0]))

    findings.sort(key=lambda f: (
        SEVERITY_ORDER.get(f.severity, 99),
        -RISK_CATEGORIES[f.category_key]["weight"],
        -f.confidence_pct,
    ))
    return findings


def analyze_with_debug(
    text: str,
    model_name: str | None = None,
    use_verification: bool = True,
    embed_model: str | None = "nomic-embed-text",
) -> tuple[list[Finding], list[dict]]:
    """Same as analyze(), but also returns a debug trail for every candidate:
    which retrieval path found it, its confidence, and what happened to it
    at the verification gate (VERIFIED / REJECTED_BY_LLM / LLM_CALL_FAILED /
    ACCEPTED_HEURISTIC). Use this to diagnose "why wasn't X flagged" instead
    of guessing at threshold values blind.

    With the top-3-per-category change, multiple candidates may appear per
    category — the earlier ones typically show REJECTED_BY_LLM (the wrong
    segment that scored higher) and the last one shows VERIFIED (the correct
    clause that was being crowded out)."""
    candidate_groups = find_candidates(text, embed_model=embed_model)
    findings: list[Finding] = []
    debug_trail: list[dict] = []

    for candidates in candidate_groups.values():
        found: Finding | None = None
        for c in candidates:
            source = "semantic" if c.keyword_hits == ["<semantic match, no literal keyword>"] else "keyword"
            row = {
                "category": c.category_key,
                "source": source,
                "retrieval_confidence": round(c.retrieval_confidence, 3),
                "evidence_preview": c.evidence.text[:100],
            }

            if use_verification and model_name:
                f, status = verify_with_status(c, model_name)
                if f is not None and found is None:
                    found = f
                row["outcome"] = status
                debug_trail.append(row)
                if f is not None:
                    break
            else:
                if found is None:
                    found = heuristic_only(c)
                row["outcome"] = "ACCEPTED_HEURISTIC"
                debug_trail.append(row)
                break

        if found is not None:
            findings.append(found)

    findings.sort(key=lambda f: (
        SEVERITY_ORDER.get(f.severity, 99),
        -RISK_CATEGORIES[f.category_key]["weight"],
        -f.confidence_pct,
    ))
    return findings, debug_trail


def cleared_categories(findings: list[Finding]) -> list[str]:
    detected = {f.category_key for f in findings}
    remaining = [k for k in RISK_CATEGORIES if k not in detected]
    return sorted(remaining, key=lambda k: RISK_CATEGORIES[k]["weight"], reverse=True)


def risk_score(findings: list[Finding]) -> dict:
    if not findings:
        return {"score": 0, "level": "No flagged clauses", "color": "#28a745"}

    # Only count findings we're reasonably sure about — unverified findings
    # contribute at half weight so heuristic-only mode can't inflate the score.
    total = sum(
        RISK_CATEGORIES[f.category_key]["weight"] * (1.0 if f.verified else 0.5)
        for f in findings
    )
    score = min(100, round(total))

    if score <= 20:
        level, color = "Low concern", "#28a745"
    elif score <= 45:
        level, color = "Moderate concern", "#ffc107"
    elif score <= 70:
        level, color = "High concern", "#fd7e14"
    else:
        level, color = "Very high concern", "#dc3545"

    return {"score": score, "level": level, "color": color}
