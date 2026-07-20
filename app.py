"""Contract Clause Reviewer — local-first, honest-by-design.

Run with: streamlit run app.py
Requires Ollama running locally (ollama serve) with at least one model pulled.
"""

import streamlit as st

from categories import RISK_CATEGORIES, SEVERITY_LABELS
from ollama_client import list_models
from pipeline import analyze, analyze_with_debug, cleared_categories, risk_score
from summarizer import summarize
from pdf_report import generate_report

st.set_page_config(page_title="Contract Clause Reviewer", page_icon="📋", layout="wide")

# ── Sidebar ──────────────────────────────────────────────
st.sidebar.title("⚙️ Settings")
models = list_models()

if not models:
    st.sidebar.error("No Ollama models found. Run `ollama pull <model>` and `ollama serve` first.")
    selected_model = None
else:
    selected_model = st.sidebar.selectbox("Model", options=models, key="selected_model")

use_verification = st.sidebar.checkbox(
    "Enable LLM verification (recommended)",
    value=True,
    key="use_verification",
    help="Each keyword match is re-checked by the local model before being shown. "
         "Turning this off shows raw keyword matches only, clearly labeled as such.",
)

use_semantic = st.sidebar.checkbox(
    "Enable semantic retrieval (nomic-embed-text)",
    value=True,
    key="use_semantic",
    help="Catches paraphrased clauses that don't literally contain the keyword list "
         "(e.g. a liability cap worded differently than the built-in phrasing). "
         "Requires `ollama pull nomic-embed-text`. Silently skipped if unavailable.",
)

show_debug = st.sidebar.checkbox(
    "Show retrieval debug trail",
    value=False,
    key="show_debug",
    help="Shows every candidate clause the retrieval stage found, which path found it "
         "(keyword/semantic), and exactly why it was accepted or dropped. Use this to "
         "diagnose 'why wasn't X flagged' instead of guessing.",
)

if st.sidebar.button("Clear"):
    st.session_state.clear()
    st.rerun()

# ── Header + persistent disclaimer ──────────────────────
st.title("📋 Contract Clause Reviewer")
st.warning(
    "**This tool is not a lawyer and does not give legal advice.** "
    "It flags clauses in a fixed set of categories using keyword matching "
    "plus a local language model check. It can miss real issues and can "
    "misidentify clauses. For anything important, have the document "
    "reviewed by a qualified professional.",
    icon="⚠️",
)

st.caption(
    "Runs entirely locally via Ollama — the text you paste never leaves this machine."
)
st.divider()

# ── Input ────────────────────────────────────────────────
text = st.text_area("Paste contract or Terms of Service text:", height=280)
word_count = len(text.split()) if text.strip() else 0
st.caption(f"{word_count:,} words")

run = st.button("Analyze", type="primary", disabled=not text.strip())

# ── Run pipeline ─────────────────────────────────────────
if run:
    verify_on = use_verification and selected_model is not None
    embed_model = "nomic-embed-text" if use_semantic else None
    spinner_msg = "Scanning clauses..."
    spinner_msg += " (LLM verification on)" if verify_on else " (heuristic only)"
    spinner_msg += " + semantic retrieval" if embed_model else ""
    with st.spinner(spinner_msg):
        if show_debug:
            findings, debug_trail = analyze_with_debug(
                text, model_name=selected_model, use_verification=verify_on, embed_model=embed_model
            )
            st.session_state["debug_trail"] = debug_trail
        else:
            findings = analyze(text, model_name=selected_model, use_verification=verify_on, embed_model=embed_model)
            st.session_state["debug_trail"] = None
    st.session_state["findings"] = findings
    st.session_state["cleared"] = cleared_categories(findings)
    st.session_state["verify_on"] = verify_on

