"""Extractor protocol, shared prompt/schema plumbing, and the S0 stub (LLD §9, ADR-8).

An extractor never raises: an API error, a refusal, or unparseable output all come back as
an Extraction whose fields are `Malformed`, and the outcome is written to the trace. This is
what makes "a malformed extraction is a finding, never a crash" true by construction.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..config import ModelPin, ROOT
from ..schema_loader import Schema
from ..trace import Tracer
from ..types import Extraction, Family, Malformed
from .schema_guard import guard

PROMPTS = ROOT / "prompts"
PROMPT_VERSION = "extract_v1"

SYSTEM = ("You are a meticulous structured-products documentation analyst. You extract terms exactly as "
          "written, cite verbatim, and declare absence explicitly. You never compute, convert or guess.")


class Extractor(Protocol):
    family: Family
    pin: ModelPin

    def extract(self, document: str, *, doc_id: str, tracer: Tracer, schema: Schema,
                prompt_version: str | None = None) -> Extraction: ...


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(PROMPTS)), undefined=StrictUndefined, autoescape=False,
                       trim_blocks=True, lstrip_blocks=True)


def render_prompt(schema: Schema, document: str, version: str = PROMPT_VERSION) -> str:
    return _env().get_template(f"{version}.md").render(schema_table=schema.prompt_table(), document=document)


def prompt_sha(version: str = PROMPT_VERSION) -> str:
    import hashlib
    return hashlib.sha256((PROMPTS / f"{version}.md").read_bytes()).hexdigest()[:12]


def raw_extraction_json_schema(schema: Schema) -> dict[str, Any]:
    """Strict, flat, union-free JSON schema shared by both families (ADR-16).

    Shape: three maps keyed by field name — status, value, citation. Values are strings "as
    written" (arrays of strings for list fields); "" stands for null. Claude's structured-output
    compiler rejects 20 nested per-field objects ("compiled grammar too large") but accepts
    this shape; Gemini accepts either, so both families get the same contract."""
    def val(f):
        return {"type": "array", "items": {"type": "string"}} if f.base_type.startswith("list") else {"type": "string"}
    return {
        "type": "object", "additionalProperties": False, "required": ["status", "value", "citation"],
        "properties": {
            "status": {"type": "object", "additionalProperties": False, "required": schema.names,
                       "description": "EXTRACTED or DECLARED_ABSENT for every field.",
                       "properties": {f.name: {"type": "string", "enum": ["EXTRACTED", "DECLARED_ABSENT"]} for f in schema.fields}},
            "value": {"type": "object", "additionalProperties": False, "required": schema.names,
                      "description": "The term as written in the document; empty string (or empty array) when DECLARED_ABSENT.",
                      "properties": {f.name: {**val(f), "description": f"{f.type}. {f.description}"} for f in schema.fields}},
            "citation": {"type": "object", "additionalProperties": False, "required": schema.names,
                         "description": "Verbatim passage from the document containing the term; empty string when DECLARED_ABSENT.",
                         "properties": {f.name: {"type": "string"} for f in schema.fields}},
        },
    }


def finalize(*, family: Family, pin: ModelPin, schema: Schema, document: str, raw_text: str,
             model_version: str | None) -> tuple[Extraction, list[str]]:
    """Parse + guard. Returns the Extraction and the list of guard violations (for the trace)."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return all_malformed(family, pin, schema, reason=f"response is not JSON: {exc}", raw=raw_text,
                             model_version=model_version), [f"not JSON: {exc}"]
    fields, violations = guard(data, document, schema)
    return Extraction(family=family, model=pin.model, model_version=model_version, fields=fields,
                      raw_text=raw_text), violations


def all_malformed(family: Family, pin: ModelPin, schema: Schema, reason: str, raw: str = "",
                  model_version: str | None = None) -> Extraction:
    return Extraction(family=family, model=pin.model, model_version=model_version,
                      fields={name: Malformed(reason=reason) for name in schema.names}, raw_text=raw)


class StubExtractor:
    """Makes no model call. Reports API_ERROR so the S0 eval scores 0 catches honestly."""

    def __init__(self, family: Family, pin: ModelPin) -> None:
        self.family, self.pin = family, pin

    def extract(self, document: str, *, doc_id: str, tracer: Tracer, schema: Schema,
                prompt_version: str | None = None) -> Extraction:
        with tracer.timed(doc_id=doc_id, step=f"extract:{self.family}", pin=self.pin) as u:
            u.outcome = "API_ERROR"
            u.detail = "stub extractor: no model call made (S0)"
        return all_malformed(self.family, self.pin, schema, reason="stub extractor: no model call made")
