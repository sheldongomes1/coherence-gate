"""recheck_document reuses the stored extractions when the document is unchanged (no extraction
calls), re-runs the deterministic steps against the CURRENT booking, and keeps prior desk queries
for unchanged findings. Stub extractors: outcomes are MALFORMED either way, but the plumbing —
REUSED_EXTRACTION trace line, CACHED extract lines, results written in place — is what is tested."""
import json
import shutil

import pytest
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


def test_a_finding_identity_survives_the_json_round_trip():
    """The money bug: a stepping schedule is [Decimal('100'), …] in memory and ["100", …] on disk, so
    a str() key made the same finding look new on every recheck and paid for a fresh desk query."""
    from decimal import Decimal
    from datetime import date
    from coherence_gate.pipeline import _finding_key
    for in_memory, on_disk in (
        ([Decimal("100"), Decimal("95"), Decimal("90")], ["100", "95", "90"]),
        (Decimal("8.25"), "8.25"),
        (date(2027, 5, 12), "2027-05-12"),
        (None, None),
        (True, True),
    ):
        assert _finding_key("f", "MISMATCH", in_memory, None) == _finding_key("f", "MISMATCH", on_disk, None)


def test_recheck_of_an_unchanged_document_reuses_every_desk_query(tmp_path):
    """A recheck that re-drafts a query is a recheck that costs money; ADR-29 says it must not."""
    import json
    from coherence_gate.config import ROOT
    from coherence_gate.eval.harness import build_context
    from coherence_gate.types import Extraction, Family
    from coherence_gate.pipeline import recheck_document, run_document

    showcase = ROOT / "runs" / "showcase"
    doc = "G07"                                   # the document whose value is a list of Decimals
    if not (showcase / doc / "extraction_gemini.json").exists():
        pytest.skip("no frozen showcase run")

    class Replay:
        def __init__(self, fam): self.fam = fam
        def extract(self, text, *, doc_id, tracer, schema):
            ex = Extraction.model_validate(json.loads((showcase / doc / f"extraction_{self.fam}.json").read_text()))
            tracer.step(doc_id=doc_id, step=f"extract:{self.fam}", outcome="OK", model=ex.model)
            return ex

    store = tmp_path / "bookings"; shutil.copytree(ROOT / "golden" / "bookings", store)
    ctx = build_context(ROOT / "golden", tmp_path / "runs", stub=True, source="txt")
    ctx.extractors = {f: Replay(f) for f in (Family.gemini, Family.claude)}
    from coherence_gate.booking.client import DirectBookingClient
    ctx.booking = DirectBookingClient(store)
    r1 = run_document(ROOT / "golden" / "termsheets" / f"{doc}.txt", ctx)

    # stand in for the triage agent: every non-clean finding leaves a drafted query behind
    fpath = r1.out_dir / "findings.json"
    raw = json.loads(fpath.read_text())
    non_clean = [f for f in raw if f["type"] != "CLEAN"]
    assert non_clean, "this document should have something to triage"
    for f in raw:
        if f["type"] != "CLEAN":
            f["triage"] = {"classification": "BOOKING_LIKELY_WRONG", "desk_query": "drafted once",
                           "cited_clause": "clause", "booking_field": f["field"],
                           "booking_value": str(f.get("booking_value")), "rationale": "stand-in for the triage agent"}
    fpath.write_text(json.dumps(raw, default=str))

    r2 = recheck_document(doc, ctx, ctx.out_dir)
    redrafted = [f.field for f in r2.findings if f.type != "CLEAN" and f.triage is None]
    assert not redrafted, f"these findings would be re-triaged (and re-paid) on every recheck: {redrafted}"
