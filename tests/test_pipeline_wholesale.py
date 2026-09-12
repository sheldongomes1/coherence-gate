"""A wholesale extractor failure produces MALFORMED findings, a deterministic note, and ZERO
triage model calls (ADR-18). Uses the stub extractors, so no network."""
from pathlib import Path

from coherence_gate.eval.harness import build_context
from coherence_gate.pipeline import run_document
from coherence_gate.types import FindingType, Lane

ROOT = Path(__file__).resolve().parents[1]


class SpyTriage:
    calls = 0

    def triage(self, **kw):
        SpyTriage.calls += len(kw["findings"])


def test_wholesale_failure_short_circuits_triage(tmp_path):
    ctx = build_context(ROOT / "golden", tmp_path, stub=True)
    ctx.triage = SpyTriage()
    r = run_document(ROOT / "golden" / "termsheets" / "G11.txt", ctx)
    ctx.booking.close()
    assert r.document_lane is Lane.TRIAGE
    assert all(f.type is FindingType.MALFORMED_EXTRACTION for f in r.findings)
    assert all(f.triage and "No desk action" in f.triage.desk_query for f in r.findings)
    assert SpyTriage.calls == 0
    assert any(l["step"] == "triage" and l["outcome"] == "SKIPPED_WHOLESALE_FAILURE" for l in ctx.tracer.lines)
