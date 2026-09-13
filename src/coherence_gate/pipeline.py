"""One document through the gate (LLD §1). Each step is a tool-shaped function that writes
one trace line; the pipeline is a fixed sequence, not a model-driven loop (HLD §8)."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import comparator, lanes, merger, normalize
from .booking.client import BookingClient
from .config import Config
from .extract.base import Extractor
from .schema_loader import Schema, all_schemas, detect_product
from .trace import Tracer
from .types import Extraction, Family, FieldExtraction, Finding, FindingType, Lane, Malformed, NormalizedField, Severity, Status, TriageNote


@dataclass
class RunContext:
    run_id: str
    out_dir: Path
    config: Config
    tracer: Tracer
    schema: Schema
    booking: BookingClient
    extractors: dict[Family, Extractor]
    triage: Any | None = None  # TriageAgent (S3)
    schemas: dict[str, Schema] = field(default_factory=all_schemas)  # product_type -> schema (CS3)
    reference: Any | None = None  # reference.ReferenceRules when the Versa lane is on (CS4)
    reference_wanted: bool = False  # the lane was requested; if reference is None the load failed (traced per document)
    source: str = "txt"         # "pdf" -> parse stage; "txt" -> read the canonical .txt (ablation / fallback)
    parser: Any | None = None   # ingest.Parser when source == "pdf"
    parsed_dir: Path | None = None


@dataclass
class DocumentResult:
    doc_id: str
    sha256: str
    trade_id: str | None
    extractions: dict[str, Extraction]
    normalized: dict[str, dict[str, NormalizedField]]
    merged: dict
    booking: dict
    findings: list[Finding]
    document_lane: Lane
    cost_usd: float = 0.0
    out_dir: Path | None = None
    source: str = "txt"
    parse_meta: dict | None = None
    product_type: str = "note"
    extras: dict = field(default_factory=dict)


def booking_hash(record: dict | None, keys: list[str] | None = None) -> str | None:
    """Canonical hash of the booking's TERMS: the projection of the record onto the schema's
    comparison keys (the fields the document governs), sorted, compact JSON.

    Why a projection: a live booking changes hundreds of times a day (fixings, MTM, accruals,
    lifecycle flags). None of that changes what the term sheet promised, so none of it may
    invalidate an attestation. Only a change to a compared term does. With a booking system
    that versions trade terms separately from events, bind to that terms-version id instead."""
    if record is None:
        return None
    proj = {k: record[k] for k in (keys or list(record)) if k in record} if keys else dict(record)
    return hashlib.sha256(json.dumps(proj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _wholesale_failures(extractions: dict[Family, Extraction]) -> dict[Family, str]:
    """Families whose EVERY field is Malformed with one shared reason (API error, timeout, refusal, non-JSON)."""
    out: dict[Family, str] = {}
    for fam, ext in extractions.items():
        reasons = {v.reason for v in ext.fields.values() if isinstance(v, Malformed)}
        if len(reasons) == 1 and all(isinstance(v, Malformed) for v in ext.fields.values()):
            out[fam] = reasons.pop()
    return out


def _agreed_trade_id(norm: dict[Family, dict[str, NormalizedField]]) -> str | None:
    vals = {nf["trade_id"].value for nf in norm.values() if not nf["trade_id"].malformed and not nf["trade_id"].absent}
    return vals.pop() if len(vals) == 1 else None


def run_document(doc_path: Path, ctx: RunContext, trade_id: str | None = None,
                 pdf_path: Path | None = None, product_type: str | None = None) -> DocumentResult:
    """`doc_path` is the canonical .txt; when ctx.source == "pdf", `pdf_path` is parsed and the
    parsed markdown becomes the source text every citation anchors into (CS2 citation chain)."""
    doc_id = doc_path.stem
    mark = ctx.tracer.mark()
    parse_meta = None
    if ctx.source == "pdf":
        from .ingest import parse_document
        assert pdf_path is not None and ctx.parser is not None and ctx.parsed_dir is not None
        with ctx.tracer.timed(doc_id=doc_id, step="parse") as u:
            try:
                res, cached = parse_document(doc_id, pdf_path, ctx.parser, ctx.parsed_dir)
            except Exception as exc:  # noqa: BLE001 — a parse failure is an outcome; fall back to the .txt
                u.outcome, u.detail = "PARSE_ERROR", f"{type(exc).__name__}: {str(exc)[:200]}"
                res, cached = None, False
            if res is not None:
                u.outcome = "CACHED" if cached else "OK"
                u.model_version = f"{res.meta.get('vendor')}:{res.meta.get('mode', '')}"
                u.detail = {"vendor": res.meta.get("vendor"), "job_id": res.meta.get("job_id"),
                            "parse_latency_ms": res.meta.get("latency_ms"), "cost_usd": res.meta.get("cost_usd"),
                            "pdf_sha256": res.meta.get("pdf_sha256"), "markdown_sha256": res.meta.get("markdown_sha256")}
        if res is not None:
            text, parse_meta = res.markdown, res.meta
        else:
            text, parse_meta = doc_path.read_text(), {"vendor": "none", "fallback": "txt", "reason": "parse error"}
    else:
        text = doc_path.read_text()
    sha = hashlib.sha256(text.encode()).hexdigest()
    ctx.tracer.step(doc_id=doc_id, step="load", outcome="OK",
                    detail={"source": ctx.source, "sha256": sha, "chars": len(text)})

    # 0. product detection (deterministic keywords) unless given; selects the pluggable schema
    if product_type is None:
        product_type, how = detect_product(text)
    else:
        how = "given"
    schema = ctx.schemas[product_type]
    ctx.tracer.step(doc_id=doc_id, step="detect_product", outcome=product_type, detail={"by": how, "schema": schema.version})

    # 1. dual-family extraction, concurrently (independent by design — neither sees the other)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {fam: pool.submit(ex.extract, text, doc_id=doc_id, tracer=ctx.tracer, schema=schema)
                for fam, ex in ctx.extractors.items()}
        extractions = {fam: f.result() for fam, f in futs.items()}
    return _complete(doc_id, text, sha, product_type, schema, extractions, parse_meta, doc_path, ctx, trade_id, mark=mark)


def recheck_document(doc_id: str, ctx: RunContext, prior_dir: Path, trade_id: str | None = None,
                     product_type: str | None = None, carry_prior_cost: bool = False) -> DocumentResult:
    """Re-check a document against the CURRENT booking WITHOUT re-extracting: the stored extractions
    of both families are attested to the document's hash, and the document has not changed, so
    only the deterministic steps (normalize, merge, compare, relations, reference, lanes) run
    again, plus triage for findings that are new since the prior run. Seconds, not minutes.
    Falls back to a full run if the stored extractions or the attested document are missing or
    the document hash moved."""
    prior = Path(prior_dir) / doc_id
    mark = ctx.tracer.mark()
    summary = json.loads((prior / "summary.json").read_text()) if (prior / "summary.json").exists() else {}
    att = summary.get("attested_hashes") or {}
    doc_path = Path(att.get("document_path", "")) if att.get("document_path") else None
    if not doc_path or not doc_path.exists() or not all((prior / f"extraction_{f}.json").exists() for f in ("gemini", "claude")):
        raise FileNotFoundError(f"no reusable extraction for {doc_id} in {prior_dir}")
    text = doc_path.read_text()
    sha = hashlib.sha256(text.encode()).hexdigest()
    if att.get("document_sha256") and att["document_sha256"] != sha:
        raise ValueError(f"document {doc_id} changed since it was extracted; a full re-read is required")
    extractions = {Family(f): Extraction.model_validate(json.loads((prior / f"extraction_{f}.json").read_text()))
                   for f in ("gemini", "claude")}
    product_type = product_type or summary.get("product_type") or "note"
    schema = ctx.schemas[product_type]
    prior_cost = float(summary.get("cost_usd") or 0.0) if carry_prior_cost else 0.0
    ctx.tracer.step(doc_id=doc_id, step="load", outcome="REUSED_EXTRACTION",
                    detail={"source": summary.get("source", "txt"), "sha256": sha, "prior_run": str(prior_dir),
                            "prior_cost_usd": prior_cost if carry_prior_cost else None,
                            "reason": "document unchanged; extractions attested to this hash"})
    for fam, e in extractions.items():
        ctx.tracer.step(doc_id=doc_id, step=f"extract:{fam}", outcome="CACHED", model=e.model, model_version=e.model_version)
    prior_findings = {(f["field"], f["type"], str(f.get("ts_value")), str(f.get("booking_value"))): f
                      for f in json.loads((prior / "findings.json").read_text())} if (prior / "findings.json").exists() else {}
    return _complete(doc_id, text, sha, product_type, schema, extractions, summary.get("parse"), doc_path, ctx, trade_id,
                     prior_findings=prior_findings, mark=mark, extra_cost=prior_cost)


def _complete(doc_id: str, text: str, sha: str, product_type: str, schema: Schema, extractions: dict[Family, Extraction],
              parse_meta: dict | None, doc_path: Path, ctx: RunContext, trade_id: str | None,
              prior_findings: dict | None = None, mark: int = 0, extra_cost: float = 0.0) -> DocumentResult:
    """Everything after extraction: deterministic steps, triage, persist. `mark` is the tracer
    position where this pass started, so the persisted cost is this pass's cost only; `extra_cost`
    is the cost of the reused extraction when an eval resumes (the number the reader wants is what
    this result cost, wherever the calls ran)."""

    # 2. normalize (code), 3. merge (code)
    norm = {fam: normalize.normalize_extraction(ext, schema) for fam, ext in extractions.items()}
    merged = merger.merge(norm[Family.gemini], norm[Family.claude], schema)
    ctx.tracer.step(doc_id=doc_id, step="merge", outcome="OK",
                    detail={"agree": sum(m.agree for m in merged.values()), "keys": len(merged)})

    # 4. booking truth, only through the tool
    tid = trade_id or _agreed_trade_id(norm)
    with ctx.tracer.timed(doc_id=doc_id, step="booking_lookup") as u:
        lookup = ctx.booking.lookup(tid or "")
        u.outcome = "FOUND" if lookup.found else "NOT_FOUND"
        u.detail = {"trade_id": tid, "transport": lookup.transport}

    # 5. compare (code), 6. lanes (code)
    findings = comparator.compare(doc_id, merged, lookup, schema)
    findings += comparator.check_relations(doc_id, merged, lookup, schema)
    if ctx.reference is not None:
        from .reference import check_reference
        ref_findings = check_reference(doc_id, merged, ctx.reference, schema)
        findings += ref_findings
        ctx.tracer.step(doc_id=doc_id, step="reference_check", outcome="OK" if ref_findings else "NO_CLAIMS",
                        detail={t: sum(f.type == t for f in ref_findings) for t in {f.type for f in ref_findings}})
    elif getattr(ctx, "reference_wanted", False):
        # the lane was requested but the methodology could not be loaded: say so on every document,
        # and mark the index claims NOT_EVALUABLE rather than silently dropping the check
        claims = [k for k in merged if k.startswith("index_") and not merged[k].absent]
        for k in claims:
            findings.append(Finding(id=f"{doc_id}:ref:{k}", doc_id=doc_id, field=f"ref:{k}", type=FindingType.NOT_EVALUABLE,
                                    severity=Severity.critical, ts_value=merged[k].value, detail="reference lane unavailable (methodology not loaded); claim not checked"))
        ctx.tracer.step(doc_id=doc_id, step="reference_check", outcome="UNAVAILABLE", detail={"claims_not_checked": len(claims)})
    findings, doc_lane = lanes.assign(findings)
    ctx.tracer.step(doc_id=doc_id, step="compare", outcome=doc_lane,
                    detail={t: sum(f.type == t for f in findings) for t in {f.type for f in findings}})

    # reuse prior desk queries for findings that did not change (recheck path); triage only the new ones
    if prior_findings:
        for f in findings:
            k = (f.field, f.type, str(f.ts_value), str(f.booking_value))
            if k in prior_findings and prior_findings[k].get("triage"):
                f.triage = TriageNote.model_validate(prior_findings[k]["triage"])

    # 7. triage (model, only for TRIAGE findings; a clean document makes no further calls).
    #    A wholesale extractor failure (timeout, API error, refusal, non-JSON) is a technical
    #    event, not a documentary question: code writes ONE note for every affected field and
    #    no model is asked to explain it (ADR-18).
    wholesale = _wholesale_failures(extractions)
    if wholesale:
        reason = "; ".join(f"{fam}: {why}" for fam, why in wholesale.items())
        for f in findings:
            if f.type is FindingType.MALFORMED_EXTRACTION and f.lane is Lane.TRIAGE:
                f.triage = TriageNote(classification="EXTRACTION_QUALITY",
                                      desk_query=f"No desk action: extraction failed wholesale ({reason}). "
                                                 "This is a technical failure, not a document/booking discrepancy. Rerun the gate.",
                                      cited_clause="", booking_field=f.field,
                                      booking_value="ABSENT" if f.booking_value is None else str(f.booking_value),
                                      rationale="every field of one extractor failed for the same technical reason")
        ctx.tracer.step(doc_id=doc_id, step="triage", outcome="SKIPPED_WHOLESALE_FAILURE", detail=reason)
    if ctx.triage is not None:
        ctx.triage.triage(doc_id=doc_id, document=text,
                          findings=[f for f in findings if f.lane is Lane.TRIAGE and f.triage is None],
                          booking=lookup, tracer=ctx.tracer)

    # CS7c: bind this attestation to what was read — the source text and the canonical booking.
    # desk_view recomputes both at page time; if either moved, the row is STALE.
    attested = {"document_path": str((ctx.parsed_dir / f"{doc_id}.md") if (ctx.source == "pdf" and parse_meta and parse_meta.get("vendor") != "none") else doc_path),
                "document_sha256": sha, "booking_trade_id": tid,
                "booking_terms_keys": schema.comparison_keys,
                "booking_sha256": booking_hash(lookup.record, schema.comparison_keys) if lookup.found else None}
    result = DocumentResult(doc_id=doc_id, sha256=sha, trade_id=tid,
                            extractions={str(k): v for k, v in extractions.items()},
                            normalized={str(k): v for k, v in norm.items()},
                            merged={k: m.model_dump() for k, m in merged.items()},
                            booking=lookup.model_dump(), findings=findings, document_lane=doc_lane,
                            cost_usd=round(ctx.tracer.total_cost(doc_id, since=mark) + extra_cost, 6), source=ctx.source, parse_meta=parse_meta,
                            product_type=product_type, extras={"attested_hashes": attested})
    persist(result, ctx)
    return result


def _write(path: Path, text: str) -> None:
    """Atomic write (temp file + rename) so a reader never sees a half-written artifact."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def persist(r: DocumentResult, ctx: RunContext) -> None:
    d = ctx.out_dir / r.doc_id
    d.mkdir(parents=True, exist_ok=True)
    for fam, ext in r.extractions.items():
        _write(d / f"extraction_{fam}.json", ext.model_dump_json(indent=2))
    _write(d / "merged.json", json.dumps(r.merged, indent=2, default=str))
    _write(d / "booking.json", json.dumps(r.booking, indent=2, default=str))
    _write(d / "findings.json", json.dumps([f.model_dump() for f in r.findings], indent=2, default=str))
    _write(d / "triage.json", json.dumps([{**f.model_dump(), "triage": f.triage.model_dump() if f.triage else None}
                                               for f in r.findings if f.lane is Lane.TRIAGE], indent=2, default=str))
    auto = [f.model_dump() for f in r.findings if f.lane is Lane.AUTO_CLEAR]
    _write(d / "auto_clear.json", json.dumps(auto, indent=2, default=str))
    _write(d / "summary.json", json.dumps({
        "doc_id": r.doc_id, "sha256": r.sha256, "trade_id": r.trade_id, "document_lane": r.document_lane,
        "cost_usd": r.cost_usd, "n_auto_clear": len(auto), "n_triage": len(r.findings) - len(auto),
        "source": r.source, "parse": r.parse_meta, "product_type": r.product_type,
        "attested_hashes": r.extras.get("attested_hashes")}, indent=2, default=str))
    r.out_dir = d
