"""CS7b: eval_diff.md from two run summaries (baseline vs rerun after ONE pinned change).
Usage: eval_diff.py <baseline summary.json> <candidate summary.json> [label_a] [label_b] > eval_diff.md"""
import json
import sys
from pathlib import Path

a_path, b_path = Path(sys.argv[1]), Path(sys.argv[2])
la = sys.argv[3] if len(sys.argv) > 3 else "baseline"
lb = sys.argv[4] if len(sys.argv) > 4 else "candidate"
A, B = json.loads(a_path.read_text()), json.loads(b_path.read_text())


def r(s, k):
    return f"{s[k]['hit']}/{s[k]['n']}"


def d(s, k):
    return B[k]["hit"] - A[k]["hit"]


lines = [
    "# eval_diff.md — model/effort change, before vs after", "",
    "**A model deprecation is this diff: rerun, compare, accept or hold. The judgment (schema, prompts, tolerances, golden set) is versioned and did not change.**", "",
    f"| | {la} | {lb} | delta |", "|---|---|---|---|",
    f"| run id | {A['run_id']} | {B['run_id']} | |",
    f"| strict catch (field + type) | {r(A,'catch_strict')} | {r(B,'catch_strict')} | {d(A,'catch_strict'):+d} |",
    f"| field-level catch (diagnostic) | {r(A,'catch_field_only')} | {r(B,'catch_field_only')} | {d(A,'catch_field_only'):+d} |",
    f"| false flags on clean fields (lower is better) | {r(A,'false_flag_fields')} | {r(B,'false_flag_fields')} | {d(A,'false_flag_fields'):+d} |",
    f"| cross-family agreement | {r(A,'agreement')} | {r(B,'agreement')} | {d(A,'agreement'):+d} |",
    f"| auto-clear correctness | {r(A,'auto_clear_correctness')} | {r(B,'auto_clear_correctness')} | {d(A,'auto_clear_correctness'):+d} |",
    f"| extraction accuracy gemini | {r(A['extraction_accuracy'],'gemini')} | {r(B['extraction_accuracy'],'gemini')} | {B['extraction_accuracy']['gemini']['hit']-A['extraction_accuracy']['gemini']['hit']:+d} |",
    f"| extraction accuracy claude | {r(A['extraction_accuracy'],'claude')} | {r(B['extraction_accuracy'],'claude')} | {B['extraction_accuracy']['claude']['hit']-A['extraction_accuracy']['claude']['hit']:+d} |",
    f"| cost per document (USD) | ${A['cost_per_doc_usd']:.4f} | ${B['cost_per_doc_usd']:.4f} | {B['cost_per_doc_usd']-A['cost_per_doc_usd']:+.4f} |",
    "",
]
# per-field outcome changes (planted detail + field accuracy where present)
pa = {(p["doc"], p["field"]): p for p in A.get("planted_detail", [])}
pb = {(p["doc"], p["field"]): p for p in B.get("planted_detail", [])}
moved = [(k, pa[k]["reported"], pb[k]["reported"]) for k in sorted(set(pa) & set(pb)) if pa[k]["reported"] != pb[k]["reported"]]
lines += ["## Planted findings whose reported outcome moved", ""]
lines += (["| doc | field | before | after |", "|---|---|---|---|"] + [f"| {k[0]} | {k[1]} | {x} | {y} |" for k, x, y in moved]) if moved else ["none"]
fa, fb = A.get("field_accuracy", {}), B.get("field_accuracy", {})
lines += ["", "## Extraction fields whose correctness moved", ""]
rows = []
for fam in sorted(set(fa) | set(fb)):
    for k in sorted(set(fa.get(fam, {})) | set(fb.get(fam, {}))):
        x, y = fa.get(fam, {}).get(k), fb.get(fam, {}).get(k)
        if x != y and x is not None and y is not None:
            rows.append(f"| {fam} | {k} | {'ok' if x else 'wrong'} | {'ok' if y else 'wrong'} |")
lines += (["| family | doc:field | before | after |", "|---|---|---|---|"] + rows) if rows else ["none recorded (per-field accuracy is stored from v0.2 runs onward)"]
lines += ["", f"n: {A['n_docs']} documents in both runs. Directional, not statistically significant."]
print("\n".join(lines))
