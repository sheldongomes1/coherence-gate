"""Parse-tax ablation (CS2): the same eval run twice, --source txt and --source pdf, same
models and prompts. Renders parse_tax.md into the pdf run and appends it to its eval_report."""
from __future__ import annotations

import json
from pathlib import Path


def _load(run: Path) -> dict:
    return json.loads((run / "summary.json").read_text())


def render_parse_tax(txt_run: Path, pdf_run: Path) -> Path:
    t, p = _load(txt_run), _load(pdf_run)
    assert t.get("source", "txt") == "txt" and p.get("source") == "pdf", "expected a txt run and a pdf run"
    lines = ["## Parse tax (ablation: canonical text vs parsed PDF)", "",
             f"Runs: txt = {t['run_id']}, pdf = {p['run_id']}. Same models, prompts, golden set; only the source text differs.", "",
             "| metric | txt | pdf | delta |", "|---|---|---|---|"]

    def row(label, key):
        a, b = t[key], p[key]
        lines.append(f"| {label} | {a['hit']}/{a['n']} | {b['hit']}/{b['n']} | {b['hit'] - a['hit']:+d} |")

    row("catch_rate (strict)", "catch_strict")
    row("catch_rate_field_only", "catch_field_only")
    row("false_flag_fields (lower is better)", "false_flag_fields")
    row("clean docs NOT auto-cleared (lower is better)", "false_flag_docs")
    row("cross-family agreement", "agreement")
    for fam in ("gemini", "claude"):
        a, b = t["extraction_accuracy"][fam], p["extraction_accuracy"][fam]
        lines.append(f"| extraction_accuracy ({fam}) | {a['hit']}/{a['n']} | {b['hit']}/{b['n']} | {b['hit'] - a['hit']:+d} |")
    lines.append(f"| cost per document (USD, models only) | ${t['cost_per_doc_usd']:.4f} | ${p['cost_per_doc_usd']:.4f} | {p['cost_per_doc_usd'] - t['cost_per_doc_usd']:+.4f} |")
    lines.append("")
    degraded, improved = [], []
    for fam in ("gemini", "claude"):
        ta, pa = t.get("field_accuracy", {}).get(fam, {}), p.get("field_accuracy", {}).get(fam, {})
        for k in sorted(set(ta) | set(pa)):
            if ta.get(k) and not pa.get(k):
                degraded.append(f"{fam} {k}")
            elif pa.get(k) and not ta.get(k):
                improved.append(f"{fam} {k}")
    lines += [f"**Fields degraded by parsing ({len(degraded)}):** " + (", ".join(degraded) if degraded else "none"),
              f"**Fields improved by parsing ({len(improved)}):** " + (", ".join(improved) if improved else "none"), ""]
    n_deg, n_imp = len(degraded), len(improved)
    lines += ["**Interpretation.** " + (
        "The parsed PDF reproduced the canonical text closely enough that extraction accuracy did not move; on this "
        "synthetic set (clean, machine-rendered PDFs) the parse tax is nil. Real desk paper (scans, multi-column, "
        "annexes) would be where a tax appears, and this ablation is the instrument that would show it."
        if n_deg == 0 and n_imp == 0 else
        f"Parsing changed {n_deg + n_imp} field readings ({n_deg} degraded, {n_imp} improved) out of "
        f"{t['extraction_accuracy']['gemini']['n'] * 2}. The listed fields are the parse tax on this set; the deltas above "
        "show whether it reached the catch or false-flag rates."),
        "Parsing cost is not reported by the vendor API and is therefore not in the cost line; parse latency is in each trace.", ""]
    out = pdf_run / "parse_tax.md"
    out.write_text("\n".join(lines))
    rep = pdf_run / "eval_report.md"
    if rep.exists() and "## Parse tax" not in rep.read_text():
        rep.write_text(rep.read_text().rstrip() + "\n\n" + "\n".join(lines))
    return out
