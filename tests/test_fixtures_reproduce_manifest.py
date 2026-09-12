"""S1 checkpoint: hand-shaped extractions (values AS WRITTEN in each layout, no model) run
through normalize -> merge -> compare and reproduce every manifest finding exactly, with
zero extra findings. Gemini's fixture writes values one way, Claude's another, so the merger
is exercised on format differences (ADR-4) and on the G09 per-period trap."""
import json
from datetime import date
from pathlib import Path

from coherence_gate import comparator, lanes, merger, normalize
from coherence_gate.reference import check_reference
from coherence_gate.reference.lane import rules_from_values

# The rulebook as the methodology states it (canonical values; vol target deferred).
METHODOLOGY_TRUTH = {"administrator": "Bloomberg Index Services Limited", "methodology_date": "2025-03-21",
                     "type_i_return_treatment": "excess_return", "type_ii_return_treatment": "total_return",
                     "type_iii_return_treatment": "excess_return", "type_iv_return_treatment": "total_return",
                     "rebalance_frequency": "daily", "index_value_floor": 0, "volatility_target_pct": "ABSENT",
                     "default_deduction_factor_pct": 0, "default_transaction_cost_rate_pct": 0,
                     "default_determination_lag_days": 1, "default_exposure_direction_type": "long_only",
                     "default_volatility_value_selection": "highest"}
RULES = rules_from_values(METHODOLOGY_TRUTH)
from coherence_gate.schema_loader import load_schema, schema_for
from coherence_gate.types import (BookingLookup, Citation, Extraction, Family, FieldExtraction, FindingType,
                                  Lane, Status)

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
S = load_schema()
PERIODS = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1}


def _prose_date(iso):
    y, m, d = map(int, iso.split("-"))
    return date(y, m, d).strftime("%-d %B %Y")


def as_written(truth: dict, family: Family, schema=None) -> Extraction:
    """Gemini fixture: prose-ish strings. Claude fixture: ISO/numeric. Same facts."""
    schema = schema or S
    fields = {}
    for spec in schema.fields:
        v = truth.get(spec.name, "ABSENT")
        if v == "ABSENT":
            fields[spec.name] = FieldExtraction(status=Status.DECLARED_ABSENT)
            continue
        if family is Family.gemini:
            if spec.base_type == "date":
                v = _prose_date(v)
            elif spec.base_type == "list[date]":
                v = [_prose_date(x) for x in v]
            elif spec.name in ("notional", "premium_amount"):
                v = f"{truth['currency']} {v:,}"
            elif spec.name == "cash_settlement_days":
                v = {3: "Three"}.get(v, str(v)) + " Currency Business Days following the Valuation Date"
            elif spec.name == "buyer":
                v = f"{v} (Party B)"
            elif spec.name in ("option_style", "option_type"):
                v = v.capitalize()
            elif spec.name == "index_return_type":
                v = {"type_i": "Type I", "type_ii": "Type II"}.get(v, v) + " under the Index Methodology"
            elif spec.name == "index_return_treatment":
                v = {"excess_return": "Excess Return", "total_return": "Total Return"}[v] + " (Type I under the Index Methodology): no cash return or financing cost accrues in the volatility control process"
            elif spec.name == "index_rebalance_frequency":
                v = {"daily": "Each Index Business Day, in accordance with the Index Methodology", "monthly": "Each calendar month, in accordance with the Index Methodology"}[v]
            elif spec.name == "index_vol_target_pct":
                v = f"{v}% per annum"
            elif spec.name == "index_deduction_factor_pct":
                v = f"{v:.2f}% per annum, deducted daily from the Index Value"
            elif spec.name == "index_transaction_cost_rate_pct":
                v = f"{v}% on changes in Underlying Index units, as provided in the Index Methodology"
            elif spec.name == "index_administrator":
                v = v + ", authorised and regulated by the Financial Conduct Authority as a benchmark administrator"
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
                v = ("Applicable" if v else "Not applicable") if spec.name == "automatic_exercise" else ("Yes" if v else "No")
        else:  # claude fixture: canonical-looking values; Claude "reads" the p.a. figure
            if spec.name == "coupon_rate_pct":
                v = truth["coupon_rate_pct"]  # canonical p.a.
            elif spec.name == "coupon_rate_basis":
                v = "per_annum"
            elif spec.name == "cash_settlement_days":
                v = "Three"
        fields[spec.name] = FieldExtraction(status=Status.EXTRACTED, value=v, citation=Citation(text_span=str(v)))
    return Extraction(family=family, model="fixture", fields=fields)


def run_doc(entry, golden=GOLDEN):
    sc = schema_for(entry.get("product_type", "note"))
    truth = json.loads((golden / entry["truth"]).read_text())
    booking = json.loads((golden / entry["booking"]).read_text())
    a = normalize.normalize_extraction(as_written(truth, Family.gemini, sc), sc)
    b = normalize.normalize_extraction(as_written(truth, Family.claude, sc), sc)
    m = merger.merge(a, b, sc)
    lk = BookingLookup(trade_id=entry["trade_id"], found=True, record=booking, transport="direct")
    f = comparator.compare(entry["id"], m, lk, sc) + comparator.check_relations(entry["id"], m, lk, sc)
    f += check_reference(entry["id"], m, RULES, sc)
    f, lane = lanes.assign(f)
    return {x.field: x for x in f}, lane, m


import os
import pytest


@pytest.mark.parametrize("golden", [GOLDEN, Path(os.environ["CG_GOLDEN_OUT"])] if os.environ.get("CG_GOLDEN_OUT") else [GOLDEN])
def test_fixtures_reproduce_manifest_exactly(golden):
    manifest = json.loads((golden / "manifest.json").read_text())
    misses, extras = [], []
    for entry in manifest["documents"]:
        findings, lane, merged = run_doc(entry, golden)
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
