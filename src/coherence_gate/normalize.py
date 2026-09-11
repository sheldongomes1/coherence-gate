"""ALL normalization lives here (LLD §4). Pure functions, unit-tested, never in a prompt.

Canonical forms:
  date       -> "YYYY-MM-DD" str. Accepts ISO, "17 April 2026", "April 17, 2026", "17-Apr-2026",
                "17/04/2026" (day-first, only when unambiguous). Ambiguous numeric dates
                (day part <= 12, e.g. 03/04/2026) raise NormalizeError (ADR-14): the gate
                refuses to guess a date.
  decimal    -> Decimal, normalized so 8.25 == 8.2500. Strips thousands separators, %,
                currency codes/words, and mm/m/bn/k multipliers.
  iso4217    -> upper 3-letter code
  ticker     -> upper, stripped, "Index"/"Equity" suffix and exchange suffix removed
  enum       -> canonical member via synonym table
  bool       -> True/False from yes/no/true/false
  coupon     -> coupon_rate_pct is converted to PER ANNUM when coupon_rate_basis is per_period
                (rate × periods per year). This is the G09 rule.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .schema_loader import FieldSpec, Schema
from .types import Extraction, FieldExtraction, Malformed, NormalizedField, Status

PERIODS_PER_YEAR = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1}

ENUM_SYNONYMS: dict[str, dict[str, str]] = {
    "barrier_type": {"european": "european", "eu": "european", "at maturity": "european",
                     "final valuation date only": "european", "american": "american",
                     "continuous": "american", "continuously observed": "american", "daily": "american",
                     "none": "none", "no barrier": "none", "n/a": "none", "not applicable": "none"},
    "coupon_frequency": {"monthly": "monthly", "month": "monthly", "quarterly": "quarterly", "quarter": "quarterly",
                         "semiannual": "semiannual", "semi-annual": "semiannual", "semi-annually": "semiannual",
                         "semiannually": "semiannual", "half-yearly": "semiannual", "half-year": "semiannual",
                         "6m": "semiannual", "annual": "annual", "annually": "annual", "yearly": "annual", "year": "annual"},
    "coupon_rate_basis": {"per_annum": "per_annum", "per annum": "per_annum", "p.a.": "per_annum", "pa": "per_annum",
                          "annual": "per_annum", "annualised": "per_annum", "annualized": "per_annum",
                          "per_period": "per_period", "per period": "per_period", "per quarter": "per_period",
                          "per month": "per_period", "per half-year": "per_period", "per coupon period": "per_period"},
    "day_count": {"30/360": "30/360", "30e/360": "30/360", "30/360 (bond basis)": "30/360", "bond basis": "30/360",
                  "act/360": "ACT/360", "actual/360": "ACT/360", "act/365": "ACT/365", "actual/365": "ACT/365",
                  "act/365 (fixed)": "ACT/365", "actual/365 (fixed)": "ACT/365", "act/365f": "ACT/365", "act/365 fixed": "ACT/365"},
    "settlement": {"cash": "cash", "cash settlement": "cash", "physical": "physical", "physical delivery": "physical",
                   "physical settlement": "physical"},
    "business_day_convention": {"following": "following", "following business day": "following",
                                "mod_following": "mod_following", "modified following": "mod_following",
                                "modified following business day": "mod_following", "mod following": "mod_following",
                                "preceding": "preceding", "preceding business day": "preceding"},
}

_MULT = {"k": 1_000, "m": 1_000_000, "mm": 1_000_000, "mn": 1_000_000, "million": 1_000_000,
         "bn": 1_000_000_000, "b": 1_000_000_000, "billion": 1_000_000_000}
_CCY_WORDS = r"(usd|cad|eur|gbp|jpy|chf|aud|us\$|c\$|\$|€|£|dollars?|euros?)"


class NormalizeError(ValueError):
    """Value cannot be brought to canonical form; becomes MALFORMED on that field."""


# ------------------------------------------------------------------ scalar normalizers
def norm_date(v: Any) -> str:
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip().rstrip(".")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return date.fromisoformat(s).isoformat()
        except ValueError as exc:
            raise NormalizeError(f"bad ISO date {s!r}") from exc
    for fmt in ("%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%d-%b-%Y", "%d-%B-%Y", "%d %B, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", s)
    if m:
        a, b, y = int(m[1]), int(m[2]), int(m[3])
        if a > 12 and b <= 12:
            return date(y, b, a).isoformat()          # unambiguous day-first
        if b > 12 and a <= 12:
            raise NormalizeError(f"month-first numeric date {s!r} not accepted; documents are day-first")
        raise NormalizeError(f"ambiguous numeric date {s!r} (ADR-14)")
    raise NormalizeError(f"unrecognised date {s!r}")


def norm_decimal(v: Any) -> Decimal:
    if isinstance(v, bool):
        raise NormalizeError(f"boolean where decimal expected: {v!r}")
    if isinstance(v, (int, float, Decimal)):
        return _dec(str(v))
    s = str(v).strip().lower()
    s = re.sub(r"\(.*?\)", "", s)                    # drop parentheticals like "(USD 2,500,000)"
    s = re.sub(_CCY_WORDS, "", s)
    s = re.sub(r"\b(per\s+(annum|year|quarter|month|half[- ]year|period)|p\.a\.?|pa|annually|quarterly|monthly|semi-?annually|of\s+(the\s+)?initial\s+level)\b", "", s)
    s = s.replace(",", "").replace("%", "").replace("per cent", "").replace("percent", "").strip().rstrip(".")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(k|mm|mn|m|million|bn|b|billion)?", s)
    if not m:
        raise NormalizeError(f"unrecognised decimal {v!r}")
    d = _dec(m[1])
    if m[2]:
        d = d * _MULT[m[2]]
    return d.normalize()


def _dec(s: str) -> Decimal:
    try:
        return Decimal(s).normalize()
    except InvalidOperation as exc:
        raise NormalizeError(f"not a decimal: {s!r}") from exc


def norm_currency(v: Any) -> str:
    s = str(v).strip().upper()
    aliases = {"US$": "USD", "$": "USD", "C$": "CAD", "CA$": "CAD", "€": "EUR", "£": "GBP"}
    s = aliases.get(s, s)
    if not re.fullmatch(r"[A-Z]{3}", s):
        raise NormalizeError(f"not an ISO-4217 code: {v!r}")
    return s


def norm_ticker(v: Any) -> str:
    s = str(v).strip().upper()
    s = re.sub(r"\s+(INDEX|EQUITY|CURNCY|COMDTY)$", "", s)
    s = re.sub(r"\s+[A-Z]{2}$", "", s)               # exchange suffix e.g. "AAPL US"
    s = s.replace("BLOOMBERG:", "").strip()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", s):
        raise NormalizeError(f"not a ticker: {v!r}")
    return s


def norm_enum(key: str, v: Any, allowed: tuple[str, ...]) -> str:
    s = str(v).strip().lower().replace("_", "_")
    table = ENUM_SYNONYMS.get(key, {})
    if s in table:
        return table[s]
    if s in {a.lower() for a in allowed}:
        return next(a for a in allowed if a.lower() == s)
    s2 = s.replace(" ", "_")
    if s2 in {a.lower() for a in allowed}:
        return next(a for a in allowed if a.lower() == s2)
    raise NormalizeError(f"{key}: {v!r} not in {list(allowed)}")


def norm_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"true", "yes", "y", "1"}:
        return True
    if s in {"false", "no", "n", "0"}:
        return False
    raise NormalizeError(f"not a boolean: {v!r}")


def _as_list(v: Any) -> list:
    if isinstance(v, (list, tuple)):
        return list(v)
    if isinstance(v, str) and ("," in v or ";" in v):
        return [p.strip() for p in re.split(r"[;,]", v) if p.strip()]
    return [v]


# ------------------------------------------------------------------ dispatcher
def normalize_value(spec: FieldSpec, value: Any, *, context: dict[str, Any] | None = None) -> Any:
    if value is None:
        raise NormalizeError(f"{spec.name}: null value")
    t = spec.base_type
    if spec.name == "coupon_rate_pct":
        rate = norm_decimal(value)
        ctx = context or {}
        basis = ctx.get("coupon_rate_basis")
        if basis is not None:
            basis = norm_enum("coupon_rate_basis", basis, ("per_annum", "per_period"))
            if basis == "per_period":
                freq = ctx.get("coupon_frequency")
                if freq is None:
                    raise NormalizeError("coupon_rate_pct quoted per period but coupon_frequency unknown")
                rate = rate * PERIODS_PER_YEAR[norm_enum("coupon_frequency", freq, tuple(PERIODS_PER_YEAR))]
        return rate.normalize()
    if t == "date":
        return norm_date(value)
    if t == "decimal":
        if isinstance(value, list):                  # autocall_level_pct may be a list
            return [norm_decimal(x) for x in value]
        return norm_decimal(value)
    if t == "iso4217":
        return norm_currency(value)
    if t == "ticker":
        return norm_ticker(value)
    if t == "list[ticker]":
        return [norm_ticker(x) for x in _as_list(value)]
    if t == "list[date]":
        return [norm_date(x) for x in _as_list(value)]
    if t == "enum":
        return norm_enum(spec.name, value, spec.enum or ())
    if t == "bool":
        return norm_bool(value)
    if t == "str":
        return str(value).strip()
    raise NormalizeError(f"{spec.name}: no normalizer for type {spec.type}")


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
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        try:
            return Decimal(str(a)).normalize() == Decimal(str(b)).normalize()
        except InvalidOperation:
            return False
    return a == b
