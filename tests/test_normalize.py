from decimal import Decimal

import pytest

from coherence_gate.normalize import (NormalizeError, norm_bool, norm_currency, norm_date, norm_decimal,
                                      norm_enum, norm_ticker, normalize_value, values_equal)
from coherence_gate.schema_loader import load_schema

S = load_schema()


@pytest.mark.parametrize("raw,iso", [
    ("2026-04-17", "2026-04-17"), ("17 April 2026", "2026-04-17"), ("April 17, 2026", "2026-04-17"),
    ("17-Apr-2026", "2026-04-17"), ("17/04/2026", "2026-04-17"), ("Apr 17, 2026", "2026-04-17"),
])
def test_dates(raw, iso):
    assert norm_date(raw) == iso


@pytest.mark.parametrize("raw", ["03/04/2026", "04/17/2026", "17 Aprl 2026", "2026-13-01"])
def test_dates_rejected(raw):
    with pytest.raises(NormalizeError):
        norm_date(raw)  # ambiguous, month-first, typo, invalid: never guessed (ADR-14)


@pytest.mark.parametrize("raw,val", [
    ("10,000,000", 10_000_000), ("USD 10,000,000", 10_000_000), ("USD 10mm", 10_000_000),
    ("USD 2.5 million (USD 2,500,000)", 2_500_000), ("65%", 65), ("65.00%", 65), ("65 per cent.", 65),
    (8.25, Decimal("8.25")), ("8.2500", Decimal("8.25")), ("2.0625%", Decimal("2.0625")),
])
def test_decimals(raw, val):
    assert norm_decimal(raw) == Decimal(str(val)).normalize()


def test_decimal_rejects_garbage():
    with pytest.raises(NormalizeError):
        norm_decimal("sixty five")


def test_currency_and_ticker():
    assert norm_currency("usd ") == "USD"
    assert norm_currency("C$") == "CAD"
    assert norm_ticker("SX5E Index") == "SX5E"
    assert norm_ticker("bversa10") == "BVERSA10"
    assert norm_ticker("SPTSX60 Index") == "SPTSX60"


def test_enums_and_bools():
    assert norm_enum("day_count", "Actual/360", ("30/360", "ACT/360", "ACT/365")) == "ACT/360"
    assert norm_enum("day_count", "Actual/365 (Fixed)", ("30/360", "ACT/360", "ACT/365")) == "ACT/365"
    assert norm_enum("business_day_convention", "Modified Following", ("following", "mod_following", "preceding")) == "mod_following"
    assert norm_enum("coupon_frequency", "semi-annually", ("monthly", "quarterly", "semiannual", "annual")) == "semiannual"
    assert norm_bool("Yes") is True and norm_bool("no") is False
    with pytest.raises(NormalizeError):
        norm_enum("day_count", "ACT/ACT", ("30/360", "ACT/360", "ACT/365"))


def test_g09_coupon_per_period_to_per_annum():
    spec = S.spec("coupon_rate_pct")
    ctx = {"coupon_rate_basis": "per_period", "coupon_frequency": "quarterly"}
    assert normalize_value(spec, "2.0625%", context=ctx) == Decimal("8.25")
    ctx_pa = {"coupon_rate_basis": "per annum", "coupon_frequency": "quarterly"}
    assert normalize_value(spec, "8.25% ", context=ctx_pa) == Decimal("8.25")
    assert values_equal(normalize_value(spec, "2.0625", context=ctx), normalize_value(spec, 8.25, context=ctx_pa))


def test_coupon_per_period_without_frequency_is_malformed():
    with pytest.raises(NormalizeError):
        normalize_value(S.spec("coupon_rate_pct"), "2.0625", context={"coupon_rate_basis": "per_period"})


def test_list_vs_scalar_is_not_equal():
    assert not values_equal(Decimal(100), [Decimal(100)] * 3)
    assert values_equal([Decimal("100"), Decimal("95")], [100, 95.0])
    assert not values_equal(["2027-05-12", "2027-11-12"], ["2027-05-12", "2027-11-15"])


def test_lists_from_strings():
    assert normalize_value(S.spec("underlyings"), "SPX Index, SX5E Index") == ["SPX", "SX5E"]
    assert normalize_value(S.spec("autocall_observation_dates"), ["09-Jun-2027", "2027-12-09"]) == ["2027-06-09", "2027-12-09"]
    assert normalize_value(S.spec("autocall_level_pct"), ["100%", "95 per cent.", 90]) == [Decimal(100), Decimal(95), Decimal(90)]


@pytest.mark.parametrize("raw,val", [("7.5% per annum", "7.5"), ("8.25% p.a.", "8.25"), ("2.0625% per quarter", "2.0625"),
                                     ("65% of the Initial Level", "65"), ("9.00% per annum, payable semi-annually", None)])
def test_decimal_strips_period_words(raw, val):
    if val is None:
        with pytest.raises(NormalizeError):
            norm_decimal(raw)  # trailing clause is not a unit; the extractor should not return it
    else:
        assert norm_decimal(raw) == Decimal(val)


def test_autocall_levels_string_forms():
    spec = S.spec("autocall_level_pct")
    assert normalize_value(spec, "100%") == Decimal(100)
    assert normalize_value(spec, "100 per cent., 95 per cent., 90 per cent.") == [Decimal(100), Decimal(95), Decimal(90)]
    assert normalize_value(spec, "100% / 95% / 90%") == [Decimal(100), Decimal(95), Decimal(90)]
    assert normalize_value(S.spec("autocall_observation_dates"), ["April 17, 2027", "October 17, 2027"]) == ["2027-04-17", "2027-10-17"]


def test_enum_strips_parentheticals_and_trailing_period():
    assert norm_enum("barrier_type", "American (continuous observation)", ("european", "american", "none")) == "american"
    assert norm_enum("barrier_type", "European (Final Valuation Date only)", ("european", "american", "none")) == "european"
    assert norm_enum("settlement", "Cash settlement.", ("cash", "physical")) == "cash"


def test_json_array_inside_string_value_and_plain_decimals():
    spec = S.spec("autocall_level_pct")
    assert normalize_value(spec, '["100 per cent.", "95 per cent.", "90 per cent."]') == [Decimal(100), Decimal(95), Decimal(90)]
    assert normalize_value(S.spec("underlyings"), '["SPX Index", "SX5E Index"]') == ["SPX", "SX5E"]
    assert str(norm_decimal("70%")) == "70" and str(norm_decimal("10,000,000")) == "10000000"
    assert str(norm_decimal("8.2500")) == "8.25" and str(norm_decimal("2.0625") * 4) == "8.2500"
