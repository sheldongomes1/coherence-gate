"""`cg propose` (CS8c): read feedback/feedback.jsonl, draft one proposal per entry into
proposals/<kind>/<id>.md. Drafting is an LLM call with triage-style containment; writing is code;
applying is a human commit followed by `make eval` and `make eval-diff`."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..config import ROOT, load_config
from ..trace import Tracer, run_with_deadline

KINDS = ("golden_candidate", "judgment_change", "error_register")
FOOTER = ("\n\n---\nPROPOSAL ONLY — apply via its own commit, rerun `make eval`, review the diff. "
          "Nothing in this file has been applied.\n")
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["kind", "title", "body", "predicted_effect", "rationale"],
          "properties": {"kind": {"type": "string", "enum": list(KINDS)}, "title": {"type": "string"},
                         "body": {"type": "string"}, "predicted_effect": {"type": "string"}, "rationale": {"type": "string"}}}


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(ROOT / "prompts")), undefined=StrictUndefined, autoescape=False,
                       trim_blocks=True, lstrip_blocks=True)


def _citations(entry: dict, runs_root: Path) -> list[str]:
    fp = runs_root / entry["run_id"] / entry["doc_id"] / "findings.json"
    if not fp.exists():
        return []
    f = next((x for x in json.loads(fp.read_text()) if x["field"] == entry["field"]), None)
    return [c["text_span"] for c in (f or {}).get("citations", [])]


def draft_with_claude(prompt: str, tracer: Tracer, doc_id: str) -> dict:
    import anthropic
    cfg = load_config()
    client = anthropic.Anthropic(timeout=cfg.extraction.timeout_s, max_retries=2)
    with tracer.timed(doc_id=doc_id, step="propose", pin=cfg.triage) as u:
        resp = run_with_deadline(lambda: client.messages.create(
            model=cfg.triage.model, max_tokens=4000,
            system="You draft precise, reviewable change proposals for an eval-gated document-coherence system.",
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}}), 300.0, what="propose")
        u.model_version, u.prompt_tokens, u.output_tokens = resp.model, resp.usage.input_tokens, resp.usage.output_tokens
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return json.loads(text)


def propose_all(feedback_file: Path, out_dir: Path, runs_root: Path, drafter=draft_with_claude,
                tracer: Tracer | None = None, only_unproposed: bool = True) -> list[Path]:
    tracer = tracer or Tracer(run_id="propose", path=out_dir / "trace.jsonl")
    entries = [json.loads(l) for l in feedback_file.read_text().splitlines() if l.strip()] if feedback_file.exists() else []
    written: list[Path] = []
    for e in entries:
        pid = f"{e['run_id']}_{e['finding_id'].replace(':', '_')}_{e['verdict']}"
        if only_unproposed and list(out_dir.glob(f"*/{pid}.md")):
            continue
        prompt = _env().get_template("propose_v1.md").render(
            finding_id=e["finding_id"], doc_id=e["doc_id"], field=e["field"], finding_type=e["finding_type"],
            severity=e.get("severity", ""), ts_value=e.get("ts_value"), booking_value=e.get("booking_value"),
            detail=e.get("detail", ""), verdict=e["verdict"], note=e.get("note") or "(none)",
            citations=_citations(e, runs_root))
        d = drafter(prompt, tracer, e["doc_id"])
        kind = d["kind"] if d.get("kind") in KINDS else "error_register"
        body = (f"# {d['title']}\n\n**Kind:** {kind}  \n**From feedback:** {e['finding_id']} ({e['finding_type']}, {e['verdict']}) "
                f"in run {e['run_id']}  \n**Desk note:** {e.get('note') or '(none)'}  \n**Drafted:** {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n\n"
                f"{d['body']}\n\n**Predicted effect:** {d['predicted_effect']}\n\n**Rationale:** {d['rationale']}" + FOOTER)
        p = out_dir / kind / f"{pid}.md"
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(body); written.append(p)
    return written
