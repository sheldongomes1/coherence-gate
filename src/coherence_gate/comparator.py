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


def _within_tolerance(spec, ts_val: Any, bk_val: Any, schema: Schema) -> bool:
    """Schema-declared per-field tolerance (v2 `tolerances` block), e.g.
    {"autocall_observation_dates": {"type": "date_days", "days": 3}}. Absent -> exact only.
    A tolerance is a versioned judgment artifact: it is applied in its own commit and re-measured."""
    tol = (getattr(schema, "tolerances", None) or {}).get(spec.name)
    if not tol or tol.get("type") != "date_days":
        return False
    from datetime import date
    days = int(tol.get("days", 0))

    def d(x):
        return date.fromisoformat(str(x))
    try:
        if isinstance(ts_val, list) and isinstance(bk_val, list):
            return len(ts_val) == len(bk_val) and all(abs((d(a) - d(b)).days) <= days for a, b in zip(ts_val, bk_val))
        return abs((d(ts_val) - d(bk_val)).days) <= days
    except (ValueError, TypeError):
        return False


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
        bk_note = ""
        try:
            bk = normalize_value(spec, bk_raw, context=record) if bk_raw is not None else None
        except NormalizeError as exc:
            bk = None
            bk_note = f"booking value {bk_raw!r} not normalizable ({exc}); "

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
            findings.append(Finding(**base, type=FindingType.BOOKING_ABSENT if bk_note else FindingType.CLEAN,
                                    booking_value=bk_raw if bk_note else None, detail=bk_note + ("term sheet absent" if bk_note else "absent in both")))
        elif bk is None:
            findings.append(Finding(**base, type=FindingType.BOOKING_ABSENT, ts_value=m.value, booking_value=bk_raw if bk_note else None,
                                    detail=bk_note + f"term sheet has {_fmt(m.value)}; booking has no usable {key}"))
        elif values_equal(m.value, bk):
            findings.append(Finding(**base, type=FindingType.CLEAN, ts_value=m.value, booking_value=bk, detail="match"))
        elif _within_tolerance(spec, m.value, bk, schema):
            findings.append(Finding(**base, type=FindingType.CLEAN, ts_value=m.value, booking_value=bk,
                                    detail=f"within declared tolerance {schema.tolerances[key]} (schema v{schema.version})"))
        else:
            findings.append(Finding(**base, type=FindingType.MISMATCH, ts_value=m.value, booking_value=bk,
                                    detail=f"TS {_fmt(m.value)} ≠ booking {_fmt(bk)}"))
    return findings


# ----------------------------------------------------------------------------- relations (v0.2 CS3)
def _side_values(keys: list[str], merged: dict[str, MergedField], record: dict | None, schema: Schema):
    """Return (ts_values, booking_values) dicts for the keys, or None entries where not evaluable."""
    ts, bk = {}, {}
    for k in keys:
        m = merged.get(k)
        ts[k] = m.value if (m and m.agree and not m.absent and not m.malformed_families) else None
        raw = record.get(k) if record else None
        try:
            bk[k] = normalize_value(schema.spec(k), raw) if raw is not None else None
        except NormalizeError:
            bk[k] = None
    return ts, bk


def check_relations(doc_id: str, merged: dict[str, MergedField], booking: BookingLookup, schema: Schema) -> list[Finding]:
    """Deterministic cross-field rules from the schema's `relations` list. Each relation yields
    exactly one finding: CLEAN (holds on both sides, or not evaluable — stated in detail) or
    RELATION_VIOLATION (fails on the term sheet, the booking, or both)."""
    from decimal import Decimal
    out: list[Finding] = []
    record = booking.record if booking.found else None
    for rel in schema.relations:
        if rel.get("type") != "product_equals":
            continue
        keys = [f["field"] for f in rel["factors"]] + [rel["equals"]]
        ts, bk = _side_values(keys, merged, record, schema)
        sev = Severity.critical if rel.get("critical", True) else Severity.minor
        tol = Decimal(str(rel.get("tolerance_abs", "0")))
        fid = f"rel:{rel['name']}"
        base = dict(id=f"{doc_id}:{fid}", doc_id=doc_id, field=fid, severity=sev)

        def evaluate(vals: dict) -> tuple[str, bool | None]:
            if any(vals[k] is None for k in keys):
                missing = [k for k in keys if vals[k] is None]
                return f"not evaluable ({', '.join(missing)} unavailable)", None
            prod = Decimal(1)
            terms = []
            for f in rel["factors"]:
                v = Decimal(str(vals[f["field"]])) * Decimal(str(f.get("scale", "1")))
                prod *= v
                terms.append(f"{vals[f['field']]}{'×' + str(f['scale']) if f.get('scale') else ''}")
            target = Decimal(str(vals[rel["equals"]]))
            ok = abs(prod - target) <= tol
            from .normalize import _plain
            return f"{' × '.join(terms)} = {_plain(prod):,} vs {rel['equals']} {_plain(target):,}", ok

        ts_detail, ts_ok = evaluate(ts)
        bk_detail, bk_ok = evaluate(bk)
        failed = [side for side, ok in (("term sheet", ts_ok), ("booking", bk_ok)) if ok is False]
        detail = f"{rel['name']}: term sheet [{ts_detail}]; booking [{bk_detail}]"
        # the relation's evidence is the citations of its constituent fields (B3)
        cites = [c for k in keys if merged.get(k) for c in merged[k].citations]
        base["citations"] = cites
        if failed:
            out.append(Finding(**base, type=FindingType.RELATION_VIOLATION,
                               ts_value=ts.get(rel["equals"]), booking_value=bk.get(rel["equals"]),
                               detail=f"violated on {', '.join(failed)} — " + detail))
        elif ts_ok is None and bk_ok is None:
            out.append(Finding(**base, type=FindingType.NOT_EVALUABLE, detail="not evaluable on either side — " + detail))
        else:
            out.append(Finding(**base, type=FindingType.CLEAN, ts_value=ts.get(rel["equals"]), booking_value=bk.get(rel["equals"]),
                               detail=detail + ("" if ts_ok is not None and bk_ok is not None else " (one side not evaluable; the other holds)")))
    return out
