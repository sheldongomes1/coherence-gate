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

import json
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
    "option_style": {"european": "european", "european-style": "european", "american": "american", "american-style": "american"},
    "option_type": {"call": "call", "call option": "call", "put": "put", "put option": "put"},
    "settlement": {"cash": "cash", "cash settlement": "cash", "physical": "physical", "physical delivery": "physical",
                   "physical settlement": "physical"},
    "business_day_convention": {"following": "following", "following business day": "following",
                                "mod_following": "mod_following", "modified following": "mod_following",
                                "modified following business day": "mod_following", "mod following": "mod_following",
                                "preceding": "preceding", "preceding business day": "preceding"},
}

# Enum resolution by regex-contains for claims written as prose (checked after exact/synonym lookup).
ENUM_CONTAINS: dict[str, list[tuple[str, str]]] = {
    "index_return_type": [(r"\btype\s*iv\b", "type_iv"), (r"\btype\s*iii\b", "type_iii"), (r"\btype\s*ii\b", "type_ii"), (r"\btype\s*i\b", "type_i")],
    "index_return_treatment": [(r"excess\s*return", "excess_return"), (r"total\s*return", "total_return")],
    "index_rebalance_frequency": [(r"(each|every|per)\s+(index\s+)?business\s+day|\bdaily\b", "daily"), (r"\bweek", "weekly"),
                                  (r"\bmonth", "monthly"), (r"\bquarter", "quarterly")],
    "type_i_return_treatment": [(r"excess\s*return", "excess_return"), (r"total\s*return", "total_return")],
    "type_ii_return_treatment": [(r"excess\s*return", "excess_return"), (r"total\s*return", "total_return")],
    "type_iii_return_treatment": [(r"excess\s*return", "excess_return"), (r"total\s*return", "total_return")],
    "type_iv_return_treatment": [(r"excess\s*return", "excess_return"), (r"total\s*return", "total_return")],
    "rebalance_frequency": [(r"(each|every|per)\s+(index\s+)?business\s+day|\bdaily\b", "daily"), (r"\bweek", "weekly"),
                            (r"\bmonth", "monthly"), (r"\bquarter", "quarterly")],
    "default_exposure_direction_type": [(r"long[- ]only", "long_only"), (r"directional", "directional")],
    "default_volatility_value_selection": [(r"highest", "highest"), (r"lowest", "lowest"), (r"average", "average")],
}
_NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10}
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
    m_words = re.match(r"^(zero|one|two|three|four|five|six|seven|eight|nine|ten)\b", s)
    if m_words:                                       # "Three Currency Business Days" -> 3
        return Decimal(_NUMBER_WORDS[m_words.group(1)])
    s = re.sub(_CCY_WORDS, "", s)
    s = re.sub(r"\b(per\s+(annum|year|quarter|month|half[- ]year|period)|p\.a\.?|pa|annually|quarterly|monthly|semi-?annually|of\s+(the\s+)?initial\s+level)\b", "", s)
    s = s.replace(",", "").replace("%", "").replace("per cent", "").replace("percent", "").strip().rstrip(".")
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(k|mm|mn|m|million|bn|b|billion)?", s)
    if not m:
        # "0.50 deducted daily from the index value": a leading number followed by a descriptor that
        # contains NO other number is the value as written (a second number would be ambiguous).
        m2 = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(k|mm|mn|m|million|bn|b|billion)?\s+[a-z][^0-9]*", s)
        if m2:
            m = m2
        else:
            raise NormalizeError(f"unrecognised decimal {v!r}")
    d = _dec(m[1])
    if m[2]:
        d = d * _MULT[m[2]]
    return _plain(d)


def _dec(s: str) -> Decimal:
    try:
        return _plain(Decimal(s))
    except InvalidOperation as exc:
        raise NormalizeError(f"not a decimal: {s!r}") from exc


