from decimal import Decimal

from coherence_gate import comparator, merger
from coherence_gate.normalize import norm_decimal, normalize_value
from coherence_gate.schema_loader import all_schemas, detect_product, schema_for
from coherence_gate.types import BookingLookup, Citation, FieldExtraction, FindingType, NormalizedField, Status

OPT = schema_for("otc_option")


def test_registry_and_detection():
    assert set(all_schemas()) == {"note", "otc_option"}
    assert OPT.comparison_keys and OPT.relation_keys == ["rel:premium_arithmetic"]
    assert detect_product("INDICATIVE TERM SHEET — OTC INDEX OPTION\nEuropean ...")[0] == "otc_option"
    assert detect_product("NORTHBRIDGE\nStructured Notes Programme, Series 2026\n...")[0] == "note"
    assert detect_product("nothing recognisable") == ("note", "default")


def test_option_normalizers():
    assert norm_decimal("Three Currency Business Days following the Valuation Date") == Decimal(3)
    assert normalize_value(OPT.spec("buyer"), "Lakeshore Life Insurance Company (Party B)") == "Lakeshore Life Insurance Company"
    assert normalize_value(OPT.spec("option_style"), "European-style") == "european"
    assert normalize_value(OPT.spec("automatic_exercise"), "Applicable") is True


def _nf(key, value):
    return NormalizedField(key=key, value=value, absent=False,
                           source=FieldExtraction(status=Status.EXTRACTED, value=value, citation=Citation(text_span=str(value))))


def _merged(vals):
    a = {k: _nf(k, v) for k, v in vals.items()}
    for k in OPT.comparison_keys:
        a.setdefault(k, NormalizedField(key=k, value=None, absent=True, source=FieldExtraction(status=Status.DECLARED_ABSENT)))
    return merger.merge(a, a, OPT)


def test_relation_holds_and_fails():
    ts = {"premium_pct": Decimal("4.15"), "notional": Decimal(25_000_000), "premium_amount": Decimal(1_037_500)}
    ok_book = {"premium_pct": "4.15", "notional": "25000000", "premium_amount": "1037500"}
    bad_book = {**ok_book, "premium_amount": "830000"}
    lk = lambda rec: BookingLookup(trade_id="X", found=True, record=rec, transport="direct")  # noqa: E731
    f = comparator.check_relations("D", _merged(ts), lk(ok_book), OPT)
    assert len(f) == 1 and f[0].type is FindingType.CLEAN and f[0].field == "rel:premium_arithmetic"
    f = comparator.check_relations("D", _merged(ts), lk(bad_book), OPT)
    assert f[0].type is FindingType.RELATION_VIOLATION and "booking" in f[0].detail and "term sheet" not in f[0].detail.split("—")[0]
    # not evaluable -> CLEAN with the reason stated, never silent
    f = comparator.check_relations("D", _merged({"premium_pct": Decimal("4.15")}), lk({}), OPT)
    assert f[0].type is FindingType.CLEAN and "not evaluable" in f[0].detail
