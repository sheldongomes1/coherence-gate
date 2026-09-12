from coherence_gate.extract.schema_guard import guard, locate
from coherence_gate.schema_loader import load_schema
from coherence_gate.types import FieldExtraction, Malformed, Status

S = load_schema()
DOC = "Trade Date: 17 April 2026.\nKnock-in Level   of 65%  of the Initial Level.\nNotional: USD 5,000,000."


def ok(value, span):
    return {"status": "EXTRACTED", "value": value, "citation": {"text_span": span}, "note": None}


def absent():
    return {"status": "DECLARED_ABSENT", "value": None, "citation": None, "note": None}


def base():
    return {f.name: absent() for f in S.fields}


def test_locate_exact_and_whitespace_collapsed():
    assert locate("17 April 2026", DOC) == (12, 25)
    s, e = locate("Knock-in Level of 65% of the Initial Level", DOC)
    assert DOC[s:e].startswith("Knock-in Level") and DOC[s:e].endswith("Initial Level")
    assert locate("70%", DOC) is None
    assert locate("", DOC) is None


def test_guard_happy_path_recomputes_offsets():
    d = base()
    d["trade_date"] = ok("17 April 2026", "Trade Date: 17 April 2026")
    fields, v = guard(d, DOC, S)
    f = fields["trade_date"]
    assert isinstance(f, FieldExtraction) and f.status is Status.EXTRACTED
    assert DOC[f.citation.char_range[0]:f.citation.char_range[1]] == "Trade Date: 17 April 2026"
    assert v == []
    assert isinstance(fields["issuer"], FieldExtraction) and fields["issuer"].status is Status.DECLARED_ABSENT


def test_guard_violations_are_per_field_not_fatal():
    d = base()
    d["barrier_level_pct"] = ok("70%", "Knock-in Level of 70%")          # span not in doc
    d["notional"] = {"status": "EXTRACTED", "value": None, "citation": {"text_span": "Notional"}, "note": None}
    d["currency"] = {"status": "EXTRACTED", "value": "USD", "citation": None, "note": None}
    d["coupon_memory"] = {"status": "DECLARED_ABSENT", "value": True, "citation": None, "note": None}
    del d["day_count"]
    d["settlement"] = "cash"
    d["trade_date"] = ok("17 April 2026", "17 April 2026")
    fields, v = guard(d, DOC, S)
    assert isinstance(fields["barrier_level_pct"], Malformed) and "not found" in fields["barrier_level_pct"].reason
    assert isinstance(fields["notional"], Malformed)
    assert isinstance(fields["currency"], Malformed) and "citation" in fields["currency"].reason
    assert isinstance(fields["coupon_memory"], Malformed)
    assert isinstance(fields["day_count"], Malformed) and "missing" in fields["day_count"].reason
    assert isinstance(fields["settlement"], Malformed)
    assert isinstance(fields["trade_date"], FieldExtraction)      # survives its neighbours
    assert len(v) == 6


def test_guard_non_object():
    fields, v = guard(["nope"], DOC, S)
    assert all(isinstance(f, Malformed) for f in fields.values()) and v


def test_locate_across_parsed_html_table_and_markdown_pipes():
    md = "<table>\n  <tr>\n    <td>Trade Date</td>\n    <td>2026-05-12</td>\n  </tr>\n  <tr>\n    <td>Issue Date</td>\n    <td>2026-05-19</td>\n  </tr>\n</table>"
    s, e = locate("Trade Date | 2026-05-12", md)
    assert md[s:e].startswith("Trade Date") and md[s:e].endswith("2026-05-12")
    assert md[s:e] == "Trade Date</td>\n    <td>2026-05-12"          # offsets refer to the artifact on disk
    pipes = "| Trade Date | 2026-05-12 |\n| Issue Date | 2026-05-19 |"
    s2, e2 = locate("Trade Date | 2026-05-12", pipes)
    assert pipes[s2:e2] == "Trade Date | 2026-05-12"
    assert locate("Trade Date | 2026-05-13", md) is None               # a wrong value still fails
