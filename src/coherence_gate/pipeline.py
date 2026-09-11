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
from .schema_loader import Schema
from .trace import Tracer
from .types import Extraction, Family, FieldExtraction, Finding, Lane, NormalizedField, Status


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
    extras: dict = field(default_factory=dict)


def _agreed_trade_id(norm: dict[Family, dict[str, NormalizedField]]) -> str | None:
    vals = {nf["trade_id"].value for nf in norm.values() if not nf["trade_id"].malformed and not nf["trade_id"].absent}
    return vals.pop() if len(vals) == 1 else None


def run_document(doc_path: Path, ctx: RunContext, trade_id: str | None = None) -> DocumentResult:
    doc_id = doc_path.stem
    text = doc_path.read_text()
    sha = hashlib.sha256(text.encode()).hexdigest()
    ctx.tracer.step(doc_id=doc_id, step="load", outcome="OK", detail={"sha256": sha, "chars": len(text)})

    # 1. dual-family extraction, concurrently (independent by design — neither sees the other)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {fam: pool.submit(ex.extract, text, doc_id=doc_id, tracer=ctx.tracer, schema=ctx.schema)
                for fam, ex in ctx.extractors.items()}
        extractions = {fam: f.result() for fam, f in futs.items()}

    # 2. normalize (code), 3. merge (code)
    norm = {fam: normalize.normalize_extraction(ext, ctx.schema) for fam, ext in extractions.items()}
    merged = merger.merge(norm[Family.gemini], norm[Family.claude], ctx.schema)
    ctx.tracer.step(doc_id=doc_id, step="merge", outcome="OK",
                    detail={"agree": sum(m.agree for m in merged.values()), "keys": len(merged)})

    # 4. booking truth, only through the tool
    tid = trade_id or _agreed_trade_id(norm)
    with ctx.tracer.timed(doc_id=doc_id, step="booking_lookup") as u:
        lookup = ctx.booking.lookup(tid or "")
        u.outcome = "FOUND" if lookup.found else "NOT_FOUND"
        u.detail = {"trade_id": tid, "transport": lookup.transport}

    # 5. compare (code), 6. lanes (code)
    findings = comparator.compare(doc_id, merged, lookup, ctx.schema)
    findings, doc_lane = lanes.assign(findings)
    ctx.tracer.step(doc_id=doc_id, step="compare", outcome=doc_lane,
                    detail={t: sum(f.type == t for f in findings) for t in {f.type for f in findings}})

    # 7. triage (model, only for TRIAGE findings; a clean document makes no further calls)
    if ctx.triage is not None:
        ctx.triage.triage(doc_id=doc_id, document=text, findings=[f for f in findings if f.lane is Lane.TRIAGE],
                          booking=lookup, tracer=ctx.tracer)

    result = DocumentResult(doc_id=doc_id, sha256=sha, trade_id=tid,
                            extractions={str(k): v for k, v in extractions.items()},
                            normalized={str(k): v for k, v in norm.items()},
                            merged={k: m.model_dump() for k, m in merged.items()},
                            booking=lookup.model_dump(), findings=findings, document_lane=doc_lane,
                            cost_usd=ctx.tracer.total_cost(doc_id))
    persist(result, ctx)
    return result


def persist(r: DocumentResult, ctx: RunContext) -> None:
    d = ctx.out_dir / r.doc_id
    d.mkdir(parents=True, exist_ok=True)
    for fam, ext in r.extractions.items():
        (d / f"extraction_{fam}.json").write_text(ext.model_dump_json(indent=2))
    (d / "merged.json").write_text(json.dumps(r.merged, indent=2, default=str))
    (d / "booking.json").write_text(json.dumps(r.booking, indent=2, default=str))
    (d / "findings.json").write_text(json.dumps([f.model_dump() for f in r.findings], indent=2, default=str))
    auto = [f.model_dump() for f in r.findings if f.lane is Lane.AUTO_CLEAR]
    (d / "auto_clear.json").write_text(json.dumps(auto, indent=2, default=str))
    (d / "summary.json").write_text(json.dumps({
        "doc_id": r.doc_id, "sha256": r.sha256, "trade_id": r.trade_id, "document_lane": r.document_lane,
        "cost_usd": r.cost_usd, "n_auto_clear": len(auto), "n_triage": len(r.findings) - len(auto)}, indent=2))
    r.out_dir = d
