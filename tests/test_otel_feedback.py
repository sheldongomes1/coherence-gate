import json
from pathlib import Path

from coherence_gate.trace import Tracer, otel_span


def test_trace_lines_carry_otel_span(tmp_path):
    tr = Tracer(run_id="t", path=tmp_path / "trace.jsonl")
    tr.step(doc_id="G01", step="extract:gemini", outcome="OK", model="gemini-3.8-flash", model_version="gemini-3.8-flash",
            prompt_tokens=10, output_tokens=5, latency_ms=7, cost_usd=0.001)
    tr.step(doc_id="G01", step="booking_lookup", outcome="FOUND")
    lines = [json.loads(l) for l in (tmp_path / "trace.jsonl").read_text().splitlines()]
    a = lines[0]["otel"]
    assert a["name"] == "gen_ai.extract" and a["kind"] == "CLIENT"
    assert a["attributes"]["gen_ai.request.model"] == "gemini-3.8-flash" and a["attributes"]["gen_ai.usage.output_tokens"] == 5
    assert a["attributes"]["gen_ai.provider.name"] == "gcp.gemini"
    assert lines[1]["otel"]["attributes"]["gen_ai.operation.name"] == "execute_tool"
    assert lines[0]["prompt_tokens"] == 10  # flat keys unchanged for the report readers
    assert otel_span(step="compare", run_id="t", doc_id="G01", model=None, model_version=None, prompt_tokens=0,
                     output_tokens=0, latency_ms=0, cost_usd=0, outcome="TRIAGE")["attributes"]["code.function"] == "compare"


def test_feedback_cli_records_and_lists(tmp_path):
    from coherence_gate.cli import main
    run = tmp_path / "runs" / "20990101-000000" / "G01"; run.mkdir(parents=True)
    (run / "findings.json").write_text(json.dumps([{"field": "barrier_level_pct", "type": "MISMATCH", "severity": "critical",
                                                     "ts_value": "65", "booking_value": "70", "detail": "TS 65 ≠ booking 70"}]))
    fb = tmp_path / "fb.jsonl"
    assert main(["feedback", "G01:barrier_level_pct", "--verdict", "desk_rejected", "--note", "desk says 70 is right",
                 "--run", str(run.parent), "--file", str(fb)]) == 0
    row = json.loads(fb.read_text().splitlines()[0])
    assert row["verdict"] == "desk_rejected" and row["finding_type"] == "MISMATCH" and row["run_id"] == "20990101-000000"
    assert main(["feedback", "--list", "--file", str(fb)]) == 0
