"""Provenance graph: built from what the run stored, never from a re-run.

The properties worth asserting are the ones a reviewer would challenge: the picture matches the
trace, a reused reading is not drawn as a purchased one, a missing artifact is visible rather than
blank, and drawing cannot touch the run.
"""
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from coherence_gate.config import ROOT
from coherence_gate.report import provenance as P

SHOWCASE = ROOT / "runs" / "showcase"
pytestmark = pytest.mark.skipif(not (SHOWCASE / "trace.jsonl").exists(), reason="no frozen showcase run in this checkout")


def _doc_with(pred) -> str:
    for d in sorted(p.name for p in SHOWCASE.iterdir() if p.is_dir() and (p / "summary.json").exists()):
        if pred(json.loads((SHOWCASE / d / "summary.json").read_text())):
            return d
    pytest.skip("no document of that shape in the showcase run")


def test_graph_covers_the_pipeline_and_links_every_artifact_it_names():
    doc = _doc_with(lambda s: s.get("document_lane") == "TRIAGE")
    g = P.build(SHOWCASE, doc)
    ids = {n.id for n in g.nodes}
    assert {"doc", "book_in", "ex_gemini", "ex_claude", "lookup", "merge", "compare", "lanes", "out"} <= ids
    # every href a node advertises must exist relative to the run directory
    for n in g.nodes:
        if n.href and not n.href.startswith(("http", "/")):
            assert (SHOWCASE / n.href).exists(), f"{n.id} links to a missing artifact: {n.href}"
    # edges only ever join declared nodes
    for e in g.edges:
        assert g.by_id(e.src) and g.by_id(e.dst), f"dangling edge {e.src}->{e.dst}"
    # columns are contiguous: a stage that produced nothing leaves no blank column
    cols = sorted({n.col for n in g.nodes})
    assert cols == list(range(len(cols)))


def test_a_reused_reading_is_drawn_as_reused_not_as_a_purchase():
    """The release run is resumed (ADR-31): its extractions were reused under an unchanged document
    hash. A graph that showed them as fresh calls would overstate what the run paid for."""
    trace = [json.loads(l) for l in (SHOWCASE / "trace.jsonl").read_text().splitlines()]
    reused = {t["doc_id"] for t in trace if t["step"].startswith("extract:") and t["outcome"] == "CACHED"}
    if not reused:
        pytest.skip("this showcase run bought every reading")
    doc = sorted(reused)[0]
    g = P.build(SHOWCASE, doc)
    node = g.by_id("ex_gemini")
    assert node.outcome in P.REUSED
    assert P._tone(node.outcome) == (P.C["reuse"], P.C["reusebg"])   # blue, not green
    assert "reused" in node.metrics


def test_missing_artifacts_produce_a_visible_node_not_a_blank(tmp_path):
    run = tmp_path / "run"; (run / "G01").mkdir(parents=True)
    (run / "G01" / "summary.json").write_text(json.dumps({"doc_id": "G01", "document_lane": "TRIAGE", "source": "txt"}))
    g = P.build(run, "G01")                       # no trace, no extractions, no booking
    assert g.by_id("book_in").outcome == "NOT_FOUND" and "not found" in g.by_id("book_in").metrics
    assert g.by_id("ex_claude").outcome == "MISSING"
    svg = P.render_svg(g)
    assert "MISSING" in svg and ET.fromstring(svg) is not None


def test_svg_is_well_formed_and_scopes_its_own_styles():
    doc = _doc_with(lambda s: True)
    svg = P.render_svg(P.build(SHOWCASE, doc))
    root = ET.fromstring(svg)                      # raises if the markup is malformed
    assert root.tag.endswith("svg")
    style = "".join(e.text or "" for e in root.iter() if e.tag.endswith("style"))
    # an inline <svg> shares the page's stylesheet: every rule must be scoped or it leaks onto the desk view
    assert style and all(rule.strip().startswith(".pgraph") for rule in style.split("}") if rule.strip())


def test_drawing_the_graph_cannot_change_the_run(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(SHOWCASE, run)
    doc = sorted(p.name for p in run.iterdir() if p.is_dir() and (p / "summary.json").exists())[0]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(run.rglob("*")) if p.is_file() and p.name != "provenance.svg"}
    P.write_all(run)
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(run.rglob("*")) if p.is_file() and p.name != "provenance.svg"}
    assert before == after, "drawing the provenance graph modified the run"
    assert (run / doc / "provenance.svg").exists()


def test_write_never_raises_even_on_a_broken_run(tmp_path, monkeypatch):
    run = tmp_path / "run"; (run / "G01").mkdir(parents=True)
    (run / "G01" / "summary.json").write_text("{}")
    monkeypatch.setattr(P, "build", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = P.write(run, "G01")
    assert out and "unavailable" in out.read_text() and "boom" in out.read_text()


def test_links_resolve_from_wherever_the_graph_is_read(tmp_path):
    """The same graph is inlined in a page that sits in the run directory and written as a file that
    sits one level deeper. Both copies must link to artifacts that actually exist from their own place."""
    import re
    doc = _doc_with(lambda s: True)
    page = P.build(SHOWCASE, doc)                       # as inlined in desk_view.html / run_report.html
    for n in page.nodes:
        if n.href:
            assert (SHOWCASE / n.href).exists(), f"page link broken: {n.href}"
    P.write(SHOWCASE, doc)
    svg = (SHOWCASE / doc / "provenance.svg").read_text()
    hrefs = set(re.findall(r'(?<!xlink:)href="([^"]+)"', svg))
    assert hrefs
    for h in hrefs:
        assert (SHOWCASE / doc / h).exists(), f"file link broken: {h}"
