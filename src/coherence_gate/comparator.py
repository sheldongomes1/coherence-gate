"""Deterministic comparator (LLD §6). Tolerance table v1: everything exact.

  merged disagree            -> EXTRACTOR_DISAGREEMENT / MALFORMED_EXTRACTION
  absent   / booking present -> TS_ABSENT
  absent   / booking absent  -> CLEAN
  value    / booking missing -> BOOKING_ABSENT
  value    / equal           -> CLEAN
  value    / different       -> MISMATCH
  booking record not found   -> BOOKING_ABSENT on every key
Booking values pass through the same normalizer as extracted values before comparison.
"""
from __future__ import annotations

from typing import Any

from .normalize import NormalizeError, normalize_value, values_equal
from .schema_loader import Schema
from .types import BookingLookup, Finding, FindingType, MergedField, Severity

TOLERANCE_V1 = {"date": "exact", "decimal": "exact", "iso4217": "exact", "ticker": "exact",
                "enum": "exact", "bool": "exact", "list": "exact_ordered", "str": "exact"}


def _fmt(v: Any) -> str:
    return "ABSENT" if v is None else str(v)


def compare(doc_id: str, merged: dict[str, MergedField], booking: BookingLookup, schema: Schema) -> list[Finding]:
    findings: list[Finding] = []
    record = booking.record if booking.found else None
    for key in schema.comparison_keys:
        m = merged[key]
        spec = schema.spec(key)
        sev = Severity.critical if spec.critical else Severity.minor
        base = dict(id=f"{doc_id}:{key}", doc_id=doc_id, field=key, severity=sev, citations=m.citations)
        bk_raw = record.get(key) if record is not None else None
        try:
            bk = normalize_value(spec, bk_raw) if bk_raw is not None else None
        except NormalizeError as exc:
            bk = None
            base["detail"] = f"booking value not normalizable: {exc}"

        if m.malformed_families:
            fams = ",".join(m.malformed_families)
            reasons = "; ".join(f"{nf.key}[{fam}]: {nf.malformed}" for fam, nf in zip(("gemini", "claude"), (m.a, m.b)) if nf.malformed)
            findings.append(Finding(**base, type=FindingType.MALFORMED_EXTRACTION, booking_value=bk,
                                    detail=f"malformed extraction from {fams}: {reasons}"))
        elif not m.agree:
            findings.append(Finding(**base, type=FindingType.EXTRACTOR_DISAGREEMENT, booking_value=bk,
                                    detail=f"gemini={_fmt(None if m.a.absent else m.a.value)} vs claude={_fmt(None if m.b.absent else m.b.value)}"))
        elif record is None:
            findings.append(Finding(**base, type=FindingType.BOOKING_ABSENT, ts_value=m.value,
                                    detail=f"booking record for trade_id '{booking.trade_id}' not found"))
        elif m.absent and bk is not None:
            findings.append(Finding(**base, type=FindingType.TS_ABSENT, booking_value=bk,
                                    detail=f"term sheet declares {key} absent; booking has {_fmt(bk)}"))
        elif m.absent and bk is None:
            findings.append(Finding(**base, type=FindingType.CLEAN, detail="absent in both"))
        elif bk is None:
            findings.append(Finding(**base, type=FindingType.BOOKING_ABSENT, ts_value=m.value,
                                    detail=f"term sheet has {_fmt(m.value)}; booking has no {key}"))
        elif values_equal(m.value, bk):
            findings.append(Finding(**base, type=FindingType.CLEAN, ts_value=m.value, booking_value=bk, detail="match"))
        else:
            findings.append(Finding(**base, type=FindingType.MISMATCH, ts_value=m.value, booking_value=bk,
                                    detail=f"TS {_fmt(m.value)} ≠ booking {_fmt(bk)}"))
    return findings
