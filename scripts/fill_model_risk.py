"""Fill the bracketed values in docs/MODEL-RISK.md from a run's summary (never by hand).
Usage: fill_model_risk.py runs/<ts> [release_tag] > MODEL-RISK.md"""
import json
import re
import sys
from datetime import date
from pathlib import Path

run = Path(sys.argv[1]); tag = sys.argv[2] if len(sys.argv) > 2 else "v0.2.0"
s = json.loads((run / "summary.json").read_text())
manifest = json.loads(Path("golden/manifest.json").read_text())
docs = manifest["documents"]
n_planted = sum(len(d["planted"]) for d in docs)
types = sorted({p["type"] for d in docs for p in d["planted"]})
clean = sum(1 for d in docs if d.get("clean_control"))
pt = run / "parse_tax.md"
parse_tax = "not measured for this run"
if pt.exists():
    m = re.search(r"\| extraction_accuracy \(gemini\) \| (\S+) \| (\S+) \| (\S+) \|.*?\| extraction_accuracy \(claude\) \| (\S+) \| (\S+) \| (\S+) \|", pt.read_text(), re.S)
    deg = re.search(r"Fields degraded by parsing \((\d+)\)", pt.read_text())
    if m:
        parse_tax = f"gemini {m.group(1)}→{m.group(2)} ({m.group(3)}), claude {m.group(4)}→{m.group(5)} ({m.group(6)}); {deg.group(1) if deg else '?'} field(s) degraded, listed in eval_report.md"
r = lambda k: f"{s[k]['hit']}/{s[k]['n']}"  # noqa: E731
tpl = Path("docs/MODEL-RISK.md").read_text()
rep = {
    "[vX.Y]": tag, "[id]": s["run_id"], "date [ ]": f"date {date.today().isoformat()}",
    "[N] documents ([n_pdf] PDF / [n_txt] text)": f"{s['n_docs']} documents ({s['n_docs'] if s.get('source') == 'pdf' else 0} parsed PDF / {s['n_docs'] if s.get('source') != 'pdf' else 0} text; every document exists in both forms)",
    "[M] planted": f"{n_planted} planted", "[k] finding types": f"{len(types)} finding types ({', '.join(types)})",
    "[c] clean controls": f"{clean} clean controls",
    "[x/M]": r("catch_strict"), "[y/M]": r("catch_field_only"), "[f/F]": r("false_flag_fields"),
    "[must be 100%]": r("auto_clear_correctness") + (" (100%)" if s["auto_clear_correctness"]["hit"] == s["auto_clear_correctness"]["n"] else " — NOT 100%"),
    "[ %]": f"{s['agreement']['hit']}/{s['agreement']['n']}",
    "[summary; fields degraded listed\n  in eval report]": parse_tax, "[summary; fields degraded listed in eval report]": parse_tax,
    "[4] layout families": "4 layout families",
}
out = tpl
for k, v in rep.items():
    out = out.replace(k, v)
print(out)
