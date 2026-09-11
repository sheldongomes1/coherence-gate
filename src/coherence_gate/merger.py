"""Agreement merger (LLD §5). Pure function over two normalized extractions.

Truth table per comparison key:
  value x  / value x  -> agree, x
  value x  / value y  -> disagree            (EXTRACTOR_DISAGREEMENT downstream)
  ABSENT   / ABSENT   -> agree, absent
  value    / ABSENT   -> disagree
  MALFORMED/ anything -> disagree, families listed (MALFORMED_EXTRACTION downstream)
There is deliberately no third input: no arbiter, no confidence, no majority (Rule 5).
"""
from __future__ import annotations

from .normalize import values_equal
from .schema_loader import Schema
from .types import Family, MergedField, NormalizedField


def merge(a: dict[str, NormalizedField], b: dict[str, NormalizedField], schema: Schema,
          families: tuple[Family, Family] = (Family.gemini, Family.claude)) -> dict[str, MergedField]:
    out: dict[str, MergedField] = {}
    for key in schema.comparison_keys:
        na, nb = a[key], b[key]
        bad = [fam for fam, nf in zip(families, (na, nb)) if nf.malformed]
        if bad:
            out[key] = MergedField(key=key, agree=False, value=None, absent=False, a=na, b=nb, malformed_families=bad)
        elif na.absent and nb.absent:
            out[key] = MergedField(key=key, agree=True, value=None, absent=True, a=na, b=nb)
        elif na.absent != nb.absent:
            out[key] = MergedField(key=key, agree=False, value=None, absent=False, a=na, b=nb)
        elif values_equal(na.value, nb.value):
            out[key] = MergedField(key=key, agree=True, value=na.value, absent=False, a=na, b=nb)
        else:
            out[key] = MergedField(key=key, agree=False, value=None, absent=False, a=na, b=nb)
    return out
