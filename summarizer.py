"""Turns structured Findings into a plain-English paragraph.

Deliberately avoids: risk verdicts ("you should proceed"), legal
conclusions, or any advice not already present in a Finding's
suggested_action. The LLM is only asked to rephrase, not to reason
about what the user should do.
"""

import json

from models import Finding
from categories import RISK_CATEGORIES
from ollama_client import query_model

SUMMARY_SYSTEM_PROMPT = (
    "You explain contract clauses in plain English for a general audience. "
    "You are NOT a lawyer and must not give legal advice or tell the user "
    "whether to sign, proceed, or worry. You may only describe what was "
    "found and restate the provided suggested actions in clearer language. "
    "Do not add any suggestion that is not explicitly provided to you. "
    "Do not mention any category that is not in the DETECTED list."
)


def summarize(findings: list[Finding], model_name: str | None) -> str:
    if not model_name:
        return _fallback_summary(findings)

    detected = [
        {
            "category": RISK_CATEGORIES[f.category_key]["label"],
            "severity": f.severity,
            "verified": f.verified,
            "what_it_means": f.impact_statement,
            "suggested_action": f.suggested_action,
        }
        for f in findings
    ]

    prompt = f"""DETECTED CLAUSES:
{json.dumps(detected, indent=2)}

Write 3-5 sentences in plain English:
1. List what was found, in plain language, one sentence per clause maximum.
2. Restate the suggested actions already provided above — do not invent new ones.
3. End with: "This is an automated summary, not legal advice."

Do not add a recommendation about whether to sign or proceed."""

    response = query_model(prompt, model=model_name, system_prompt=SUMMARY_SYSTEM_PROMPT, timeout=120)
    if response.startswith("ERROR"):
        return _fallback_summary(findings)
    return response


def _fallback_summary(findings: list[Finding]) -> str:
    if not findings:
        return "No flagged clauses in the categories this tool checks. This is an automated summary, not legal advice."
    lines = [f"- {RISK_CATEGORIES[f.category_key]['label']}: {f.impact_statement}" for f in findings]
    return "Flagged clauses:\n" + "\n".join(lines) + "\n\nThis is an automated summary, not legal advice."
