"""Run the pipeline over golden/ and score it (LLD §14). No retries, no reruns: one pass,
scored as it fell (GOAL.md: evals report reality)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..booking.client import DirectBookingClient
from ..config import Config, load_config
from ..extract.base import StubExtractor
from ..pipeline import DocumentResult, RunContext, recheck_document, run_document
from ..schema_loader import load_schema
from ..trace import Tracer
from ..types import Family
from . import scoring


def build_context(golden: Path, out_dir: Path, *, stub: bool, config: Config | None = None,
                  booking_transport: str = "direct", with_triage: bool = False,
                  source: str = "txt", parser_name: str = "mixedbread", reference: bool = False,
                  bookings_dir: Path | None = None) -> RunContext:
    config = config or load_config()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = out_dir / run_id
    tracer = Tracer(run_id=run_id, path=run_dir / "trace.jsonl")
    from dataclasses import asdict
    from ..extract.base import prompt_sha
    tracer.step(doc_id="-", step="config", outcome="OK", detail={
        "models": {p.family: p.model for p in config.pins}, "extraction": asdict(config.extraction),
        "prompt_sha": prompt_sha(config.extraction.prompt_version), "stub": stub, "booking_transport": booking_transport,
        "source": source, "parser": parser_name if source == "pdf" else None, "reference_lane": reference,
        "bookings_dir": str(bookings_dir) if bookings_dir else None})
    for pin in config.pins:
        if not pin.pinned:
            tracer.step(doc_id="-", step="config", outcome="UNPINNED_MODEL", model=pin.model)
    if stub:
        extractors = {Family.gemini: StubExtractor(Family.gemini, config.gemini),
                      Family.claude: StubExtractor(Family.claude, config.claude)}
    else:
        from ..extract.claude import ClaudeExtractor  # S2
        from ..extract.gemini import GeminiExtractor  # S2
        extractors = {Family.gemini: GeminiExtractor(config.gemini, config.extraction),
                      Family.claude: ClaudeExtractor(config.claude, config.extraction)}
    store = Path(bookings_dir) if bookings_dir else golden / "bookings"
    if booking_transport == "mcp":
        from ..booking.mcp_client import McpBookingClient  # S1
        booking = McpBookingClient(store)
    else:
        booking = DirectBookingClient(store)
    triage = None
    if with_triage:
        from ..triage.agent import TriageAgent  # S3
        triage = TriageAgent(config.triage, effort=config.extraction.claude_effort)
    parser = None
    if source == "pdf" or reference:
        from ..ingest import get_parser
        parser = get_parser(parser_name)
    ctx = RunContext(run_id=run_id, out_dir=run_dir, config=config, tracer=tracer, schema=load_schema(),
                     booking=booking, extractors=extractors, triage=triage,
                     source=source, parser=parser, parsed_dir=golden / "parsed")
    ctx.reference_wanted = bool(reference and not stub)
    if reference and not stub:
        from ..reference import load_reference
        ctx.reference = load_reference(ctx)
    return ctx


COMPLETED = {"OK", "MALFORMED", "CACHED"}   # the model answered (rightly or wrongly); anything else never completed


def completed_extractions(prior_run: Path) -> set[str]:
    """Documents in a prior run whose LAST extraction call of EACH family completed. A TIMEOUT,
    API_ERROR, REFUSAL or a suspended process is not a reading and is never reused."""
    last: dict[tuple[str, str], str] = {}
    trace = prior_run / "trace.jsonl"
    if not trace.exists():
        return set()
    for line in trace.read_text().splitlines():
        d = json.loads(line)
        if d["step"].startswith("extract:") and d["doc_id"] != "REF":
            last[(d["doc_id"], d["step"])] = d["outcome"]
    docs = {doc for doc, _ in last}
    return {doc for doc in docs
            if all(last.get((doc, f"extract:{fam}")) in COMPLETED for fam in ("gemini", "claude"))
            and (prior_run / doc / "summary.json").exists()}


def never_completed_in(prior_run: Path) -> dict[str, dict[str, str]]:
    """doc -> {family: last outcome} for extraction calls in a prior run that never produced a reading."""
    last: dict[tuple[str, str], str] = {}
    trace = prior_run / "trace.jsonl"
    if not trace.exists():
        return {}
    for line in trace.read_text().splitlines():
        d = json.loads(line)
        if d["step"].startswith("extract:") and d["doc_id"] != "REF":
            last[(d["doc_id"], d["step"].split(":", 1)[1])] = d["outcome"]
    out: dict[str, dict[str, str]] = {}
    for (doc, fam), outcome in last.items():
        if outcome not in COMPLETED:
            out.setdefault(doc, {})[fam] = outcome
    return out


def run_eval(golden: Path, out_dir: Path, *, stub: bool, booking_transport: str = "direct",
             with_triage: bool = False, only: list[str] | None = None,
             source: str = "txt", parser_name: str = "mixedbread", reference: bool | None = None,
             resume: Path | None = None) -> scoring.EvalResult:
    """One pass over the golden set. With `resume`, documents whose extraction calls completed in the
    prior run are re-checked from those stored, hash-attested extractions (ADR-29: the deterministic
    steps run again, no model call) and only the documents whose calls never completed are extracted
    again; the report says which. A stall or a suspended host then costs one document, not the run."""
    manifest = json.loads((golden / "manifest.json").read_text())
    if reference is None:
        reference = "reference" in manifest
    ctx = build_context(golden, out_dir, stub=stub, booking_transport=booking_transport, with_triage=with_triage,
                        source=source, parser_name=parser_name, reference=reference)
    reusable = completed_extractions(Path(resume)) if resume else set()
    resumed: dict | None = None
    if resume:
        resumed = {"prior_run": str(resume), "reused": [], "re_extracted": [], "prior_never_completed": never_completed_in(Path(resume))}
        ctx.tracer.step(doc_id="-", step="config", outcome="RESUME", detail={"prior_run": str(resume), "reusable": sorted(reusable)})
    results: dict[str, DocumentResult] = {}
    try:
        for entry in manifest["documents"]:
            if only and entry["id"] not in only:
                continue
            doc = entry["id"]
            if resume and doc in reusable:
                try:
                    results[doc] = recheck_document(doc, ctx, Path(resume), trade_id=None,
                                                    product_type=entry.get("product_type"), carry_prior_cost=True)
                    resumed["reused"].append(doc)
                    continue
                except (FileNotFoundError, ValueError) as why:   # not reusable after all: extract again, and say so
                    ctx.tracer.step(doc_id=doc, step="load", outcome="RESUME_FALLBACK", detail=str(why)[:200])
            if resumed is not None:
                resumed["re_extracted"].append(doc)
            results[doc] = run_document(golden / entry["termsheet"], ctx, trade_id=None,
                                        pdf_path=(golden / entry["pdf"]) if entry.get("pdf") else None,
                                        product_type=entry.get("product_type"))
    finally:
        ctx.booking.close()
    ev = scoring.score(manifest, results, ctx, golden)
    ev.resumed = resumed
    (ctx.out_dir / "eval_report.md").write_text(scoring.render_markdown(ev))
    (ctx.out_dir / "summary.json").write_text(json.dumps(ev.summary(), indent=2))
    try:  # the two pages are generated per run (CS5); a rendering error must not lose the eval
        from ..report.desk_view import render as render_desk
        from ..report.html import render as render_html
        render_html(ctx.out_dir); render_desk(ctx.out_dir)
    except Exception as exc:  # noqa: BLE001
        ctx.tracer.step(doc_id="-", step="render", outcome="ERROR", detail=str(exc)[:200])
    return ev


def rescore(run_dir: Path, golden: Path) -> scoring.EvalResult:
    """Re-score a stored run from its artifacts with the CURRENT scoring code: no model call, no new
    reading. Extractions are reloaded and re-normalized (deterministic), findings, merges, lanes and
    costs are taken as persisted, the trace is read back. A report-format change is a rescore, not a
    rerun. The report says it was rescored and from what; `cg ablation` and `cg triage` appendices are
    re-appended by their own commands."""
    import subprocess
    from types import SimpleNamespace
    from .. import normalize
    from ..report.html import read_trace
    from ..schema_loader import all_schemas
    from ..types import Extraction, Finding, Lane
    run_dir = Path(run_dir)
    manifest = json.loads((golden / "manifest.json").read_text())
    trace = read_trace(run_dir / "trace.jsonl")
    cfg_line = next((l for l in trace if l["step"] == "config" and l["outcome"] == "OK"), {})
    run_id = cfg_line.get("run_id") or run_dir.name
    schemas = all_schemas()
    ctx = SimpleNamespace(run_id=run_id, out_dir=run_dir, config=load_config(), schemas=schemas,
                          source=(cfg_line.get("detail") or {}).get("source", "txt"), tracer=SimpleNamespace(lines=trace))
    results: dict[str, DocumentResult] = {}
    for entry in manifest["documents"]:
        d = run_dir / entry["id"]
        if not (d / "summary.json").exists():
            continue
        summary = json.loads((d / "summary.json").read_text())
        ptype = summary.get("product_type") or entry.get("product_type") or "note"
        extractions = {fam: Extraction.model_validate(json.loads((d / f"extraction_{fam}.json").read_text())) for fam in ("gemini", "claude")}
        normalized = {fam: normalize.normalize_extraction(e, schemas[ptype]) for fam, e in extractions.items()}
        results[entry["id"]] = DocumentResult(
            doc_id=entry["id"], sha256=summary.get("sha256", ""), trade_id=summary.get("trade_id"),
            extractions=extractions, normalized=normalized,
            merged=json.loads((d / "merged.json").read_text()) if (d / "merged.json").exists() else {},
            booking=json.loads((d / "booking.json").read_text()) if (d / "booking.json").exists() else {},
            findings=[Finding.model_validate(f) for f in json.loads((d / "findings.json").read_text())],
            document_lane=Lane(summary["document_lane"]), cost_usd=float(summary.get("cost_usd") or 0.0), out_dir=d,
            source=summary.get("source", ctx.source), parse_meta=summary.get("parse"), product_type=ptype,
            extras={"attested_hashes": summary.get("attested_hashes"), "cost_breakdown": summary.get("cost_breakdown")})
    prev = json.loads((run_dir / "summary.json").read_text()) if (run_dir / "summary.json").exists() else {}
    ev = scoring.score(manifest, results, ctx, golden)
    ev.resumed = prev.get("resumed")
    if ev.resumed and "prior_never_completed" not in ev.resumed and Path(ev.resumed["prior_run"]).exists():
        ev.resumed["prior_never_completed"] = never_completed_in(Path(ev.resumed["prior_run"]))   # older summaries lack it
    try:
        code = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=str(golden.parent)).stdout.strip()
    except OSError:
        code = "?"
    from datetime import date
    note = (f"> **Rescored {date.today().isoformat()}** from this run's stored artifacts with scoring code `{code}` (no model call, no new "
            f"reading; extractions re-normalized, findings and lanes as persisted). Previous report headline: "
            f"catch {prev.get('catch_strict', {}).get('hit', '?')}/{prev.get('catch_strict', {}).get('n', '?')}, false flags "
            f"{prev.get('false_flag_fields', {}).get('hit', '?')}/{prev.get('false_flag_fields', {}).get('n', '?')}.\n\n")
    text = scoring.render_markdown(ev)
    # Sections other commands appended (`cg ablation` writes the parse tax, `cg triage` the desk-query
    # spend) are not reproducible from the artifacts this function reads, so they are carried across
    # rather than silently dropped; the alternative is a rescored report that quietly loses evidence.
    prior_text = (run_dir / "eval_report.md").read_text() if (run_dir / "eval_report.md").exists() else ""
    carried = []
    for marker in ("## Parse tax", "**Desk queries drafted afterwards**"):
        if marker in prior_text and marker not in text:
            block = prior_text[prior_text.index(marker):]
            for later in ("## Parse tax", "**Desk queries drafted afterwards**"):
                if later != marker and later in block:
                    block = block[:block.index(later)]
            carried.append(block.rstrip())
    head, _, rest = text.partition("\n\n")
    body = head + "\n\n" + note + rest
    if carried:
        body = body.rstrip() + "\n\n" + "\n\n".join(carried) + "\n"
    (run_dir / "eval_report.md").write_text(body)
    (run_dir / "summary.json").write_text(json.dumps(ev.summary(), indent=2))
    return ev
