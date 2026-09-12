"""Versa reference lane.

load_reference: parse the methodology PDF (same ingest stage, cached), extract it with BOTH
families against schema/index_methodology_v1.json using prompts/reference_v1.md, merge
deterministically. Extractions are cached under golden/reference/ keyed by (markdown sha,
prompt sha, model): the rulebook does not change between runs, so re-extracting it buys
nothing; the trace says CACHED when the cache was used.

check_reference: for each methodology field that maps to a term-sheet claim (`claim`):
  binding=rule     -> compare; REFERENCE_INCONSISTENT if the claim contradicts the rule
  binding=default  -> CLEAN, "methodology default; the index-specific document may override"
  binding=deferred -> CLEAN, "deferred to the index-specific document; not checkable here"
  rule not evaluable (families disagreed / malformed / absent) -> CLEAN with the reason
The return-type rule is special: the claim (Type I, Excess Return) is checked against the
methodology's type->treatment map. Findings use field "ref:<claim field>".
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import merger, normalize
from ..config import ROOT
from ..extract.base import prompt_sha
from ..schema_loader import SCHEMA_DIR, Schema, load_products, load_schema
from ..types import Extraction, Family, Finding, FindingType, MergedField, Severity

REF_DIR = ROOT / "golden" / "reference"


@dataclass
class ReferenceRules:
    schema: Schema
    merged: dict[str, MergedField]
    meta: dict[str, Any] = field(default_factory=dict)

    def value(self, key: str):
        """(value | None, status) where status in {'ok','absent','unusable'}."""
        m = self.merged.get(key)
        if m is None or m.malformed_families or not m.agree:
            return None, "unusable"
        if m.absent:
            return None, "absent"
        return m.value, "ok"

    @property
    def claims(self) -> list[dict]:
        return [dict(rf) for rf in self.schema.relations] if False else [
            {"ref_field": f.name, "claim": r.get("claim"), "binding": r.get("binding", "rule")}
            for f, r in ((f, _raw_field(self.schema, f.name)) for f in self.schema.fields) if r.get("claim")]


def _raw_field(schema: Schema, name: str) -> dict:
    raw = json.loads((SCHEMA_DIR / "index_methodology_v1.json").read_text())
    return next(f for f in raw["fields"] if f["name"] == name)


def _ref_config() -> dict:
    return load_products()["reference"]["index_methodology"]


def load_reference(ctx, *, use_cache: bool = True) -> ReferenceRules | None:
    """Parse + extract + merge the methodology. Returns None (and traces why) if unavailable."""
    from ..ingest import LocalParser, parse_document
    cfg = _ref_config()
    schema = load_schema(SCHEMA_DIR / cfg["schema"])
    pdf = ROOT / cfg["document"]
    if not pdf.exists():
        ctx.tracer.step(doc_id="REF", step="reference_load", outcome="MISSING", detail=str(pdf))
        return None
    parser = ctx.parser or LocalParser()
    with ctx.tracer.timed(doc_id="REF", step="parse") as u:
        try:
            res, cached = parse_document("methodology", pdf, parser, REF_DIR / "parsed")
            u.outcome = "CACHED" if cached else "OK"
            u.model_version = f"{res.meta.get('vendor')}:{res.meta.get('mode', '')}"
            u.detail = {"vendor": res.meta.get("vendor"), "job_id": res.meta.get("job_id"), "pages": res.meta.get("pages")}
        except Exception as exc:  # noqa: BLE001
            u.outcome, u.detail = "PARSE_ERROR", str(exc)[:200]
            return None
    text = res.markdown
    md_sha = hashlib.sha256(text.encode()).hexdigest()
    psha = prompt_sha(cfg["prompt"])
    extractions: dict[Family, Extraction] = {}
    for fam, ex in ctx.extractors.items():
        key = f"{fam}:{ex.pin.model}:{md_sha[:12]}:{psha}"
        cache = REF_DIR / f"extraction_{fam}.json"
        if use_cache and cache.exists():
            data = json.loads(cache.read_text())
            if data.get("key") == key:
                extractions[fam] = Extraction.model_validate(data["extraction"])
                ctx.tracer.step(doc_id="REF", step=f"extract:{fam}", outcome="CACHED", model=ex.pin.model,
                                model_version=data["extraction"].get("model_version"), detail={"cache_key": key})
                continue
        e = ex.extract(text, doc_id="REF", tracer=ctx.tracer, schema=schema, prompt_version=cfg["prompt"])
        extractions[fam] = e
        cache.write_text(json.dumps({"key": key, "extraction": e.model_dump(mode="json")}, indent=1, default=str))
    if len(extractions) < 2:
        return None
    norm = {fam: normalize.normalize_extraction(e, schema) for fam, e in extractions.items()}
    merged = merger.merge(norm[Family.gemini], norm[Family.claude], schema)
    agree = sum(m.agree for m in merged.values())
    ctx.tracer.step(doc_id="REF", step="reference_merge", outcome="OK",
                    detail={"agree": agree, "keys": len(merged), "markdown_sha256": md_sha,
                            "disagree": [k for k, m in merged.items() if not m.agree]})
    return ReferenceRules(schema=schema, merged=merged, meta={"markdown_sha256": md_sha, "prompt_sha": psha, "pdf": str(pdf)})


def rules_from_values(values: dict[str, Any]) -> ReferenceRules:
    """Build rules from canonical values (tests / fixtures): 'ABSENT' -> absent."""
    from ..types import Citation, FieldExtraction, NormalizedField, Status
    schema = load_schema(SCHEMA_DIR / "index_methodology_v1.json")
    merged = {}
    for f in schema.fields:
        v = values.get(f.name, "ABSENT")
        absent = v == "ABSENT"
        src = FieldExtraction(status=Status.DECLARED_ABSENT) if absent else \
            FieldExtraction(status=Status.EXTRACTED, value=v, citation=Citation(text_span=str(v)))
        val = None if absent else normalize.normalize_value(f, v)
        nf = NormalizedField(key=f.name, value=val, absent=absent, source=src)
        merged[f.name] = MergedField(key=f.name, agree=True, value=val, absent=absent, a=nf, b=nf)
    return ReferenceRules(schema=schema, merged=merged, meta={"source": "values"})


def check_reference(doc_id: str, ts_merged: dict[str, MergedField], ref: ReferenceRules, ts_schema: Schema) -> list[Finding]:
    """Term-sheet index claims vs the rulebook. Emits nothing for a document with no index section."""
    claim_keys = [k for k in ts_merged if k.startswith("index_")]
    if not claim_keys or all(ts_merged[k].absent for k in claim_keys if not ts_merged[k].malformed_families):
        return []
    out: list[Finding] = []
    raw = json.loads((SCHEMA_DIR / "index_methodology_v1.json").read_text())
    type_map = raw.get("return_type_map", {})

    def ts_claim(key: str):
        m = ts_merged.get(key)
        if m is None or m.malformed_families or not m.agree:
            return None, "unusable"
        if m.absent:
            return None, "absent"
        return m.value, "ok"

    def finding(claim_field: str, typ: FindingType, ts_val, ref_val, detail: str, sev: Severity) -> Finding:
        m = ts_merged.get(claim_field)
        return Finding(id=f"{doc_id}:ref:{claim_field}", doc_id=doc_id, field=f"ref:{claim_field}", type=typ, severity=sev,
                       ts_value=ts_val, booking_value=ref_val, citations=(m.citations if m else []), detail=detail)

    for rf in raw["fields"]:
        claim = rf.get("claim")
        if not claim:
            continue
        binding = rf.get("binding", "rule")
        sev = Severity.critical if rf.get("critical") else Severity.minor
        tv, ts_status = ts_claim(claim)
        if ts_status == "absent":
            continue  # the document makes no such claim
        if ts_status == "unusable":
            out.append(finding(claim, FindingType.CLEAN, None, None, "not evaluable: term-sheet claim unreadable (families disagree or malformed)", sev))
            continue
        rv, r_status = ref.value(rf["name"])
        if binding == "deferred" or r_status == "absent":
            out.append(finding(claim, FindingType.CLEAN, tv, None, f"deferred: the methodology defines {rf['name']} but fixes no value (index-specific document); not checkable here", sev))
            continue
        if binding == "default":
            out.append(finding(claim, FindingType.CLEAN, tv, rv, f"methodology default {rv}; the index-specific document may override — informational, not checked", sev))
            continue
        if r_status == "unusable":
            out.append(finding(claim, FindingType.CLEAN, tv, None, f"not evaluable: reference rule {rf['name']} unreadable (families disagree or malformed)", sev))
            continue
        if normalize.values_equal(tv, rv):
            out.append(finding(claim, FindingType.CLEAN, tv, rv, f"claim {tv} agrees with the methodology rule {rf['name']} = {rv}", sev))
        else:
            out.append(finding(claim, FindingType.REFERENCE_INCONSISTENT, tv, rv, f"term sheet claims {claim} = {tv}; methodology rule {rf['name']} = {rv}", sev))

    # return type -> treatment map (the claim is the PAIR (type, treatment))
    tt, s1 = ts_claim("index_return_type")
    tr, s2 = ts_claim("index_return_treatment")
    if s1 == "ok" and s2 == "ok":
        rule_field = type_map.get(str(tt))
        rv, r_status = ref.value(rule_field) if rule_field else (None, "absent")
        if r_status == "ok":
            if normalize.values_equal(tr, rv):
                out.append(finding("index_return_treatment", FindingType.CLEAN, tr, rv, f"{tt} is {rv} under the methodology; term sheet agrees", Severity.critical))
            else:
                out.append(finding("index_return_treatment", FindingType.REFERENCE_INCONSISTENT, tr, rv,
                                   f"term sheet calls a {tt} index '{tr}'; the methodology says {tt} is {rv}", Severity.critical))
        else:
            out.append(finding("index_return_treatment", FindingType.CLEAN, tr, None, f"not evaluable: methodology treatment for {tt} unreadable", Severity.critical))
    elif s2 == "ok" and s1 == "absent":
        out.append(finding("index_return_treatment", FindingType.CLEAN, tr, None, "not checkable: term sheet states a return treatment but no methodology Type", Severity.critical))
    return out
