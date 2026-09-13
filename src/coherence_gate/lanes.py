"""Tiered autonomy (LLD §7). A field auto-clears only when the comparator said CLEAN, and
CLEAN already implies both families agreed. The document auto-clears only if every field
did. There is no partial credit and no override hook: autonomy is earned per field."""
from __future__ import annotations

from .types import Finding, FindingType, Lane


def assign(findings: list[Finding]) -> tuple[list[Finding], Lane]:
    """CLEAN -> AUTO_CLEAR; NOT_EVALUABLE -> INFO (a check that was not performed is neither attested
    nor a flag); everything else -> TRIAGE. A document auto-clears when every performed check is
    CLEAN and nothing is in TRIAGE; INFO rows do not block it but are listed as not evaluated."""
    for f in findings:
        f.lane = Lane.AUTO_CLEAR if f.type is FindingType.CLEAN else (Lane.INFO if f.type is FindingType.NOT_EVALUABLE else Lane.TRIAGE)
    performed = [f for f in findings if f.lane is not Lane.INFO]
    doc_lane = Lane.AUTO_CLEAR if performed and all(f.lane is Lane.AUTO_CLEAR for f in performed) else Lane.TRIAGE
    return findings, doc_lane
