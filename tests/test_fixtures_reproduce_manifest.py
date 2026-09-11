"""S1 checkpoint: hand-shaped extractions (values AS WRITTEN in each layout, no model) run
through normalize -> merge -> compare and reproduce every manifest finding exactly, with
zero extra findings. Gemini's fixture writes values one way, Claude's another, so the merger
is exercised on format differences (ADR-4) and on the G09 per-period trap."""
import json
from datetime import date
from pathlib import Path

from coherence_gate import comparator, lanes, merger, normalize
from coherence_gate.schema_loader import load_schema
from coherence_gate.types import (BookingLookup, Citation, Extraction, Family, FieldExtraction, FindingType,
                                  Lane, Status)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
S = load_schema()
PERIODS = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1}


def _prose_date(iso):
    y, m, d = map(int, iso.split("-"))
    return date(y, m, d).strftime("%-d %B %Y")


def as_written(truth: dict, family: Family) -> Extraction:
    """Gemini fixture: prose-ish strings. Claude fixture: ISO/numeric. Same facts."""
    fields = {}
    for spec in S.fields:
        v = truth.get(spec.name, "ABSENT")
        if v == "ABSENT":
            fields[spec.name] = FieldExtraction(status=Status.DECLARED_ABSENT)
            continue
        if family is Family.gemini:
            if spec.base_type == "date":
                v = _prose_date(v)
            elif spec.base_type == "list[date]":
                v = [_prose_date(x) for x in v]
            elif spec.name == "notional":
                v = f"{truth['currency']} {v:,}"
            elif spec.name == "coupon_rate_pct":
                if truth["coupon_rate_basis"] == "per_period":
                    v = f"{v / PERIODS[truth['coupon_frequency']]:g}% per {truth['coupon_frequency'][:-2]}"
                else:
                    v = f"{v}% per annum"
            elif spec.name == "coupon_rate_basis":
                v = "per quarter" if v == "per_period" else "per annum"
            elif spec.name == "underlyings":
                v = [f"{x} Index" for x in v]
            elif spec.name == "day_count":
                v = {"ACT/360": "Actual/360", "ACT/365": "Actual/365 (Fixed)", "30/360": "30/360"}[v]
            elif spec.name == "business_day_convention":
                v = {"following": "Following", "mod_following": "Modified Following", "preceding": "Preceding"}[v]
            elif spec.base_type == "decimal" and not isinstance(v, list):
                v = f"{v}%"
            elif spec.base_type == "bool":
                v = "Yes" if v else "No"
        else:  # claude fixture: canonical-looking values; G09 still quoted per period? No: Claude "reads" the p.a. figure
            if spec.name == "coupon_rate_pct":
                v = truth["coupon_rate_pct"]  # canonical p.a.
            elif spec.name == "coupon_rate_basis":
                v = "per_annum"
        fields[spec.name] = FieldExtraction(status=Status.EXTRACTED, value=v, citation=Citation(text_span=str(v)))
    return Extraction(family=family, model="fixture", fields=fields)


def run_doc(entry):
    truth = json.loads((GOLDEN / entry["truth"]).read_text())
    booking = json.loads((GOLDEN / entry["booking"]).read_text())
    a = normalize.normalize_extraction(as_written(truth, Family.gemini), S)
    b = normalize.normalize_extraction(as_written(truth, Family.claude), S)
    m = merger.merge(a, b, S)
    lk = BookingLookup(trade_id=entry["trade_id"], found=True, record=booking, transport="direct")
    f = comparator.compare(entry["id"], m, lk, S)
    f, lane = lanes.assign(f)
    return {x.field: x for x in f}, lane, m


def test_fixtures_reproduce_manifest_exactly():
    manifest = json.loads((GOLDEN / "manifest.json").read_text())
    misses, extras = [], []
    for entry in manifest["documents"]:
        findings, lane, merged = run_doc(entry)
        assert all(mf.agree for mf in merged.values()), f"{entry['id']}: fixtures should agree after normalization"
        planted = {p["field"]: p["type"] for p in entry["planted"]}
        for fld, typ in planted.items():
            if findings[fld].type != typ:
                misses.append((entry["id"], fld, typ, findings[fld].type, findings[fld].detail))
        for fld, f in findings.items():
            if fld not in planted and f.type is not FindingType.CLEAN:
                extras.append((entry["id"], fld, f.type, f.detail))
        if entry.get("clean_control"):
            assert lane is Lane.AUTO_CLEAR, f"{entry['id']} clean control must auto-clear"
        for t in entry.get("traps", []):
            assert findings[t["field"]].type is FindingType.CLEAN, f"{entry['id']} trap not resolved"
    assert not misses, f"missed planted findings: {misses}"
    assert not extras, f"false flags on clean fields: {extras}"
