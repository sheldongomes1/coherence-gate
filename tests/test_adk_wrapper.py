"""ADK packaging: the framework must change nothing about the result.

This is the acceptance test for ADR-34. Both paths are given the SAME readings (the ones the frozen
showcase run stored, replayed by a fake extractor, so no model is called) and must produce identical
findings, identical lanes and identical attestation hashes. If the wrapper ever starts re-expressing
the deterministic core instead of calling it, this test is what goes red.
"""
import json
import shutil
from pathlib import Path

import pytest

from coherence_gate.config import ROOT
from coherence_gate.eval.harness import build_context
from coherence_gate.types import Extraction, Family

adk = pytest.importorskip("google.adk", reason="google-adk is optional: `uv pip install google-adk`")

SHOWCASE = ROOT / "runs" / "showcase"
pytestmark = pytest.mark.skipif(not (SHOWCASE / "trace.jsonl").exists(), reason="no frozen showcase run")

VOLATILE = {"cost_usd"}          # timing and spend differ by microseconds; the decision must not


class ReplayExtractor:
    """Returns the reading this family gave in the frozen run. No network, no variance: the point of
    the test is the code around the reading, not the reading."""

    def __init__(self, family: Family, doc_dir: Path):
        self.family, self.doc_dir = family, doc_dir

    def extract(self, text: str, *, doc_id: str, tracer, schema) -> Extraction:
        ex = Extraction.model_validate(json.loads((self.doc_dir / f"extraction_{self.family}.json").read_text()))
        tracer.step(doc_id=doc_id, step=f"extract:{self.family}", outcome="OK", model=ex.model,
                    model_version=ex.model_version, detail={"replayed": True})
        return ex


def _ctx(tmp_path: Path, doc: str, tag: str):
    ctx = build_context(ROOT / "golden", tmp_path / tag, stub=True, source="txt")
    ctx.extractors = {fam: ReplayExtractor(fam, SHOWCASE / doc) for fam in (Family.gemini, Family.claude)}
    return ctx


def _artifacts(run_dir: Path, doc: str) -> dict[str, object]:
    out: dict[str, object] = {}
    for name in ("findings.json", "merged.json", "booking.json", "auto_clear.json", "triage.json", "summary.json"):
        p = run_dir / doc / name
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        if name == "summary.json":
            data = {k: v for k, v in data.items() if k not in VOLATILE}
        out[name] = data
    return out


@pytest.mark.parametrize("doc", ["G11", "G14"])         # one clean note, one option with relations and a reference claim
def test_adk_path_produces_the_same_result_as_the_direct_path(tmp_path, doc):
    from coherence_gate.adk import run_document_adk_sync
    from coherence_gate.pipeline import run_document

    src = ROOT / "golden" / "termsheets" / f"{doc}.txt"
    trade = json.loads((SHOWCASE / doc / "summary.json").read_text()).get("trade_id")

    direct_ctx = _ctx(tmp_path, doc, "direct")
    direct = run_document(src, direct_ctx, trade_id=trade)

    adk_ctx = _ctx(tmp_path, doc, "adk")
    via_adk = run_document_adk_sync(src, adk_ctx, trade_id=trade)

    assert via_adk.document_lane == direct.document_lane
    assert via_adk.sha256 == direct.sha256
    assert via_adk.extras["attested_hashes"] == direct.extras["attested_hashes"]
    assert [f.model_dump() for f in via_adk.findings] == [f.model_dump() for f in direct.findings]
    assert _artifacts(adk_ctx.out_dir, doc) == _artifacts(direct_ctx.out_dir, doc)


def test_composition_is_code_ordered_and_contains_no_llm_planner(tmp_path):
    """The claim that survives a model-risk review: nothing in this tree lets a model choose the order."""
    from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

    from coherence_gate.adk import Work, build_app

    ctx = _ctx(tmp_path, "G11", "shape")
    app = build_app(Work(ctx=ctx, doc_path=ROOT / "golden" / "termsheets" / "G11.txt"))
    assert isinstance(app, SequentialAgent)
    assert [a.name for a in app.sub_agents] == ["read_document", "read_both_families", "decide_and_explain"]
    parallel = app.sub_agents[1]
    assert isinstance(parallel, ParallelAgent)
    assert [a.name for a in parallel.sub_agents] == ["extract_gemini", "extract_claude"]

    def walk(agent):
        yield agent
        for child in getattr(agent, "sub_agents", []) or []:
            yield from walk(child)

    assert not [a for a in walk(app) if isinstance(a, LlmAgent)], "an LLM agent would decide control flow"


def test_events_report_each_stage_for_the_trace(tmp_path):
    import asyncio

    from coherence_gate.adk import run_document_adk

    ctx = _ctx(tmp_path, "G11", "events")
    events: list = []
    asyncio.run(run_document_adk(ROOT / "golden" / "termsheets" / "G11.txt", ctx,
                                 trade_id="SN-2026-0111", collect_events=events))
    authors = [e.author for e in events if e.actions and e.actions.state_delta]
    assert {"read_document", "extract_gemini", "extract_claude", "decide_and_explain"} <= set(authors)
    deltas = {e.author: e.actions.state_delta for e in events if e.actions and e.actions.state_delta}
    assert deltas["read_document"]["product_type"] == "note"
    assert deltas["decide_and_explain"]["attested"] == deltas["read_document"]["sha256"]


def test_a_stage_that_fails_is_not_reported_as_a_clean_run(tmp_path, monkeypatch):
    """A step that yields nothing must raise, never return an empty result that reads like success."""
    from coherence_gate import adk as adk_pkg
    from coherence_gate.adk import run_document_adk_sync

    monkeypatch.setattr(adk_pkg.app, "_complete", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("compare blew up")))
    ctx = _ctx(tmp_path, "G11", "fail")
    with pytest.raises(RuntimeError):
        run_document_adk_sync(ROOT / "golden" / "termsheets" / "G11.txt", ctx, trade_id="SN-2026-0111")


def test_wrapper_states_its_dependency_when_adk_is_absent(monkeypatch):
    import builtins

    from coherence_gate.adk import app as mod

    real = builtins.__import__

    def no_adk(name, *a, **k):
        if name.startswith("google.adk"):
            raise ImportError("no module named google.adk")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_adk)
    with pytest.raises(ImportError, match="uv pip install google-adk"):
        mod._require_adk()
