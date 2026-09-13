"""schema/termsheet_v1.json is the single source of truth (LLD §3.1).

It drives three things from one file: the field table rendered into the prompt, the JSON
schema both extractors are constrained with, and the list of comparison keys.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, create_model

from .types import FieldExtraction

from .config import ROOT

SCHEMA_DIR = ROOT / "schema"
SCHEMA_PATH = SCHEMA_DIR / "termsheet_v1.json"
PRODUCTS_PATH = SCHEMA_DIR / "products.json"

# Fields that have no booking counterpart and are consumed by normalize.py only (ADR-1).
# (termsheet_v1 predates the per-schema `non_compared` list; kept as its default.)
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
    product_type: str = "note"
    non_compared: frozenset[str] = NON_COMPARED
    relations: tuple[dict, ...] = ()   # deterministic cross-field rules (comparator.check_relations)
    tolerances: dict = field(default_factory=dict)  # per-field declared tolerances (CS8c cycle); default none

    @property
    def names(self) -> list[str]:
        return [f.name for f in self.fields]

    @property
    def comparison_keys(self) -> list[str]:
        return [f.name for f in self.fields if f.name not in self.non_compared]

    @property
    def relation_keys(self) -> list[str]:
        return [f"rel:{r['name']}" for r in self.relations]

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
    nc = frozenset(raw["non_compared"]) if "non_compared" in raw else NON_COMPARED
    return Schema(version=str(raw["version"]), fields=fields, product_type=raw.get("product_type", "note"),
                  non_compared=nc, relations=tuple(raw.get("relations", [])), tolerances=dict(raw.get("tolerances", {})))


@lru_cache(maxsize=1)
def load_products(path: Path = PRODUCTS_PATH) -> dict:
    return json.loads(Path(path).read_text())


def schema_for(product_type: str) -> Schema:
    prods = load_products()["products"]
    if product_type not in prods:
        raise KeyError(f"unknown product_type {product_type!r}; known: {list(prods)}")
    return load_schema(SCHEMA_DIR / prods[product_type]["schema"])


def all_schemas() -> dict[str, Schema]:
    return {pt: schema_for(pt) for pt in load_products()["products"]}


def detect_product(text: str) -> tuple[str, str]:
    """Deterministic product detection by title keywords (code, not model). Returns
    (product_type, matched keyword or 'default')."""
    prods = load_products()
    head = text[:4000]
    for pt, spec in prods["products"].items():
        for kw in spec.get("detect", []):
            if kw in head:
                return pt, kw
    return prods.get("default", "note"), "default"


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
    "load_products",
    "schema_for",
    "all_schemas",
    "detect_product",
    "build_extraction_model",
    "extraction_json_schema",
    "FieldExtraction",
    "NON_COMPARED",
]
