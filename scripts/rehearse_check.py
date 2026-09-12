"""CS7a rehearsal: apply one booking edit per class to a SCRATCH copy of the store, run `cg check`
on the document's PDF, and assert the expected finding type is present. Real models: ~1 min and
~$0.15 per case. Usage: uv run python scripts/rehearse_check.py [--stub]"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB = "--stub" in sys.argv
CASES = [  # (doc, trade, field, new value, expected finding field, expected type)
    ("G13", "OP-2026-0114", "participation_rate_pct", 95, "participation_rate_pct", "MISMATCH"),
    ("G13", "OP-2026-0114", "premium_amount", 830000, "rel:premium_arithmetic", "RELATION_VIOLATION"),
    ("G12", "SN-2026-0112", "coupon_memory", False, "coupon_memory", "MISMATCH"),
    ("G12", "SN-2026-0112", "barrier_level_pct", 65, "barrier_level_pct", "MISMATCH"),
    ("G12", "SN-2026-0112", "autocall_observation_dates", ["2027-05-10", "2027-11-09", "2028-05-08", "2028-11-08", "2029-05-08", "2029-11-08"], "autocall_observation_dates", "MISMATCH"),
    ("G11", "SN-2026-0111", "currency", "CAD", "currency", "MISMATCH"),
]
results = []
for doc, trade, field, value, exp_field, exp_type in CASES:
    tmp = Path(tempfile.mkdtemp(prefix="cg-rehearse-"))
    store = tmp / "bookings"; shutil.copytree(ROOT / "golden" / "bookings", store)
    b = store / f"{trade}.json"; rec = json.loads(b.read_text()); rec[field] = value; b.write_text(json.dumps(rec, indent=2))
    out = tmp / "runs"
    cmd = [sys.executable, "-m", "coherence_gate.cli", "check", str(ROOT / "golden" / "pdf" / f"{doc}.pdf"), "--trade", trade,
           "--bookings", str(store), "--out", str(out), "--no-triage"] + (["--stub"] if STUB else [])
    subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    run = sorted(out.iterdir())[-1]
    findings = json.loads((run / doc / "findings.json").read_text())
    hit = next((f for f in findings if f["field"] == exp_field and f["type"] == exp_type), None)
    other = [f for f in findings if f["type"] != "CLEAN" and f["field"] != exp_field]
    trace = [json.loads(l) for l in (run / "trace.jsonl").read_text().splitlines()]
    secs = sum(l["latency_ms"] for l in trace) / 1000; cost = sum(l["cost_usd"] for l in trace)
    results.append((doc, field, exp_type, bool(hit), len(other), secs, cost, hit["detail"][:80] if hit else "MISSED"))
print("| doc | booking edit | expected | caught | extra flags | secs | $ | detail |")
print("|---|---|---|---|---|---|---|---|")
for r in results:
    print(f"| {r[0]} | {r[1]} | {r[2]} | {'✅' if r[3] else '❌'} | {r[4]} | {r[5]:.0f} | {r[6]:.3f} | {r[7]} |")
print(f"\n{sum(r[3] for r in results)}/{len(results)} edit classes caught with the correct type")