# ── Results ──────────────────────────────────────────────
if "findings" in st.session_state:
    findings = st.session_state["findings"]
    cleared = st.session_state["cleared"]
    verify_on = st.session_state["verify_on"]

    if not verify_on:
        st.info(
            "LLM verification was OFF for this run — every result below is a raw "
            "keyword match, not confirmed by the model. Confidence is capped low "
            "on purpose to reflect that.",
            icon="ℹ️",
        )

    score = risk_score(findings)
    st.header("Summary")
    st.markdown(
        f'<div style="background:{score["color"]}22;border-left:5px solid {score["color"]};'
        f'padding:14px;border-radius:8px;">'
        f'<h3 style="margin:0;color:{score["color"]}">{score["level"]}</h3>'
        f'<p style="margin:4px 0 0">{len(findings)} clause(s) flagged out of '
        f'{len(RISK_CATEGORIES)} categories checked. Score is a rough weighting, '
        f'not a certified rating.</p></div>',
        unsafe_allow_html=True,
    )
    st.divider()

    if not findings:
        st.success("No clauses matched the categories this tool checks.")
    else:
        st.header("Flagged Clauses")
        for i, f in enumerate(findings, 1):
            cat = RISK_CATEGORIES[f.category_key]
            sev_label, sev_color = SEVERITY_LABELS[f.severity]
            verify_badge = "✅ LLM-verified" if f.verified else "🔸 Heuristic only (not LLM-checked)"

            with st.expander(f"{cat['icon']} {i}. {cat['label']} — {sev_label}", expanded=(f.severity in ("critical", "high"))):
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.markdown(f"**{verify_badge}**")
                with c2:
                    st.markdown(f"**Confidence: {f.confidence_pct}%**")

                st.markdown("**Quoted excerpt:**")
                st.info(f.evidence.text + (f"  \n*— {f.evidence.section_ref}*" if f.evidence.section_ref else ""))

                st.markdown("**Why this was flagged:**")
                st.write(f.reason)

                st.markdown("**What it means:**")
                st.warning(f.impact_statement)

                st.markdown("**Suggested action:**")
                st.success(f.suggested_action)

        st.divider()

    with st.expander(f"✅ Categories checked and not found ({len(cleared)})"):
        cols = st.columns(3)
        for idx, key in enumerate(cleared):
            with cols[idx % 3]:
                st.write(f"✅ {RISK_CATEGORIES[key]['icon']} {RISK_CATEGORIES[key]['label']}")

    debug_trail = st.session_state.get("debug_trail")
    if debug_trail:
        with st.expander(f"🔧 Retrieval debug trail ({len(debug_trail)} candidates found before verification)"):
            st.caption(
                "Every candidate the retrieval stage produced, before the LLM gate. "
                "REJECTED_BY_LLM = model genuinely said no. LLM_CALL_FAILED / "
                "UNPARSEABLE_RESPONSE = the check itself didn't run cleanly — "
                "not a real rejection, worth re-running."
            )
            for row in debug_trail:
                cat_label = RISK_CATEGORIES[row["category"]]["label"]
                st.markdown(
                    f"**{cat_label}** — source: `{row['source']}`, "
                    f"retrieval confidence: `{row['retrieval_confidence']}`, "
                    f"outcome: `{row['outcome']}`"
                )
                st.caption(f"Evidence preview: {row['evidence_preview']}...")
                st.divider()

    st.divider()
    st.header("Plain-English Summary")
    with st.spinner("Summarizing..."):
        summary = summarize(findings, selected_model if verify_on else None)
    st.write(summary)

    st.divider()
    import json
    export = {
        "risk_score": score,
        "verification_enabled": verify_on,
        "findings": [
            {
                "category": RISK_CATEGORIES[f.category_key]["label"],
                "severity": f.severity,
                "confidence_pct": f.confidence_pct,
                "verified": f.verified,
                "reason": f.reason,
                "evidence": f.evidence.text,
                "impact": f.impact_statement,
                "suggested_action": f.suggested_action,
            }
            for f in findings
        ],
        "cleared_categories": [RISK_CATEGORIES[k]["label"] for k in cleared],
    }
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download analysis (JSON)",
            data=json.dumps(export, indent=2),
            file_name="contract_analysis.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        pdf_bytes = generate_report(
            findings, cleared, score, verify_on, summary,
            debug_trail=st.session_state.get("debug_trail"),
            show_debug=bool(st.session_state.get("debug_trail")),
        )
        st.download_button(
            "Download analysis (PDF)",
            data=pdf_bytes,
            file_name="contract_analysis.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
