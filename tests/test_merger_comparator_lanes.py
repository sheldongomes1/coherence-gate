from decimal import Decimal

from coherence_gate import comparator, lanes, merger
from coherence_gate.schema_loader import load_schema
from coherence_gate.types import (BookingLookup, Citation, FieldExtraction, FindingType, Lane, Malformed,
                                  NormalizedField, Status)

S = load_schema()
KEYS = S.comparison_keys


def nf(key, value=None, absent=False, malformed=None):
    src = Malformed(reason=malformed) if malformed else (
        FieldExtraction(status=Status.DECLARED_ABSENT) if absent
        else FieldExtraction(status=Status.EXTRACTED, value=value, citation=Citation(text_span=str(value))))
    return NormalizedField(key=key, value=value, absent=absent, malformed=malformed, source=src)


def full(values: dict, **overrides):
    """A complete normalized extraction: every comparison key present."""
    out = {k: nf(k, v) for k, v in values.items()}
    for k in KEYS:
        out.setdefault(k, nf(k, absent=True))
    out.update(overrides)
    return out


BASE = {"trade_id": "T1", "issuer": "X", "notional": Decimal(100), "currency": "USD", "trade_date": "2026-01-01",
        "maturity_date": "2028-01-01", "underlyings": ["SPX"], "initial_level_pct": Decimal(100),
        "barrier_type": "european", "barrier_level_pct": Decimal(65), "coupon_rate_pct": Decimal("8.25"),
        "coupon_frequency": "quarterly", "coupon_memory": True, "day_count": "30/360"}
BOOK = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in BASE.items()}


def test_merger_truth_table():
    a = full(BASE)
    b = full(BASE, barrier_level_pct=nf("barrier_level_pct", Decimal(70)),
             coupon_memory=nf("coupon_memory", absent=True), day_count=nf("day_count", malformed="bad"))
    m = merger.merge(a, b, S)
    assert m["notional"].agree and m["notional"].value == Decimal(100)
    assert m["issue_date"].agree and m["issue_date"].absent           # absent/absent
    assert not m["barrier_level_pct"].agree                            # x vs y
    assert not m["coupon_memory"].agree                                # value vs absent
    assert m["day_count"].malformed_families == ["claude"]             # malformed on one side
    assert len(m["notional"].citations) == 2


def _findings(a, b, record):
    m = merger.merge(a, b, S)
    lk = BookingLookup(trade_id="T1", found=record is not None, record=record, transport="direct")
    return {f.field: f for f in comparator.compare("D", m, lk, S)}


def test_comparator_table():
    f = _findings(full(BASE), full(BASE), {**BOOK, "barrier_level_pct": "70"})
    assert f["barrier_level_pct"].type is FindingType.MISMATCH and f["barrier_level_pct"].severity == "critical"
    assert f["notional"].type is FindingType.CLEAN
    assert f["issue_date"].type is FindingType.CLEAN                   # absent in both
    assert f["settlement"].type is FindingType.CLEAN and f["settlement"].severity == "minor"


def test_ts_absent_and_booking_absent():
    a = full(BASE, barrier_level_pct=nf("barrier_level_pct", absent=True))
    f = _findings(a, a, {**BOOK, "barrier_level_pct": "70"})
    assert f["barrier_level_pct"].type is FindingType.TS_ABSENT
    f2 = _findings(full(BASE), full(BASE), {k: v for k, v in BOOK.items() if k != "day_count"})
    assert f2["day_count"].type is FindingType.BOOKING_ABSENT


def test_disagreement_and_malformed_win_over_booking():
    b = full(BASE, currency=nf("currency", "CAD"), notional=nf("notional", malformed="nope"))
    f = _findings(full(BASE), b, BOOK)
    assert f["currency"].type is FindingType.EXTRACTOR_DISAGREEMENT
    assert f["notional"].type is FindingType.MALFORMED_EXTRACTION


def test_booking_not_found():
    f = _findings(full(BASE), full(BASE), None)
    assert all(x.type is FindingType.BOOKING_ABSENT for x in f.values())


def test_booking_values_are_normalized_before_compare():
    f = _findings(full(BASE), full(BASE), {**BOOK, "trade_date": "1 January 2026", "coupon_rate_pct": "8.2500"})
    assert f["trade_date"].type is FindingType.CLEAN and f["coupon_rate_pct"].type is FindingType.CLEAN


def test_lanes():
    f = list(_findings(full(BASE), full(BASE), BOOK).values())
    f, doc = lanes.assign(f)
    assert doc is Lane.AUTO_CLEAR and all(x.lane is Lane.AUTO_CLEAR for x in f)
    f2 = list(_findings(full(BASE), full(BASE), {**BOOK, "currency": "CAD"}).values())
    f2, doc2 = lanes.assign(f2)
    assert doc2 is Lane.TRIAGE and sum(x.lane is Lane.TRIAGE for x in f2) == 1


def test_not_evaluable_is_info_lane_and_does_not_block_auto_clear():
    from coherence_gate.types import Finding, Severity
    fs = [Finding(id="D:a", doc_id="D", field="a", type=FindingType.CLEAN, severity=Severity.minor),
          Finding(id="D:ref:b", doc_id="D", field="ref:b", type=FindingType.NOT_EVALUABLE, severity=Severity.critical, detail="deferred")]
    fs, doc = lanes.assign(fs)
    assert fs[1].lane is Lane.INFO and doc is Lane.AUTO_CLEAR
    fs2 = [Finding(id="D:ref:b", doc_id="D", field="ref:b", type=FindingType.NOT_EVALUABLE, severity=Severity.critical)]
    assert lanes.assign(fs2)[1] is Lane.TRIAGE   # nothing performed -> nothing attested
