"""Parser interface, local fallback, cache, and the pdf source path with stub extractors (no network)."""
import json
from pathlib import Path

from coherence_gate.eval.harness import build_context
from coherence_gate.ingest import LocalParser, parse_document
from coherence_gate.pipeline import run_document

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "golden" / "pdf" / "G12.pdf"


def test_local_parser_and_cache(tmp_path):
    res, cached = parse_document("G12", PDF, LocalParser(), tmp_path)
    assert not cached and "SN-2026-0112" in res.markdown and res.meta["vendor"] == "local-fallback"
    assert (tmp_path / "G12.md").exists() and json.loads((tmp_path / "G12.meta.json").read_text())["pdf_sha256"]
    res2, cached2 = parse_document("G12", PDF, LocalParser(), tmp_path)
    assert cached2 and res2.markdown == res.markdown


def test_pdf_source_pipeline_cites_into_parsed_text(tmp_path):
    ctx = build_context(ROOT / "golden", tmp_path, stub=True, source="pdf", parser_name="local")
    ctx.parsed_dir = tmp_path / "parsed"
    r = run_document(ROOT / "golden" / "termsheets" / "G12.txt", ctx, pdf_path=PDF)
    ctx.booking.close()
    assert r.source == "pdf" and r.parse_meta["vendor"] == "local-fallback"
    steps = [l["step"] for l in ctx.tracer.lines]
    assert steps.index("parse") < steps.index("load")
    assert any(l["step"] == "parse" and l["outcome"] == "OK" for l in ctx.tracer.lines)
