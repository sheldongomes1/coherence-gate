import json
from pathlib import Path

from coherence_gate.feedback import propose_all
from coherence_gate.trace import Tracer


def test_propose_writes_reviewable_file_and_never_applies(tmp_path):
    fb = tmp_path / "feedback.jsonl"
    fb.write_text(json.dumps({"ts": "t", "run_id": "r1", "finding_id": "G01:barrier_level_pct", "doc_id": "G01", "field": "barrier_level_pct",
                              "finding_type": "MISMATCH", "severity": "critical", "verdict": "desk_rejected", "note": "70 is correct per amendment",
                              "ts_value": "65", "booking_value": "70", "detail": "TS 65 ≠ booking 70"}) + "\n")
    def fake_drafter(prompt, tracer, doc_id):
        assert "70 is correct per amendment" in prompt and "never learns" in prompt
        return {"kind": "golden_candidate", "title": "Amended barrier case", "body": "Add a term sheet + amendment pair.",
                "predicted_effect": "false-flag rate should fall; catch rate unchanged", "rationale": "desk cited an amendment"}
    out = tmp_path / "proposals"
    written = propose_all(fb, out, tmp_path / "runs", drafter=fake_drafter, tracer=Tracer(run_id="t", path=tmp_path / "trace.jsonl"))
    assert len(written) == 1 and written[0].parent.name == "golden_candidate"
    txt = written[0].read_text()
    assert "PROPOSAL ONLY" in txt and "Nothing in this file has been applied" in txt and "Predicted effect" in txt
    assert propose_all(fb, out, tmp_path / "runs", drafter=fake_drafter) == []   # idempotent: already proposed
