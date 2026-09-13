"""`cg eval --resume`: a document whose extraction calls completed in a prior run is re-checked from the stored
extractions; one whose call never completed is extracted again; the report names both sets."""
import json
from pathlib import Path

from coherence_gate.config import ROOT
from coherence_gate.eval.harness import completed_extractions, run_eval


def _fake_prior(tmp_path: Path) -> Path:
    prior = tmp_path / "prior"; (prior / "G11").mkdir(parents=True); (prior / "G10").mkdir()
    lines = [
        {"doc_id": "G11", "step": "extract:gemini", "outcome": "OK"}, {"doc_id": "G11", "step": "extract:claude", "outcome": "OK"},
        {"doc_id": "G10", "step": "extract:gemini", "outcome": "TIMEOUT"}, {"doc_id": "G10", "step": "extract:claude", "outcome": "OK"},
        {"doc_id": "REF", "step": "extract:gemini", "outcome": "API_ERROR"},
    ]
    (prior / "trace.jsonl").write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    (prior / "G11" / "summary.json").write_text("{}"); (prior / "G10" / "summary.json").write_text("{}")
    return prior


def test_only_documents_with_both_calls_completed_are_reusable(tmp_path):
    assert completed_extractions(_fake_prior(tmp_path)) == {"G11"}
    assert completed_extractions(tmp_path / "missing") == set()


def test_resume_reuses_completed_and_reextracts_the_rest(tmp_path):
    golden = ROOT / "golden"
    first = run_eval(golden, tmp_path / "runs", stub=True, only=["G11", "G10"], source="txt", reference=False)
    prior = first.run_dir
    # pretend G11's calls completed in the prior run (the stub records API_ERROR on every call)
    trace = prior / "trace.jsonl"
    fixed = []
    for line in trace.read_text().splitlines():
        d = json.loads(line)
        if d["doc_id"] == "G11" and d["step"].startswith("extract:"):
            d["outcome"] = "OK"
        fixed.append(json.dumps(d))
    trace.write_text("\n".join(fixed) + "\n")
    second = run_eval(golden, tmp_path / "runs", stub=True, only=["G11", "G10"], source="txt", reference=False, resume=prior)
    assert {k: second.resumed[k] for k in ("prior_run", "reused", "re_extracted")} == {"prior_run": str(prior), "reused": ["G11"], "re_extracted": ["G10"]}
    assert second.resumed["prior_never_completed"] == {"G10": {"gemini": "API_ERROR", "claude": "API_ERROR"}}   # the prior failure is named
    steps = [(json.loads(l)["doc_id"], json.loads(l)["step"], json.loads(l)["outcome"]) for l in (second.run_dir / "trace.jsonl").read_text().splitlines()]
    assert ("G11", "load", "REUSED_EXTRACTION") in steps and ("G11", "extract:claude", "CACHED") in steps
    assert ("G10", "extract:claude", "API_ERROR") in steps          # extracted again (stub: still fails, honestly)
    report = (second.run_dir / "eval_report.md").read_text()
    assert "Resumed from" in report and "G11" in report and "G10" in report
    assert second.never_completed["claude"]["docs"] == ["G10"]     # the reused document is not a failure of this run
