"""PDF report generation for contract analysis via WeasyPrint."""

from datetime import datetime

from weasyprint import HTML

from categories import RISK_CATEGORIES, SEVERITY_LABELS


def _severity_badge(severity: str) -> str:
    colors = {"critical": "#dc3545", "high": "#fd7e14", "medium": "#ffc107", "low": "#28a745"}
    bg = colors.get(severity, "#6c757d")
    return f'<span style="background:{bg};color:#fff;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600">{severity.upper()}</span>'


def _score_box(score: dict) -> str:
    return (
        f'<div style="background:{score["color"]}22;border-left:5px solid {score["color"]};'
        f'padding:14px;border-radius:8px;margin:12px 0">'
        f'<h3 style="margin:0;color:{score["color"]};font-size:18px">{score["level"]}</h3>'
        f'<p style="margin:4px 0 0;font-size:14px">Score: {score["score"]}/100</p></div>'
    )


def _findings_table(findings: list, show_debug: bool, debug_trail: list[dict] | None) -> str:
    rows = []
    for i, f in enumerate(findings, 1):
        cat = RISK_CATEGORIES[f.category_key]
        sev_label, _ = SEVERITY_LABELS.get(f.severity, ("Unknown", "#6c757d"))
        verify_badge = "✅ LLM-verified" if f.verified else "🔸 Heuristic only (not LLM-checked)"
        rows.append(f"""
        <tr>
            <td style="padding:12px;vertical-align:top;border-bottom:2px solid #eee">
                <strong style="font-size:16px">{cat['icon']} {cat['label']}</strong>
            </td>
            <td style="padding:12px;vertical-align:top;border-bottom:2px solid #eee">
                {_severity_badge(f.severity)}<br>
                <span style="font-size:12px;color:#666">{verify_badge}</span><br>
                <span style="font-size:12px;color:#666">Confidence: {f.confidence_pct}%</span>
            </td>
            <td style="padding:12px;vertical-align:top;border-bottom:2px solid #eee;font-size:13px">
                <p><strong>Excerpt:</strong><br><em>"{f.evidence.text}"</em></p>
                <p><strong>Reason:</strong> {f.reason}</p>
                <p><strong>Impact:</strong> {f.impact_statement}</p>
                <p><strong>Suggested Action:</strong> {f.suggested_action}</p>
            </td>
        </tr>""")

    rows_html = "\n".join(rows)

    html = f"""
    <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif">
        <thead>
            <tr style="background:#f8f9fa;text-align:left">
                <th style="padding:10px;font-size:14px">Clause</th>
                <th style="padding:10px;font-size:14px">Severity</th>
                <th style="padding:10px;font-size:14px">Details</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>"""
    return html


def _cleared_section(cleared: list[str]) -> str:
    if not cleared:
        return ""
    items = "".join(f'<li style="margin:4px 0;font-size:13px">✅ {RISK_CATEGORIES[k]["icon"]} {RISK_CATEGORIES[k]["label"]}</li>' for k in cleared)
    return f"""
    <h3 style="margin-top:24px;color:#333">Categories Checked and Not Found ({len(cleared)})</h3>
    <ul style="columns:3;list-style:none;padding:0">{items}</ul>"""


def generate_report(
    findings: list,
    cleared: list[str],
    score: dict,
    verify_on: bool,
    summary: str,
    debug_trail: list[dict] | None = None,
    show_debug: bool = False,
) -> bytes:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    verification_status = "LLM verification was ON" if verify_on else "LLM verification was OFF (heuristic only)"
    debug_section = ""
    if show_debug and debug_trail:
        debug_rows = ""
        for row in debug_trail:
            cat_label = RISK_CATEGORIES[row["category"]]["label"]
            debug_rows += f"""
            <tr>
                <td style="padding:8px;border-bottom:1px solid #ddd;font-size:12px">{cat_label}</td>
                <td style="padding:8px;border-bottom:1px solid #ddd;font-size:12px">{row['source']}</td>
                <td style="padding:8px;border-bottom:1px solid #ddd;font-size:12px">{row['retrieval_confidence']}</td>
                <td style="padding:8px;border-bottom:1px solid #ddd;font-size:12px">{row['outcome']}</td>
            </tr>"""
        debug_section = f"""
        <h3 style="margin-top:24px;color:#333">Retrieval Debug Trail</h3>
        <table style="width:100%;border-collapse:collapse;font-family:Arial,sans-serif;margin-top:8px">
            <thead><tr style="background:#f8f9fa;text-align:left">
                <th style="padding:8px;font-size:12px">Category</th>
                <th style="padding:8px;font-size:12px">Source</th>
                <th style="padding:8px;font-size:12px">Confidence</th>
                <th style="padding:8px;font-size:12px">Outcome</th>
            </tr></thead>
            <tbody>{debug_rows}</tbody>
        </table>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ margin: 2cm; }}
    body {{ font-family: Arial, Helvetica, sans-serif; color: #333; font-size: 14px; line-height: 1.5; }}
    h1 {{ color: #1a1a2e; font-size: 24px; margin-bottom: 4px; }}
    .subtitle {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
    .summary-text {{ background: #f8f9fa; padding: 14px; border-radius: 8px; font-size: 14px; }}
    .footer {{ margin-top: 30px; font-size: 11px; color: #999; text-align: center; border-top: 1px solid #ddd; padding-top: 12px; }}
</style>
</head>
<body>
    <h1>📋 Contract Clause Analysis Report</h1>
    <p class="subtitle">Generated: {timestamp} &nbsp;|&nbsp; {verification_status}</p>
    {_score_box(score)}
    <hr>
    <h2 style="color:#333">Plain-English Summary</h2>
    <div class="summary-text">{summary}</div>
    <hr>
    <h2 style="color:#333">Flagged Clauses ({len(findings)})</h2>
    {_findings_table(findings, show_debug, debug_trail)}
    {_cleared_section(cleared)}
    {debug_section}
    <hr>
    <div class="footer">
        <p><strong>This tool is not a lawyer and does not give legal advice.</strong></p>
        <p>Runs entirely locally via Ollama — text never leaves your machine.</p>
        <p>Contract Clause Reviewer &bull; {timestamp}</p>
    </div>
</body>
</html>"""

    return HTML(string=html).write_pdf()
