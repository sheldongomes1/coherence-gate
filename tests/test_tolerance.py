from dataclasses import replace

from coherence_gate import comparator, merger
from coherence_gate.schema_loader import schema_for
from coherence_gate.types import BookingLookup, Citation, FieldExtraction, FindingType, NormalizedField, Status

S = schema_for("note")


def _m(vals):
    a = {}
    for k in S.comparison_keys:
        v = vals.get(k)
        src = FieldExtraction(status=Status.DECLARED_ABSENT) if v is None else FieldExtraction(status=Status.EXTRACTED, value=v, citation=Citation(text_span=str(v)))
        a[k] = NormalizedField(key=k, value=v, absent=v is None, source=src)
    return merger.merge(a, a, S)


def test_date_tolerance_is_off_by_default_and_declared_per_schema():
    ts = {"autocall_observation_dates": ["2027-05-12", "2027-11-12"]}
    bk = {"autocall_observation_dates": ["2027-05-12", "2027-11-15"]}
    lk = BookingLookup(trade_id="X", found=True, record=bk, transport="direct")
    S0 = replace(S, tolerances={})   # no declared tolerance -> exact (independent of what the schema file currently declares)
    f = {x.field: x for x in comparator.compare("D", _m(ts), lk, S0)}
    assert f["autocall_observation_dates"].type is FindingType.MISMATCH
    S3 = replace(S, tolerances={"autocall_observation_dates": {"type": "date_days", "days": 3}})
    f3 = {x.field: x for x in comparator.compare("D", _m(ts), lk, S3)}
    assert f3["autocall_observation_dates"].type is FindingType.CLEAN and "tolerance" in f3["autocall_observation_dates"].detail
    S1 = replace(S, tolerances={"autocall_observation_dates": {"type": "date_days", "days": 1}})
    assert {x.field: x for x in comparator.compare("D", _m(ts), lk, S1)}["autocall_observation_dates"].type is FindingType.MISMATCH
