"""Generate BRIEF.md from docs/BRIEF.template.md and a run's summary.json.
Numbers in the brief are never typed by hand (SKILL.md Rule 7).  Usage: fill_brief.py runs/<ts>"""
import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
s = json.loads((run / "summary.json").read_text())


def r(k: str) -> str:
    return f"{s[k]['hit']}/{s[k]['n']}"


ac_ok = s["auto_clear_correctness"]["hit"] == s["auto_clear_correctness"]["n"]
vals = {
    "catch_strict": r("catch_strict"),
    "false_flags": r("false_flag_fields"),
    "clean_docs": f"{s['false_flag_docs']['n'] - s['false_flag_docs']['hit']}/{s['false_flag_docs']['n']}",
    "auto_clear": r("auto_clear_correctness") + (" (100%)" if ac_ok else " — NOT 100%: tiered-autonomy claim does not hold"),
    "agreement": r("agreement"),
    "trap": r("trap_resolved"),
    "cost": f"${s['cost_per_doc_usd']:.3f}",
    "run_id": s["run_id"],
}
tpl = Path("docs/BRIEF.template.md").read_text()
out = tpl.format(**vals)
Path("BRIEF.md").write_text(out)
print("BRIEF.md written from run", s["run_id"], vals)
