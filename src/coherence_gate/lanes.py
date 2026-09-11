"""Tiered autonomy (LLD §7). A field auto-clears only when the comparator said CLEAN, and
CLEAN already implies both families agreed. The document auto-clears only if every field
did. There is no partial credit and no override hook: autonomy is earned per field."""
from __future__ import annotations

from .types import Finding, FindingType, Lane


def assign(findings: list[Finding]) -> tuple[list[Finding], Lane]:
    for f in findings:
        f.lane = Lane.AUTO_CLEAR if f.type is FindingType.CLEAN else Lane.TRIAGE
    doc_lane = Lane.AUTO_CLEAR if findings and all(f.lane is Lane.AUTO_CLEAR for f in findings) else Lane.TRIAGE
    return findings, doc_lane
