"""Triage agent (LLD §11, ADR-17): for each TRIAGE finding, one Claude call that classifies
(advisory) and drafts the desk query from the finding, its citations and the booking field.
It never changes finding type or lane, and never sees the whole document."""
from __future__ import annotations

import json
from functools import lru_cache

import anthropic
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..config import ROOT, ModelPin
from ..schema_loader import load_schema
from ..trace import Tracer
from ..types import BookingLookup, Finding, TriageNote

PROMPT_VERSION = "triage_v1"
MEANING = {
    "MISMATCH": "both extractors agree on the term sheet value and it differs from the booking",
    "EXTRACTOR_DISAGREEMENT": "the two extraction models read different values; no arbitration is performed",
    "TS_ABSENT": "the term sheet does not state this field but the booking has a value",
    "BOOKING_ABSENT": "the term sheet states this field but the booking record has no value",
    "MALFORMED_EXTRACTION": "an extractor returned an invalid or uncitable value for this field",
    "RELATION_VIOLATION": "a deterministic cross-field arithmetic rule fails on the term sheet, the booking, or both (the detail shows the arithmetic)",
    "REFERENCE_INCONSISTENT": "the term sheet's description of the underlying index contradicts the index methodology (the 'booking value' shown is the methodology's rule)",
}
TRIAGE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["classification", "desk_query", "cited_clause", "booking_field", "booking_value", "rationale"],
    "properties": {
        "classification": {"type": "string", "enum": ["BOOKING_LIKELY_WRONG", "DOCUMENT_LIKELY_WRONG", "GENUINE_AMBIGUITY", "EXTRACTION_QUALITY"]},
        "desk_query": {"type": "string"}, "cited_clause": {"type": "string"},
        "booking_field": {"type": "string"}, "booking_value": {"type": "string"}, "rationale": {"type": "string"},
    },
}


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(ROOT / "prompts")), undefined=StrictUndefined,
                       autoescape=False, trim_blocks=True, lstrip_blocks=True)


class TriageAgent:
    def __init__(self, pin: ModelPin, effort: str = "medium") -> None:
        self.pin, self.effort = pin, effort
        self.client = anthropic.Anthropic()
        from ..schema_loader import all_schemas
        self.schemas = all_schemas()

    def render(self, f: Finding) -> str:
        if f.field.startswith("rel:"):
            desc = "cross-field arithmetic relation (deterministic)"
        elif f.field.startswith("ref:"):
            desc = "term-sheet claim about the underlying index, checked against the index methodology"
        else:
            desc = next((sp.description for sc in self.schemas.values() for sp in sc.fields if sp.name == f.field), "")
        return _env().get_template(f"{PROMPT_VERSION}.md").render(
            doc_id=f.doc_id, field=f.field, field_description=desc, finding_type=f.type,
            finding_type_meaning=MEANING.get(f.type, ""), severity=f.severity,
            ts_value="ABSENT" if f.ts_value is None else str(f.ts_value),
            booking_value="ABSENT" if f.booking_value is None else str(f.booking_value),
            detail=f.detail, citations=[c.text_span for c in f.citations])

    def triage(self, *, doc_id: str, document: str, findings: list[Finding], booking: BookingLookup,
               tracer: Tracer) -> None:
        for f in findings:
            with tracer.timed(doc_id=doc_id, step=f"triage:{f.field}", pin=self.pin) as u:
                try:
                    resp = self.client.messages.create(
                        model=self.pin.model, max_tokens=4000,
                        system="You draft precise desk queries for a structured-products documentation team.",
                        messages=[{"role": "user", "content": self.render(f)}],
                        output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": TRIAGE_SCHEMA}},
                    )
                except Exception as exc:  # noqa: BLE001
                    u.outcome, u.detail = "API_ERROR", f"{type(exc).__name__}: {str(exc)[:300]}"
                    f.triage = self._unavailable(f, u.detail)
                    continue
                u.model_version, u.prompt_tokens, u.output_tokens = resp.model, resp.usage.input_tokens, resp.usage.output_tokens
                if resp.stop_reason == "refusal":
                    u.outcome = "REFUSAL"
                    f.triage = self._unavailable(f, "model refusal")
                    continue
                text = next((b.text for b in resp.content if b.type == "text"), "")
                try:
                    f.triage = TriageNote(**json.loads(text))
                    u.outcome, u.detail = "OK", {"classification": f.triage.classification}
                except Exception as exc:  # noqa: BLE001 — malformed triage is an outcome
                    u.outcome, u.detail = "MALFORMED", str(exc)[:200]
                    f.triage = self._unavailable(f, f"malformed triage output: {exc}")

    @staticmethod
    def _unavailable(f: Finding, reason: str) -> TriageNote:
        return TriageNote(classification="EXTRACTION_QUALITY", desk_query=f"<triage unavailable: {reason}>",
                          cited_clause="", booking_field=f.field,
                          booking_value="ABSENT" if f.booking_value is None else str(f.booking_value),
                          rationale="triage agent did not return a valid note; finding still requires review")
