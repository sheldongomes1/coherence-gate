"""Extractor protocol and the S0 stub (LLD §9, ADR-8).

An extractor never raises: an API error, a refusal, or unparseable output all come back as
an Extraction whose fields are `Malformed`, and the outcome is written to the trace. This is
what makes "a malformed extraction is a finding, never a crash" true by construction.
"""
from __future__ import annotations

from typing import Protocol

from ..config import ModelPin
from ..schema_loader import Schema
from ..trace import Tracer
from ..types import Extraction, Family, Malformed


class Extractor(Protocol):
    family: Family
    pin: ModelPin

    def extract(self, document: str, *, doc_id: str, tracer: Tracer, schema: Schema) -> Extraction: ...


def all_malformed(family: Family, pin: ModelPin, schema: Schema, reason: str, raw: str = "") -> Extraction:
    return Extraction(family=family, model=pin.model,
                      fields={name: Malformed(reason=reason) for name in schema.names}, raw_text=raw)


class StubExtractor:
    """Makes no model call. Reports API_ERROR so the S0 eval scores 0 catches honestly."""

    def __init__(self, family: Family, pin: ModelPin) -> None:
        self.family, self.pin = family, pin

    def extract(self, document: str, *, doc_id: str, tracer: Tracer, schema: Schema) -> Extraction:
        with tracer.timed(doc_id=doc_id, step=f"extract:{self.family}", pin=self.pin) as u:
            u.outcome = "API_ERROR"
            u.detail = "stub extractor: no model call made (S0)"
        return all_malformed(self.family, self.pin, schema, reason="stub extractor: no model call made")
