"""Jinja2 -> static run_report.html for one run directory (LLD §13). Reads only what the
pipeline persisted (findings.json, triage.json, summary.json, booking.json, trace.jsonl)."""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..config import ROOT
from ..trace import read_trace

TEMPLATES = ROOT / "templates"


def load_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    trace = read_trace(run_dir / "trace.jsonl") if (run_dir / "trace.jsonl").exists() else []
    docs = []
    for d in sorted(p for p in run_dir.iterdir() if p.is_dir() and (p / "summary.json").exists()):
        summary = json.loads((d / "summary.json").read_text())
        findings = json.loads((d / "findings.json").read_text())
        triage = {t["field"]: t.get("triage") for t in json.loads((d / "triage.json").read_text())} if (d / "triage.json").exists() else {}
        for f in findings:
            f["triage"] = triage.get(f["field"])
        booking = json.loads((d / "booking.json").read_text()) if (d / "booking.json").exists() else {}
        docs.append({**summary, "findings": findings, "booking_transport": booking.get("transport", "?"),
                     "attested_hashes": summary.get("attested_hashes"),
                     "trace": [l for l in trace if l["doc_id"] == summary["doc_id"]]})
    docs_cost = round(sum(d.get("cost_usd") or 0 for d in docs), 4)
    doc_ids = {d["doc_id"] for d in docs}
    triage_cost = round(sum(l["cost_usd"] for l in trace if l["step"].startswith("triage:") and l["doc_id"] in doc_ids), 4)
    # per-document summaries already include triage lines traced under the run's own id; add only later desk-query drafting
    run_ids = {l["run_id"] for l in trace}
    own = run_dir.name
    later_triage = round(sum(l["cost_usd"] for l in trace if l["step"].startswith("triage:") and l["doc_id"] in doc_ids and l["run_id"] != own), 4)
    ref_cost = round(sum(l["cost_usd"] for l in trace if l["doc_id"] == "REF"), 4)
    cost = {"documents": docs_cost, "later_desk_queries": later_triage, "methodology_once": ref_cost,
            "total": round(docs_cost + later_triage + ref_cost, 4), "n_docs": len(docs), "runs_in_trace": len(run_ids)}
    return {"run_id": run_dir.name, "docs": docs, "trace": trace, "cost": cost}


def render(run_dir: Path, out: Path | None = None) -> Path:
    from .desk_view import LEAD_RANK, RED_TYPES, AMBER_TYPES, trust_state
    data = load_run(run_dir)
    docs = data["docs"]
    fx_path = ROOT / "golden" / "desk_fixtures.json"
    fixtures = json.loads(fx_path.read_text()) if fx_path.exists() else {}
    state_order = {"MISMATCH": 0, "STALE": 1, "DISAGREEMENT": 2, "ATTESTED": 3}
    for d in docs:
        d["trust"], d["trust_why"] = trust_state(d["findings"])
        fx = fixtures.get(d["trade_id"] or "", {})
        d["exposure"] = abs(fx.get("delta_usd") or 0)
        for f in d["findings"]:
            f["attention"] = f["type"] in RED_TYPES or f["type"] in AMBER_TYPES
            f["not_evaluable"] = f["type"] == "NOT_EVALUABLE"
        d["findings"].sort(key=lambda f: (not f["attention"], f["not_evaluable"], f["severity"] != "critical", LEAD_RANK.get(f["field"], 50), f["field"]))
        d["n_attention"] = sum(f["attention"] for f in d["findings"])
    docs.sort(key=lambda d: (state_order.get(d["trust"], 9), -d["exposure"], d["doc_id"]))
    all_f = [f for d in docs for f in d["findings"]]
    models = sorted({l["model"] for l in data["trace"] if l.get("model")})
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    from ..extract.schema_guard import display_span
    env.filters["cite"] = lambda t: display_span(t or "")
    html = env.get_template("run_report.html.j2").render(
        run_id=data["run_id"], docs=docs, models=models,
        total_cost=data["cost"]["total"], cost=data["cost"],
        n_auto_docs=sum(d["document_lane"] == "AUTO_CLEAR" for d in docs),
        n_auto_fields=sum(f["lane"] == "AUTO_CLEAR" for f in all_f), n_fields=len(all_f),
        n_triage=sum(f["lane"] == "TRIAGE" for f in all_f),
        n_model_calls=sum(1 for l in data["trace"] if l.get("model")),
    )
    out = out or Path(run_dir) / "run_report.html"
    out.write_text(html)
    return out
