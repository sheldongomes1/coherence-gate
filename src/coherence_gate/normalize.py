"""Canonical forms (LLD §4). STATUS: S0 passthrough — S1 replaces the bodies with the real
rules and unit tests. The interface is final: the pipeline, merger and comparator only call
`normalize_extraction` and `normalize_value`.
"""
from __future__ import annotations

from typing import Any

from .schema_loader import FieldSpec, Schema
from .types import Extraction, FieldExtraction, Malformed, NormalizedField, Status


class NormalizeError(ValueError):
    """Raised when a value cannot be brought to canonical form; becomes MALFORMED."""


def normalize_value(spec: FieldSpec, value: Any, *, context: dict[str, Any] | None = None) -> Any:
    """S0: identity. S1: dates→ISO, decimals→Decimal, tickers→upper, enums→canonical,
    coupon per-period→per-annum using context['coupon_rate_basis'] and ['coupon_frequency']."""
    return value


def normalize_extraction(ext: Extraction, schema: Schema) -> dict[str, NormalizedField]:
    raw_ctx = {k: (v.value if isinstance(v, FieldExtraction) else None) for k, v in ext.fields.items()}
    out: dict[str, NormalizedField] = {}
    for key in schema.comparison_keys:
        src = ext.fields.get(key) or Malformed(reason="field missing from extraction")
        if isinstance(src, Malformed):
            out[key] = NormalizedField(key=key, value=None, absent=False, malformed=src.reason, source=src)
            continue
        if src.status is Status.DECLARED_ABSENT:
            out[key] = NormalizedField(key=key, value=None, absent=True, source=src)
            continue
        try:
            val = normalize_value(schema.spec(key), src.value, context=raw_ctx)
            out[key] = NormalizedField(key=key, value=val, absent=False, source=src)
        except NormalizeError as exc:
            out[key] = NormalizedField(key=key, value=None, absent=False, malformed=str(exc), source=src)
    return out


def values_equal(a: Any, b: Any) -> bool:
    """Exact equality on canonical values. Lists are ordered and length-sensitive: a scalar
    100 and a list [100, 100, 100] are NOT equal (a near-miss is a finding)."""
    if isinstance(a, list) or isinstance(b, list):
        if not (isinstance(a, list) and isinstance(b, list)) or len(a) != len(b):
            return False
        return all(values_equal(x, y) for x, y in zip(a, b))
    return a == b
