"""BigQuery sink: the row shape and the guarantees that hold without touching a cloud."""
import json
from pathlib import Path

import pytest

from coherence_gate.sink import bq


def _trace(tmp_path: Path, lines: list[dict]) -> Path:
    run = tmp_path / "run"; run.mkdir()
    (run / "trace.jsonl").write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    return run


BASE = {"ts": "2026-09-14T10:00:00.000+00:00", "run_id": "20260914-100000", "doc_id": "G01",
        "prompt_tokens": 10, "output_tokens": 20, "latency_ms": 500, "cost_usd": 0.01}


def test_rows_carry_the_distinctions_the_report_makes(tmp_path):
    run = _trace(tmp_path, [
        {**BASE, "step": "extract:gemini", "outcome": "OK", "model": "gemini-3.8-flash", "detail": {"violations": []}},
        {**BASE, "step": "extract:claude", "outcome": "API_ERROR", "detail": "credit balance is too low"},
        {**BASE, "step": "extract:claude", "outcome": "CACHED", "doc_id": "G02"},
        {**BASE, "step": "compare", "outcome": "TRIAGE", "otel": {"gen_ai.system": "anthropic"}},
    ])
    plan = bq.prepare(run, "proj", "ds")
    rows = [json.loads(l) for l in plan.ndjson.read_text().splitlines()]
    assert [r["family"] for r in rows] == ["gemini", "claude", "claude", None]     # derived from the step name
    # "the model never answered" vs "the model answered" is the distinction a billing event hides
    assert [r["completed"] for r in rows] == [True, False, True, True]
    assert json.loads(rows[0]["detail"]) == {"violations": []}
    assert json.loads(rows[3]["otel"])["gen_ai.system"] == "anthropic"
    assert rows[1]["detail"] == '"credit balance is too low"'


def test_staging_never_writes_into_the_run(tmp_path):
    """A frozen run is evidence; an export must leave it byte-identical (same rule as ADR-33)."""
    import hashlib
    run = _trace(tmp_path, [{**BASE, "step": "load", "outcome": "OK"}])
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
    plan = bq.prepare(run, "proj", "ds")
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}
    assert before == after
    assert run not in plan.ndjson.parents and plan.ndjson.exists()


def test_lines_that_are_not_evidence_are_dropped(tmp_path):
    run = _trace(tmp_path, [
        {**BASE, "step": "load", "outcome": "OK"},
        {"step": "load", "outcome": "OK"},                       # no ts, no run_id
        {"ts": BASE["ts"], "step": "load", "outcome": "OK"},     # no run_id
    ])
    plan = bq.prepare(run, "proj", "ds")
    assert plan.rows == 1 and plan.run_ids == ["20260914-100000"]


def test_load_commands_name_the_partitioned_clustered_table(tmp_path):
    run = _trace(tmp_path, [{**BASE, "step": "load", "outcome": "OK"}])
    plan = bq.prepare(run, "proj", "ds", "trace")
    flat = [" ".join(c) for c in plan.commands]
    assert any("mk --dataset" in c or "mk --dataset" in c.replace("  ", " ") for c in flat)
    assert any("--time_partitioning_field ts" in c and "--clustering_fields run_id,step,doc_id" in c for c in flat)
    assert any("load --source_format NEWLINE_DELIMITED_JSON proj:ds.trace" in c for c in flat)
    assert plan.table == "proj.ds.trace"


def test_every_view_formats_and_filters_non_document_rows():
    for name, sql in bq.VIEWS.items():
        body = sql.format(table="p.d.t", nondoc=bq.NON_DOCUMENT)
        assert "p.d.t" in body, name
    # the config line and the one-off methodology extraction are not documents and must not be counted
    counted = bq.VIEWS["v_cost_by_run"].format(table="p.d.t", nondoc=bq.NON_DOCUMENT)
    assert "'-'" in counted and "'REF'" in counted


def test_missing_trace_is_an_error_not_an_empty_load(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError):
        bq.prepare(tmp_path / "empty", "proj", "ds")


def test_export_reports_failure_when_bq_is_absent(tmp_path, monkeypatch):
    run = _trace(tmp_path, [{**BASE, "step": "load", "outcome": "OK"}])
    monkeypatch.setattr(bq.shutil, "which", lambda _: None)
    res = bq.export_run(run, "proj", "ds")
    assert res["loaded"] is False and "bq CLI" in res["steps"][0][2]
