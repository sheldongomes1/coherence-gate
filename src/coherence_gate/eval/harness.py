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
        resumed = {"prior_run": str(resume), "reused": [], "re_extracted": []}
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
