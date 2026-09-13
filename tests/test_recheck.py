"""recheck_document reuses the stored extractions when the document is unchanged (no extraction
calls), re-runs the deterministic steps against the CURRENT booking, and keeps prior desk queries
for unchanged findings. Stub extractors: outcomes are MALFORMED either way, but the plumbing —
REUSED_EXTRACTION trace line, CACHED extract lines, results written in place — is what is tested."""
import json
import shutil
from pathlib import Path

from coherence_gate.eval.harness import build_context
from coherence_gate.pipeline import recheck_document, run_document

ROOT = Path(__file__).resolve().parents[1]


def test_recheck_reuses_extractions_and_reads_current_booking(tmp_path):
    store = tmp_path / "bookings"; shutil.copytree(ROOT / "golden" / "bookings", store)
    ctx = build_context(ROOT / "golden", tmp_path / "runs", stub=True)
    from coherence_gate.booking.client import DirectBookingClient
    ctx.booking = DirectBookingClient(store)
    r1 = run_document(ROOT / "golden" / "termsheets" / "G11.txt", ctx, trade_id="SN-2026-0111")
    b = store / "SN-2026-0111.json"; rec = json.loads(b.read_text()); rec["currency"] = "CAD"; b.write_text(json.dumps(rec))
    mark = ctx.tracer.mark()
    r2 = recheck_document("G11", ctx, ctx.out_dir, trade_id="SN-2026-0111")
    new = [l for l in ctx.tracer.lines if l["seq"] >= mark]
    assert any(l["step"] == "load" and l["outcome"] == "REUSED_EXTRACTION" for l in new)
    assert all(l["outcome"] == "CACHED" for l in new if l["step"].startswith("extract:"))
    assert r2.booking["record"]["currency"] == "CAD"            # the current booking was read
    assert r2.out_dir == r1.out_dir and (r2.out_dir / "findings.json").exists()


def test_tracer_cost_is_per_pass_and_window_is_bounded(tmp_path):
    from coherence_gate.trace import Tracer
    t = Tracer(run_id="t", path=tmp_path / "trace.jsonl")
    t.step(doc_id="G01", step="extract:claude", outcome="OK", cost_usd=1.0)
    m = t.mark()
    t.step(doc_id="G01", step="extract:claude", outcome="CACHED", cost_usd=0.25)
    assert t.total_cost("G01") == 1.25 and t.total_cost("G01", since=m) == 0.25   # second pass costs only itself
    t.lines = type(t.lines)(maxlen=3)
    for i in range(10):
        t.step(doc_id="G02", step="x", outcome="OK")
    assert len(t.lines) == 3 and sum(1 for _ in open(tmp_path / "trace.jsonl")) == 12  # memory bounded, file complete


def test_cost_breakdown_separates_readings_from_desk_queries(tmp_path):
    from coherence_gate.trace import Tracer
    t = Tracer(run_id="t", path=tmp_path / "trace.jsonl")
    t.step(doc_id="G01", step="extract:claude", outcome="OK", cost_usd=0.5)
    t.step(doc_id="G01", step="triage:coupon", outcome="OK", cost_usd=0.2)
    assert t.total_cost("G01") == 0.7 and t.total_cost("G01", step_prefix="triage:") == 0.2
