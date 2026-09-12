"""Closed vocabulary of the pipeline (LLD §3).

Everything downstream of the extractors is typed with these models. Two invariants are
enforced here, not in prompts:
  * a FieldExtraction is EXTRACTED (value + citation) or DECLARED_ABSENT (neither) — no
    third shape exists, so a silent blank cannot be represented;
  * a Finding always carries a type from a closed enum and a lane.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class Status(StrEnum):
    EXTRACTED = "EXTRACTED"
    DECLARED_ABSENT = "DECLARED_ABSENT"


class FindingType(StrEnum):
    CLEAN = "CLEAN"
    MISMATCH = "MISMATCH"
    EXTRACTOR_DISAGREEMENT = "EXTRACTOR_DISAGREEMENT"
    TS_ABSENT = "TS_ABSENT"
    BOOKING_ABSENT = "BOOKING_ABSENT"
    MALFORMED_EXTRACTION = "MALFORMED_EXTRACTION"  # ADR-7
    RELATION_VIOLATION = "RELATION_VIOLATION"      # v0.2 CS3: a deterministic cross-field rule failed
    REFERENCE_INCONSISTENT = "REFERENCE_INCONSISTENT"  # v0.2 CS4: a term-sheet claim about the index contradicts its methodology


class Severity(StrEnum):
    critical = "critical"
    minor = "minor"


class Lane(StrEnum):
    AUTO_CLEAR = "AUTO_CLEAR"
    TRIAGE = "TRIAGE"


class Family(StrEnum):
    gemini = "gemini"
    claude = "claude"


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)
    text_span: str
    # Recomputed by schema_guard from the source document (ADR-3). (-1, -1) until then.
    char_range: tuple[int, int] = (-1, -1)


class FieldExtraction(BaseModel):
    """One field as returned by an extractor, after the guard. `raw_value` keeps what the
    model wrote; `value` is the same thing until normalize.py replaces it."""

    status: Status
    value: Any | None = None
    citation: Citation | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _pairing(self) -> "FieldExtraction":
        if self.status is Status.EXTRACTED and (self.value is None or self.citation is None):
            raise ValueError("EXTRACTED requires both value and citation")
        if self.status is Status.DECLARED_ABSENT and (
            self.value is not None or self.citation is not None
        ):
            raise ValueError("DECLARED_ABSENT must carry neither value nor citation")
        return self


class Malformed(BaseModel):
    """Marker for a field the guard rejected. Replaces the FieldExtraction for that field."""

    reason: str
    raw: Any | None = None


class Extraction(BaseModel):
    family: Family
    model: str
    model_version: str | None = None
    fields: dict[str, FieldExtraction | Malformed]
    raw_text: str = ""


class NormalizedField(BaseModel):
    key: str
    value: Any | None
    absent: bool
    malformed: str | None = None  # reason, if the source field or its normalization failed
    source: FieldExtraction | Malformed


class MergedField(BaseModel):
    key: str
    agree: bool
    value: Any | None
    absent: bool
    a: NormalizedField
    b: NormalizedField
    malformed_families: list[Family] = []

    @property
    def citations(self) -> list[Citation]:
        out: list[Citation] = []
        for nf in (self.a, self.b):
            if isinstance(nf.source, FieldExtraction) and nf.source.citation:
                out.append(nf.source.citation)
        return out


class TriageNote(BaseModel):
    classification: Literal[
        "BOOKING_LIKELY_WRONG", "DOCUMENT_LIKELY_WRONG", "GENUINE_AMBIGUITY", "EXTRACTION_QUALITY"
    ]
    desk_query: str
    cited_clause: str
    booking_field: str
    booking_value: str
    rationale: str


class Finding(BaseModel):
    id: str
    doc_id: str
    field: str
    type: FindingType
    severity: Severity
    ts_value: Any | None = None
    booking_value: Any | None = None
    citations: list[Citation] = []
    detail: str = ""
    lane: Lane = Lane.TRIAGE
    triage: TriageNote | None = None


class BookingLookup(BaseModel):
    trade_id: str
    found: bool
    record: dict[str, Any] | None = None
    transport: Literal["mcp-stdio", "direct"]