def _plain(d: Decimal) -> Decimal:
    """normalize() but never in exponent form: 70 not 7E+1, 8.25 not 8.2500."""
    d = d.normalize()
    return d.quantize(Decimal(1)) if d == d.to_integral() else d


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
    s = str(v).strip().lower()
    table = ENUM_SYNONYMS.get(key, {})
    if s in table:
        return table[s]
    # "American (continuous observation)" -> "american"; "Cash settlement." -> "cash"
    s = re.sub(r"\(.*?\)", "", s).strip().rstrip(".").strip()
    if s in table:
        return table[s]
    # verbose as-written forms: "European observation", "Modified Following Business Day Convention",
    # "Actual/360 day count basis", "cash settlement"
    s = re.sub(r"\b(observation|barrier|knock-in|business day convention|convention|day count( fraction| basis)?|settlement|basis)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .,-")
    if s in table:
        return table[s]
    if s in {a.lower() for a in allowed}:
        return next(a for a in allowed if a.lower() == s)
    s2 = s.replace(" ", "_")
    if s2 in {a.lower() for a in allowed}:
        return next(a for a in allowed if a.lower() == s2)
    for pat, val in ENUM_CONTAINS.get(key, []):
        if re.search(pat, str(v).lower()):
            return val
    raise NormalizeError(f"{key}: {v!r} not in {list(allowed)}")


def norm_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower().rstrip(".")
    if s in {"true", "yes", "y", "1", "applicable"}:
        return True
    if s in {"false", "no", "n", "0", "not applicable", "n/a", "none"}:
        return False
    # as-written clause fragments: "No memory feature" / "Memory feature" / "memory: yes"
    if re.match(r"^(no|without|not)\b", s):
        return False
    if re.match(r"^(with|has|memory|yes)\b", s):
        return True
    raise NormalizeError(f"not a boolean: {v!r}")


def _unwrap_json_array(v: Any) -> Any:
    """'["100%", "95%"]' (a JSON array written inside a string value) -> ["100%", "95%"]."""
    if isinstance(v, str) and v.lstrip().startswith("[") and v.rstrip().endswith("]"):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
    return v


def _as_list(v: Any, *, split_commas: bool = True) -> list:
    """Arrays pass through. A string splits on ';' '/' or newline; on ',' only when asked
    (dates like 'April 17, 2026' must not be split)."""
    v = _unwrap_json_array(v)
    if isinstance(v, (list, tuple)):
        return list(v)
    if isinstance(v, str):
        seps = r"[;/\n]|,\s*" if split_commas else r"[;/\n]"
        parts = [p.strip() for p in re.split(seps, v) if p.strip()]
        return parts if len(parts) > 1 else [v]
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
        return _plain(rate)
    if t == "date":
        return norm_date(value)
    if t == "decimal":
        value = _unwrap_json_array(value) if spec.name == "autocall_level_pct" else value
        if isinstance(value, list) or (spec.name == "autocall_level_pct" and isinstance(value, str)
                                       and len(_as_list(value)) > 1):
            return [norm_decimal(x) for x in _as_list(value)]  # step-down list; a 1-element list stays a list
        return norm_decimal(value)
    if t == "iso4217":
        return norm_currency(value)
    if t == "ticker":
        return norm_ticker(value)
    if t == "list[ticker]":
        return [norm_ticker(x) for x in _as_list(value)]
    if t == "list[date]":
        return [norm_date(x) for x in _as_list(value, split_commas=False)]
    if t == "enum":
        return norm_enum(spec.name, value, spec.enum or ())
    if t == "bool":
        return norm_bool(value)
    if t == "str":
        out = re.sub(r"\s*\((party [ab]|the (buyer|seller|issuer))\)\s*$", "", str(value).strip(), flags=re.I).strip()
        if spec.name in ("index_administrator", "administrator"):
            # "Bloomberg Index Services Limited, authorised and regulated by ..." / '... ("BISL")' -> legal name only
            out = re.sub(r"\s*\(.*?\)", "", out).split(",")[0].strip()
        return out
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
