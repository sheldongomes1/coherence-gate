"""Post-validation of a raw model extraction (LLD §9.4, ADR-3).

Per field: present; status valid; value/citation pairing invariant; citation span found
VERBATIM in the document (exact first, then whitespace-collapsed); char_range recomputed from
the source, never trusted from the model; rough type shape. Each violation demotes that field
to `Malformed`; the rest of the extraction survives. Never raises.
"""
from __future__ import annotations

import re
from typing import Any

from ..schema_loader import Schema
from ..types import Citation, FieldExtraction, Malformed, Status

_WS = re.compile(r"\s+")


_TAG = re.compile(r"<[^>]+>")
_SEP = re.compile(r"[\s|]+")
_ENTITY = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&apos;": "'", "&nbsp;": " "}
_TAG_OR_ENTITY = re.compile(r"<[^>]+>|&(?:amp|lt|gt|quot|#39|apos|nbsp);")


def _clean_span(span: str) -> str:
    """What the model may have pasted around the words: HTML tags, literal escape sequences
    ("\\n", "\\t"), entities. None of it is evidence; the words are."""
    span = _TAG.sub(" ", span)
    span = span.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    for ent, ch in _ENTITY.items():
        span = span.replace(ent, ch)
    return span


def _view(document: str) -> tuple[str, list[int]]:
    """A matching view of the document: HTML tags and '|' become single spaces, so a span cited
    as 'Trade Date | 2026-05-12' can anchor into '<td>Trade Date</td>\n<td>2026-05-12</td>' (parsed
    PDFs) or '| Trade Date | 2026-05-12 |' (markdown tables). Returns the view and a map from
    view offsets back to ORIGINAL offsets, so char_range always refers to the artifact on disk."""
    out, idx = [], []
    i = 0
    for m in _TAG_OR_ENTITY.finditer(document):
        for j in range(i, m.start()):
            out.append(" " if document[j] == "|" else document[j]); idx.append(j)
        out.append(_ENTITY.get(m.group(0), " ")); idx.append(m.start())
        i = m.end()
    for j in range(i, len(document)):
        out.append(" " if document[j] == "|" else document[j]); idx.append(j)
    idx.append(len(document))
    return "".join(out), idx


def locate(span: str, document: str) -> tuple[int, int] | None:
    """Offsets of `span` in `document`: exact; else whitespace-insensitive; else against the
    tag/pipe-stripped view (offsets mapped back to the original). None if not found."""
    if not span:
        return None
    i = document.find(span)
    if i >= 0:
        return (i, i + len(span))
    parts = [re.escape(p) for p in _SEP.split(_clean_span(span).strip()) if p]
    if not parts:
        return None
    pattern = re.compile(r"\s+".join(parts))
    m = pattern.search(document)
    if m:
        return (m.start(), m.end())
    view, idx = _view(document)
    m = pattern.search(view)
    if not m:
        return None
    return (idx[m.start()], idx[m.end() - 1] + 1)


def display_span(text: str) -> str:
    """Human-readable form of a matched slice of the artifact: tags and entities removed,
    pipes/whitespace collapsed. char_range still points at the raw artifact bytes."""
    view, _ = _view(text)
    return re.sub(r"\s+", " ", view).strip()


def _shape_ok(base_type: str, value: Any) -> bool:
    if base_type.startswith("list"):
        return isinstance(value, (list, str))          # a comma string is normalized later
    if base_type == "bool":
        return isinstance(value, (bool, str))
    if base_type == "decimal":
        return isinstance(value, (int, float, str, list)) and not isinstance(value, bool)
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def _per_field(data: dict) -> dict:
    """Map shapes -> {f: {status, value, citation, note}}.
    Shape E (ADR-24): {value:{f..}, citation:{f..}, absent:[f..]}. Shape maps3 (ADR-16): {status:{f..}, value:{f..}, citation:{f..}}."""
    if {"value", "citation", "absent"} <= set(data) and isinstance(data["value"], dict) and isinstance(data["citation"], dict):
        absent = set(data["absent"]) if isinstance(data["absent"], list) else set()
        names = set(data["value"]) | set(data["citation"]) | absent
        return {n: {"status": "DECLARED_ABSENT" if n in absent else "EXTRACTED",
                    "value": data["value"].get(n), "citation": {"text_span": data["citation"].get(n)}, "note": None} for n in names}
    if not ({"status", "value", "citation"} <= set(data) and all(isinstance(data[k], dict) for k in ("status", "value", "citation"))):
        return data
    names = set(data["status"]) | set(data["value"]) | set(data["citation"])
    notes = data.get("note") if isinstance(data.get("note"), dict) else {}
    return {n: {"status": data["status"].get(n), "value": data["value"].get(n),
                "citation": {"text_span": data["citation"].get(n)}, "note": notes.get(n)} for n in names}


def guard(data: Any, document: str, schema: Schema) -> tuple[dict[str, FieldExtraction | Malformed], list[str]]:
    out: dict[str, FieldExtraction | Malformed] = {}
    violations: list[str] = []
    if isinstance(data, dict):
        data = _per_field(data)
    if not isinstance(data, dict):
        for f in schema.fields:
            out[f.name] = Malformed(reason="top-level JSON is not an object", raw=data)
        return out, ["top-level JSON is not an object"]
    for spec in schema.fields:
        raw = data.get(spec.name)
        if raw is None:
            out[spec.name] = Malformed(reason="field missing from output")
            violations.append(f"{spec.name}: missing")
            continue
        if not isinstance(raw, dict):
            out[spec.name] = Malformed(reason="field is not an object", raw=raw)
            violations.append(f"{spec.name}: not an object")
            continue
        status, value, cit, note = raw.get("status"), raw.get("value"), raw.get("citation"), raw.get("note")
        if isinstance(note, str) and not note.strip():
            note = None
        if status == Status.DECLARED_ABSENT:
            if value not in (None, "", [], [""], "ABSENT", "null", "N/A", "n/a"):
                out[spec.name] = Malformed(reason="DECLARED_ABSENT with a value", raw=raw)
                violations.append(f"{spec.name}: absent-with-value")
                continue
            out[spec.name] = FieldExtraction(status=Status.DECLARED_ABSENT, note=note)
            continue
        if status != Status.EXTRACTED:
            out[spec.name] = Malformed(reason=f"unknown status {status!r}", raw=raw)
            violations.append(f"{spec.name}: bad status")
            continue
        if value is None or value == "" or value == []:
            out[spec.name] = Malformed(reason="EXTRACTED with null/empty value", raw=raw)
            violations.append(f"{spec.name}: extracted-null")
            continue
        if not _shape_ok(spec.base_type, value):
            out[spec.name] = Malformed(reason=f"value shape {type(value).__name__} not valid for {spec.type}", raw=raw)
            violations.append(f"{spec.name}: shape")
            continue
        span = (cit or {}).get("text_span") if isinstance(cit, dict) else None
        if isinstance(span, str):
            span = span.strip()
        if not span:
            out[spec.name] = Malformed(reason="EXTRACTED without citation", raw=raw)
            violations.append(f"{spec.name}: no-citation")
            continue
        rng = locate(span, document)
        if rng is None:
            out[spec.name] = Malformed(reason="citation span not found verbatim in document", raw=raw)
            violations.append(f"{spec.name}: span-not-found")
            continue
        out[spec.name] = FieldExtraction(status=Status.EXTRACTED, value=value,
                                         citation=Citation(text_span=display_span(document[rng[0]:rng[1]]), char_range=rng), note=note)
    return out, violations
