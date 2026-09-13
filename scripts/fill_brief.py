"""Generate BRIEF.md from docs/BRIEF.template.md and a run's summary.json.
Numbers in the brief are never typed by hand (SKILL.md Rule 7).  Usage: fill_brief.py runs/<ts>"""
import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
s = json.loads((run / "summary.json").read_text())


def _cost_book(run: Path, s: dict) -> str:
    """Readings + desk queries, from the trace: the two buckets the run report shows, never one number hiding the other."""
    tri = [json.loads(l) for l in (run / "trace.jsonl").read_text().splitlines()]
    tri = [l for l in tri if l["step"].startswith("triage:") and l["doc_id"] != "REF"]
    ext = s["cost_total_usd"]
    if not tri:
        return f"${ext:.2f}"
    tc = sum(l["cost_usd"] for l in tri)
    return f"${ext:.2f} for the readings + ${tc:.2f} for the {len(tri)} desk queries drafted = ${ext + tc:.2f}"

def run_label(s: dict) -> str:
    """Run id, plus the resume note when the run is a composite (ADR-31): the reader must see it."""
    rs = s.get("resumed")
    if not rs:
        return s["run_id"]
    prior = rs["prior_run"].rstrip("/").split("/")[-1]
    return (f"{s['run_id']}, resumed from {prior}: {len(rs['reused'])} documents re-checked from their hash-attested "
            f"extractions, {len(rs['re_extracted'])} ({', '.join(rs['re_extracted'])}) extracted again")



def r(k: str) -> str:
    return f"{s[k]['hit']}/{s[k]['n']}"


def _parse_tax(run: Path) -> str:
    """Summarise parse_tax.md if the ablation was run for this run; otherwise say so."""
    p = run / "parse_tax.md"
    if not p.exists():
        return "not measured for this run (run the ablation)"
    import re
    txt = p.read_text()
    deg = re.search(r"Fields degraded by parsing \((\d+)\)", txt)
    rows = re.findall(r"\| extraction_accuracy \((\w+)\) \| (\d+/\d+) \| (\d+/\d+) \| ([+-]\d+) \|", txt)
    parts = [f"{fam} {a}→{b} ({d})" for fam, a, b, d in rows]
    ws = re.search(r"\*\*Wholesale events, not parse tax:\*\* (.*)", txt)
    note = f"; {deg.group(1)} field(s) degraded by parsing" if deg else ""
    if ws:
        note += " (the remaining delta is an extractor deadline/API event in one run, not parsing)"
    return (", ".join(parts) if parts else "see parse_tax.md") + note


ac_ok = s["auto_clear_correctness"]["hit"] == s["auto_clear_correctness"]["n"]
manifest = json.loads(Path("golden/manifest.json").read_text())
_docs = [d for d in manifest["documents"]]
_planted = sum(len(d["planted"]) for d in _docs)
_traps = sum(len(d.get("traps", [])) for d in _docs)
_clean = sum(1 for d in _docs if d.get("clean_control"))
vals = {
    "n_planted": str(_planted), "n_traps": str(_traps), "n_clean": str(_clean),
    "cost_ref": f"${s.get('reference_cost_usd', 0):.2f}",
    "cost_traced": (f"${s.get('cost_traced_total_usd', 0):.2f} traced in this run, the reused extractions in the prior run's trace"
                    if s.get("resumed") else f"${s.get('cost_traced_total_usd', 0):.2f} traced in total"),
    "catch_strict": r("catch_strict"),
    "false_flags": r("false_flag_fields"),
    "clean_docs": f"{s['false_flag_docs']['n'] - s['false_flag_docs']['hit']}/{s['false_flag_docs']['n']}",
    "auto_clear": r("auto_clear_correctness") + (" (100%)" if ac_ok else " — NOT 100%: tiered-autonomy claim does not hold"),
    "agreement": r("agreement"),
    "trap": r("trap_resolved"),
    "cost": f"${s['cost_per_doc_usd']:.3f}",
    "cost_book": _cost_book(run, s),
    "n_docs": str(s["n_docs"]),
    "parse_tax": _parse_tax(run),
    "run_id": run_label(s),
}
tpl = Path("docs/BRIEF.template.md").read_text()
out = tpl.format(**vals)
Path("BRIEF.md").write_text(out)
print("BRIEF.md written from run", s["run_id"], vals)
