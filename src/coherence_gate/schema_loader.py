"""schema/termsheet_v1.json is the single source of truth (LLD §3.1).

It drives three things from one file: the field table rendered into the prompt, the JSON
schema both extractors are constrained with, and the list of comparison keys.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, create_model

from .types import FieldExtraction

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "termsheet_v1.json"

# Fields that have no booking counterpart and are consumed by normalize.py only (ADR-1).
NON_COMPARED = frozenset({"coupon_rate_basis"})


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str
    critical: bool
    description: str
    enum: tuple[str, ...] | None = None

    @property
    def base_type(self) -> str:
        """'decimal|absent' -> 'decimal'; 'list[date]|absent' -> 'list[date]'."""
        return self.type.split("|")[0]

    @property
    def may_be_absent(self) -> bool:
        return "absent" in self.type


@dataclass(frozen=True)
class Schema:
    version: str
    fields: tuple[FieldSpec, ...]

    @property
    def names(self) -> list[str]:
        return [f.name for f in self.fields]

    @property
    def comparison_keys(self) -> list[str]:
        return [f.name for f in self.fields if f.name not in NON_COMPARED]

    def spec(self, name: str) -> FieldSpec:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    def prompt_table(self) -> str:
        rows = ["| field | type | description |", "|---|---|---|"]
        for f in self.fields:
            t = f.type + (f" one of {list(f.enum)}" if f.enum else "")
            rows.append(f"| {f.name} | {t} | {f.description} |")
        return "\n".join(rows)


@lru_cache(maxsize=1)
def load_schema(path: Path = SCHEMA_PATH) -> Schema:
    raw = json.loads(Path(path).read_text())
    fields = tuple(
        FieldSpec(
            name=f["name"],
            type=f["type"],
            critical=bool(f["critical"]),
            description=f["description"],
            enum=tuple(f["enum"]) if f.get("enum") else None,
        )
        for f in raw["fields"]
    )
    return Schema(version=str(raw["version"]), fields=fields)


class _RawCitation(BaseModel):
    text_span: str = Field(description="Verbatim substring copied from the document.")


class _RawField(BaseModel):
    """What the MODEL emits (before the guard). Looser than FieldExtraction on purpose: the
    guard, not the JSON parser, is what turns a bad shape into a MALFORMED finding."""

    status: str = Field(description="EXTRACTED or DECLARED_ABSENT")
    value: Any | None = Field(default=None, description="As written in the document; null if absent.")
    citation: _RawCitation | None = None
    note: str | None = None


@lru_cache(maxsize=1)
def build_extraction_model(schema: Schema | None = None) -> type[BaseModel]:
    """Pydantic model with one required `_RawField` per schema field. Its JSON schema is what
    both extractors are constrained with, so a field cannot be omitted by the model."""
    schema = schema or load_schema()
    fields: dict[str, Any] = {
        f.name: (_RawField, Field(description=f"{f.type}. {f.description}")) for f in schema.fields
    }
    return create_model("TermSheetExtractionV1", **fields)


def extraction_json_schema(schema: Schema | None = None) -> dict[str, Any]:
    return build_extraction_model(schema).model_json_schema()


__all__ = [
    "FieldSpec",
    "Schema",
    "load_schema",
    "build_extraction_model",
    "extraction_json_schema",
    "FieldExtraction",
    "NON_COMPARED",
]
