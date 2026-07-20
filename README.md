# Contract Clause Reviewer

A local-first tool that flags common risky clauses in contracts / Terms of
Service, using keyword retrieval + local LLM verification via Ollama.

## Why this exists / what it isn't
This is a clause-spotting aid, not a legal opinion. It's built around one
rule: **nothing gets shown to the user without also showing why**, and the
UI never claims a stronger guarantee than the pipeline actually provides.

## Setup
```bash
pip install -r requirements.txt   # streamlit, requests
ollama serve                      # in a separate terminal
ollama pull qwen3.6                # or any instruction-tuned model you have
ollama pull nomic-embed-text       # for semantic retrieval (optional but recommended)
streamlit run app.py
```

## Architecture
```
text
  → segmenter.py       sentence/section splitting, bounded merging
  → retrieval.py         keyword candidates AND semantic (embedding) candidates,
                            exclude_keywords suppress false positives on both paths
  → llm_gate.py            LLM YES/NO + reason, per-finding (not per-run)
  → pipeline.py              orchestration + score
  → summarizer.py           plain-English recap, grounded in Finding objects only
  → app.py                     Streamlit UI
```

### Why two retrieval paths
Keyword matching alone has a recall ceiling — real contracts paraphrase.
Tested against Google's live Terms of Service, keyword-only retrieval
missed a real liability cap ("Google's total liability... is limited to
the greater of $500...") because it shares no literal phrase with the
`liability_limitation` category's keyword list. `retrieval.py` now runs
a second pass: each segment is embedded with `nomic-embed-text` and
compared against a reference embedding of each category's description
(`_category_reference_embedding`), catching paraphrases that keyword
matching alone misses. If the embedding model isn't installed, this path
fails silently and keyword matching still runs — see
`test_semantic_retrieval_fails_silently_without_embedding_model`.

`SEMANTIC_THRESHOLD = 0.55` in `retrieval.py` is a starting point, not a
calibrated value — tune it against a labeled eval set of real documents
before trusting it in production.

## Design decisions worth knowing about
- **`Finding.verified` is mandatory, not a global toggle.** A single run can
  mix LLM-verified and heuristic-only results if verification fails on some
  candidates; the UI reflects that per-finding, never as one blanket label.
- **Failed LLM calls drop the candidate, they don't downgrade it into a
  fake result.** A network hiccup should never look like a checked-and-passed
  finding.
- **`exclude_keywords` per category** — cheap guardrail against a clause
  matching on adjacent vocabulary. Covered by `test_pipeline.py`.
- **Risk score halves the weight of unverified findings** so heuristic-only
  mode can't produce an artificially high/confident-looking score.
- **The summarizer is explicitly told not to give a verdict** ("should you
  proceed") — it may only restate detected clauses and their pre-approved
  suggested actions.

## What this tool deliberately does NOT do
- Give a "safe to sign" / "don't sign" recommendation
- Cover every possible risky clause (fixed category list — see `categories.py`)
- Replace review by a qualified professional for anything with real stakes

## Extending it
Add a new category in `categories.py` with `keywords`, a tight
`verification_question`, and — if it's prone to overlap with another
category — an `exclude_keywords` list. Add a regression test in
`test_pipeline.py` for any false positive you find in real documents.
