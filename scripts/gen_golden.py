"""Generate the golden set from parameters (ADR-13, v0.2 CS1).

One parameter table -> per document: HTML (house style from the approved templates, one of
four layout variants), PDF (WeasyPrint), canonical TXT (text of the same HTML), truth JSON,
booking JSON; plus manifest.json. Everything comes from the same dict, so labels cannot drift
from the prose. Planted discrepancies are applied to the BOOKING only; the document is always
its own truth. Approved templates override the parameter table where they differ (ADR-20).

Run: make golden   (idempotent; overwrites golden/)
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined

import os
ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(os.environ.get("CG_GOLDEN_OUT", ROOT / "golden"))
TEMPLATES = ROOT / "templates" / "golden"
ISSUER = "Northbridge Capital Markets (Canada) Inc."  # fictional (ADR-12)
PROGRAMME = "Structured Notes Programme, Series 2026"
DESK = "Global Markets — Equity & Index Solutions"
ACCENT = {"clauses": "#12314f", "table": "#1f3d2b", "letter": "#3a2b5f", "prose": "#4a3413"}

# The approved Underlying Index section (templates/golden/G12_bversa10.html), verbatim values.
VERSA10 = dict(
    name="Bloomberg Versa 10 Index", ticker="BVERSA10",
    administrator="Bloomberg Index Services Limited, authorised and regulated by the Financial Conduct Authority as a benchmark administrator",
    return_treatment="Excess Return (Type I under the Index Methodology): no cash return or financing cost accrues in the volatility control process",
    vol_target="10% per annum",
    vol_calc="Exponentially weighted moving average (EWMA), short-term and long-term variance; Volatility Value Selection: Highest",
    exposure="Determined daily; Maximum Target Exposure 150%; Minimum Target Exposure 0%; Exposure Direction: Long-only",
    determination_lag="One Index Business Day",
    rebalancing="Each Index Business Day, in accordance with the Index Methodology",
    deduction="0.50% per annum, deducted daily from the Index Value",
    tcr="0.02% on changes in Underlying Index units, as provided in the Index Methodology",
    currency="USD",
)
INDEX_PROSE = {
    "SPX": "the S&P 500 Index (Bloomberg: SPX Index), a price return index administered by S&P Dow Jones Indices LLC",
    "SX5E": "the EURO STOXX 50 Index (Bloomberg: SX5E Index), a price return index administered by STOXX Ltd.",
    "SPTSX60": "the S&P/TSX 60 Index (Bloomberg: SPTSX60 Index), a price return index administered by S&P Dow Jones Indices LLC",
}
PERIODS = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1}
FREQ_WORD = {"monthly": "month", "quarterly": "quarter", "semiannual": "half-year", "annual": "year"}
DAYCOUNT_WORD = {"ACT/360": "Actual/360", "ACT/365": "Actual/365 (Fixed)", "30/360": "30/360"}
BDC_WORD = {"following": "Following", "mod_following": "Modified Following", "preceding": "Preceding"}
INDEX_NAME = {
    "SPX": "S&P 500 Index",
    "SX5E": "EURO STOXX 50 Index",
    "SPTSX60": "S&P/TSX 60 Index",
    "BVERSA10": "Bloomberg Versa 10 Index",
}

# ----------------------------------------------------------------------------- parameters
# Each entry = the term sheet's truth. `booking_overrides` = what the booking says instead.
DOCS: list[dict] = [
    dict(id="G01", layout="prose", trade_id="SN-2026-0101", notional=5_000_000, currency="USD",
         trade_date="2026-04-14", issue_date="2026-04-21", maturity_date="2029-04-23",
         underlyings=["SPX"], initial_level_pct=100, barrier_type="european", barrier_level_pct=65,
         coupon_rate_pct=7.5, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=False,
         autocall_observation_dates=["2027-04-14", "2027-10-14", "2028-04-14", "2028-10-16"],
         autocall_level_pct=100, day_count="30/360", settlement="cash", business_day_convention="mod_following",
         booking_overrides={"barrier_level_pct": 70},
         planted=[dict(field="barrier_level_pct", type="MISMATCH", note="TS 65, booking 70")]),
    dict(id="G02", layout="table", trade_id="SN-2026-0102", notional=3_000_000, currency="EUR",
         trade_date="2026-05-12", issue_date="2026-05-19", maturity_date="2028-05-19",
         underlyings=["SX5E"], initial_level_pct=100, barrier_type="american", barrier_level_pct=60,
         coupon_rate_pct=9, coupon_rate_basis="per_annum", coupon_frequency="semiannual", coupon_memory=True,
         autocall_observation_dates=["2027-05-12", "2027-11-12", "2028-05-12"],
         autocall_level_pct=100, day_count="ACT/365", settlement="cash", business_day_convention="following",
         booking_overrides={"autocall_observation_dates": ["2027-05-12", "2027-11-15", "2028-05-12"]},
         planted=[dict(field="autocall_observation_dates", type="MISMATCH", note="second observation 2027-11-12 -> 2027-11-15 (+1 business day)")]),
    dict(id="G03", layout="clauses", trade_id="SN-2026-0103", notional=8_000_000, currency="CAD",
         trade_date="2026-03-03", issue_date="2026-03-10", maturity_date="2029-03-12",
         underlyings=["SPTSX60", "BVERSA10"], initial_level_pct=100, barrier_type="european", barrier_level_pct=70,
         coupon_rate_pct=6.8, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=True,
         autocall_observation_dates=["2027-03-03", "2027-09-03", "2028-03-03", "2028-09-05"],
         autocall_level_pct=100, day_count="ACT/360", settlement="cash", business_day_convention="mod_following",
         booking_overrides={"day_count": "30/360"},
         planted=[dict(field="day_count", type="MISMATCH", note="TS ACT/360, booking 30/360")]),
    dict(id="G04", layout="letter", trade_id="SN-2026-0104", notional=2_500_000, currency="USD",
         trade_date="2026-06-09", issue_date="2026-06-16", maturity_date="2028-06-16",
         underlyings=["SPX", "SX5E"], initial_level_pct=100, barrier_type="european", barrier_level_pct=60,
         coupon_rate_pct=10.2, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=True,
         autocall_observation_dates=["2027-06-09", "2027-12-09", "2028-06-09"],
         autocall_level_pct=100, day_count="30/360", settlement="cash", business_day_convention="following",
         booking_overrides={"coupon_memory": False},
         planted=[dict(field="coupon_memory", type="MISMATCH", note="TS has memory clause, booking false")]),
    dict(id="G05", layout="prose", trade_id="SN-2026-0105", notional=10_000_000, currency="USD",
         trade_date="2026-02-17", issue_date="2026-02-24", maturity_date="2028-02-24",
         underlyings=["SPX"], initial_level_pct=100, barrier_type="none", barrier_level_pct="ABSENT",
         coupon_rate_pct=5.25, coupon_rate_basis="per_annum", coupon_frequency="annual", coupon_memory=False,
         autocall_observation_dates="ABSENT", autocall_level_pct="ABSENT",
         day_count="30/360", settlement="cash", business_day_convention="mod_following",
         booking_overrides={"notional": 1_000_000},
         planted=[dict(field="notional", type="MISMATCH", note="TS 10,000,000, booking 1,000,000")]),
    dict(id="G06", layout="table", trade_id="SN-2026-0106", notional=4_000_000, currency="USD",
         trade_date="2026-07-07", issue_date="2026-07-14", maturity_date="2029-07-16",
         underlyings=["SPTSX60"], initial_level_pct=100, barrier_type="european", barrier_level_pct=65,
         coupon_rate_pct=6.5, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=False,
         autocall_observation_dates=["2027-07-07", "2028-07-07"],
         autocall_level_pct=100, day_count="ACT/360", settlement="cash", business_day_convention="mod_following",
         booking_overrides={"currency": "CAD"},
         planted=[dict(field="currency", type="MISMATCH", note="TS USD, booking CAD")]),
    dict(id="G07", layout="clauses", trade_id="SN-2026-0107", notional=6_000_000, currency="EUR",
         trade_date="2026-01-20", issue_date="2026-01-27", maturity_date="2029-01-29",
         underlyings=["SX5E"], initial_level_pct=100, barrier_type="european", barrier_level_pct=55,
         coupon_rate_pct=8, coupon_rate_basis="per_annum", coupon_frequency="annual", coupon_memory=True,
         autocall_observation_dates=["2027-01-20", "2028-01-20", "2028-07-20"],
         autocall_level_pct=[100, 95, 90], day_count="30/360", settlement="cash", business_day_convention="following",
         booking_overrides={"autocall_level_pct": [100, 100, 100]},
         planted=[dict(field="autocall_level_pct", type="MISMATCH", note="TS step-down 100/95/90, booking flat 100/100/100")]),
    dict(id="G08", layout="letter", trade_id="SN-2026-0108", notional=7_500_000, currency="USD",
         trade_date="2026-08-11", issue_date="2026-08-18", maturity_date="2028-08-18",
         underlyings=["SX5E"], initial_level_pct=100, barrier_type="american", barrier_level_pct=60,
         coupon_rate_pct=9.75, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=False,
         autocall_observation_dates=["2027-08-11", "2028-02-11"],
         autocall_level_pct=100, day_count="ACT/365", settlement="cash", business_day_convention="mod_following",
         booking_overrides={"underlyings": ["SPX"]},
         planted=[dict(field="underlyings", type="MISMATCH", note="TS SX5E, booking SPX")]),
    dict(id="G09", layout="prose", trade_id="SN-2026-0109", notional=5_000_000, currency="CAD",
         trade_date="2026-04-28", issue_date="2026-05-05", maturity_date="2029-05-07",
         underlyings=["BVERSA10"], initial_level_pct=100, barrier_type="european", barrier_level_pct=70,
         coupon_rate_pct=2.0625, coupon_rate_basis="per_period", coupon_frequency="quarterly", coupon_memory=False,
         autocall_observation_dates=["2027-04-28", "2027-10-28", "2028-04-28", "2028-10-30"],
         autocall_level_pct=100, day_count="30/360", settlement="cash", business_day_convention="mod_following",
         booking_overrides={},
         planted=[], traps=[dict(field="coupon_rate_pct", expect="CLEAN", note="TS 2.0625% per quarter (8.25% p.a.); booking 8.25 quarterly")]),
    dict(id="G10", layout="table", trade_id="SN-2026-0110", notional=3_500_000, currency="USD",
         trade_date="2026-09-01", issue_date="2026-09-08", maturity_date="2029-09-10",
         underlyings=["SPX"], initial_level_pct=100, barrier_type="european", barrier_level_pct="ABSENT",
         coupon_rate_pct=7.25, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=True,
         autocall_observation_dates=["2027-09-01", "2028-03-01", "2028-09-01"],
         autocall_level_pct=100, day_count="30/360", settlement="cash", business_day_convention="following",
         booking_overrides={"barrier_level_pct": 70},
         planted=[dict(field="barrier_level_pct", type="TS_ABSENT", note="TS omits the knock-in level; booking has 70")]),
    dict(id="G11", layout="clauses", trade_id="SN-2026-0111", notional=4_500_000, currency="USD",
         trade_date="2026-05-26", issue_date="2026-06-02", maturity_date="2028-06-02",
         underlyings=["SPX", "SPTSX60"], initial_level_pct=100, barrier_type="european", barrier_level_pct=60,
         coupon_rate_pct=8.4, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=True,
         autocall_observation_dates=["2027-05-26", "2027-11-26"],
         autocall_level_pct=100, day_count="30/360", settlement="cash", business_day_convention="mod_following",
         booking_overrides={}, planted=[], clean_control=True),
    # G12 = the approved template document (templates/golden/G12_bversa10.html), economics verbatim.
    dict(id="G12", layout="clauses", trade_id="SN-2026-0112", notional=7_500_000, currency="USD",
         trade_date="2026-05-08", issue_date="2026-05-15", maturity_date="2030-05-17",
         underlyings=["BVERSA10"], initial_level_pct=100, barrier_type="european", barrier_level_pct=60,
         coupon_rate_pct=8.25, coupon_rate_basis="per_annum", coupon_frequency="quarterly", coupon_memory=True,
         autocall_observation_dates=["2027-05-10", "2027-11-08", "2028-05-08", "2028-11-08", "2029-05-08", "2029-11-08"],
         autocall_level_pct=100, day_count="30/360", settlement="cash", business_day_convention="mod_following",
         coupon_barrier_pct=70, final_valuation_date="2030-05-10", dist_fee_pct=1.25, hedge_cost_pct=0.30,
         booking_overrides={}, planted=[], clean_control=True),
]

BUYER = "Lakeshore Life Insurance Company"  # fictional (approved template)

OPTIONS: list[dict] = [
    # G13 = the approved OP-2026-0114 document, verbatim economics (clean control).
    dict(id="G13", product="otc_option", trade_id="OP-2026-0114", buyer=BUYER, seller=ISSUER, option_style="european",
         option_type="call", underlyings=["BVERSA10"], notional=25_000_000, currency="USD",
         trade_date="2026-05-08", effective_date="2026-05-12", strike_level_pct=100, participation_rate_pct=100,
         valuation_date="2028-05-08", expiration_date="2028-05-08", automatic_exercise=True,
         premium_pct=4.15, premium_amount=1_037_500, premium_payment_date="2026-05-12", cash_settlement_days=3,
         settlement_currency="USD", calculation_agent="Party A",
         booking_overrides={}, planted=[], clean_control=True),
    # G14: participation documented 100%, booked 95% (the classic FIA under-hedge).
    dict(id="G14", product="otc_option", trade_id="OP-2026-0117", buyer=BUYER, seller=ISSUER, option_style="european",
         option_type="call", underlyings=["BVERSA10"], notional=40_000_000, currency="USD",
         trade_date="2026-06-15", effective_date="2026-06-17", strike_level_pct=100, participation_rate_pct=100,
         valuation_date="2027-06-15", expiration_date="2027-06-15", automatic_exercise=True,
         premium_pct=3.60, premium_amount=1_440_000, premium_payment_date="2026-06-17", cash_settlement_days=3,
         settlement_currency="USD", calculation_agent="Party A",
         booking_overrides={"participation_rate_pct": 95},
         planted=[dict(field="participation_rate_pct", type="MISMATCH", note="documented 100%, booked 95%")]),
    # G15: premium documented 4.15% = USD 1,037,500 on 25mm; booking premium computed off the wrong notional (20mm).
    dict(id="G15", product="otc_option", trade_id="OP-2026-0121", buyer=BUYER, seller=ISSUER, option_style="european",
         option_type="call", underlyings=["BVERSA10"], notional=25_000_000, currency="USD",
         trade_date="2026-07-20", effective_date="2026-07-22", strike_level_pct=100, participation_rate_pct=100,
         valuation_date="2028-07-20", expiration_date="2028-07-20", automatic_exercise=True,
         premium_pct=4.15, premium_amount=1_037_500, premium_payment_date="2026-07-22", cash_settlement_days=3,
         settlement_currency="USD", calculation_agent="Party A",
         booking_overrides={"premium_amount": 830_000},
         planted=[dict(field="premium_amount", type="MISMATCH", note="TS 1,037,500; booking 830,000 (= 4.15% × 20mm, wrong notional)"),
                  dict(field="rel:premium_arithmetic", type="RELATION_VIOLATION", note="booking: 4.15% × 25,000,000 ≠ 830,000")]),
]
OPTION_FIELDS = ["trade_id", "buyer", "seller", "option_style", "option_type", "underlyings", "notional", "currency",
                 "trade_date", "effective_date", "strike_level_pct", "participation_rate_pct", "valuation_date",
                 "expiration_date", "automatic_exercise", "premium_pct", "premium_amount", "premium_payment_date",
                 "cash_settlement_days", "settlement_currency", "calculation_agent"]

FIELDS = ["trade_id", "issuer", "notional", "currency", "trade_date", "issue_date", "maturity_date",
          "underlyings", "initial_level_pct", "barrier_type", "barrier_level_pct", "coupon_rate_pct",
          "coupon_rate_basis", "coupon_frequency", "coupon_memory", "autocall_observation_dates",
          "autocall_level_pct", "day_count", "settlement", "business_day_convention"]


# ----------------------------------------------------------------------------- helpers
def d(iso: str, style: str) -> str:
    y, m, dd = (int(x) for x in iso.split("-"))
    dt = date(y, m, dd)
    if style == "prose":
        return dt.strftime("%-d %B %Y")
    if style == "table":
        return iso
    if style == "clauses":
        return dt.strftime("%B %-d, %Y")
    return dt.strftime("%d-%b-%Y")


def money(n: int, ccy: str, style: str) -> str:
    if style == "prose":
        return f"{ccy} {n:,}"
    if style == "table":
        return f"{ccy} {n:,.2f}"
    if style == "clauses":
        return f"{n:,} {ccy}"
    return f"{ccy} {n/1_000_000:g} million ({ccy} {n:,})"


def pct(v, style: str) -> str:
    if style == "clauses":
        return f"{v:g} per cent."
    if style == "table":
        return f"{v:.2f}%"
    return f"{v:g}%"


def rate_phrase(p: dict, style: str) -> str:
    r, freq = p["coupon_rate_pct"], p["coupon_frequency"]
    if p["coupon_rate_basis"] == "per_period":
        pa = r * PERIODS[freq]
        return f"{r:g}% per {FREQ_WORD[freq]} (equivalent to {pa:g}% per annum)"
    return f"{pct(r, style)} per annum, payable {freq.replace('semiannual', 'semi-annually').replace('ly', 'ly') if freq != 'annual' else 'annually'}"


def freq_adverb(freq: str) -> str:
    return {"monthly": "monthly", "quarterly": "quarterly", "semiannual": "semi-annually", "annual": "annually"}[freq]


def underlying_phrase(p: dict) -> str:
    names = [f"the {INDEX_NAME[u]} (Bloomberg: {u} Index)" for u in p["underlyings"]]
    if len(names) == 1:
        return names[0]
    return "the worst performing of " + " and ".join(names)


def memory_clause(p: dict) -> str:
    if p["coupon_memory"]:
        return ("Memory feature: if a Coupon is not paid on a Coupon Payment Date because the "
                "Coupon Condition is not satisfied, that Coupon is not lost. It will be paid, together "
                "with the Coupon then due, on the first subsequent Coupon Payment Date on which the "
                "Coupon Condition is satisfied.")
    return ("No memory feature: a Coupon that is not paid because the Coupon Condition is not satisfied "
            "on the relevant Coupon Observation Date is forfeited and will not be paid at a later date.")


def barrier_clause(p: dict, style: str) -> str:
    bt, lvl = p["barrier_type"], p["barrier_level_pct"]
    if bt == "none":
        return "Capital protection: the Notes are not subject to a knock-in barrier. Redemption at maturity is at 100% of the Notional Amount irrespective of the Final Level."
    obs = ("observed on the Final Valuation Date only (European observation)" if bt == "european"
           else "observed continuously on each Scheduled Trading Day from the Trade Date to the Final Valuation Date (American observation)")
    if lvl == "ABSENT":
        return (f"Knock-in Event: the Notes are subject to a knock-in barrier {obs}. The Knock-in Level is "
                "as specified in the Final Terms. If a Knock-in Event has occurred and the Notes have not "
                "been redeemed early, the Final Redemption Amount will be reduced in line with the performance of the Underlying.")
    return (f"Knock-in Event: the Notes are subject to a knock-in barrier {obs} at a Knock-in Level of "
            f"{pct(lvl, style)} of the Initial Level. If a Knock-in Event has occurred and the Notes have not "
            "been redeemed early, the Final Redemption Amount will be reduced in line with the performance of the Underlying.")


def autocall_clause(p: dict, style: str) -> str:
    dates, lvls = p["autocall_observation_dates"], p["autocall_level_pct"]
    if dates == "ABSENT":
        return "Early redemption: the Notes are not subject to automatic early redemption."
    if isinstance(lvls, list):
        pairs = ", ".join(f"{d(x, style)} at {pct(l, style)}" for x, l in zip(dates, lvls))
        return (f"Automatic Early Redemption: if on an Autocall Observation Date the closing level of the Underlying is at or "
                f"above the applicable Autocall Level, the Notes redeem early at 100% of the Notional Amount plus the Coupon then due. "
                f"Autocall Observation Dates and Autocall Levels (as a percentage of the Initial Level): {pairs}.")
    dl = ", ".join(d(x, style) for x in dates)
    return (f"Automatic Early Redemption: if on any Autocall Observation Date the closing level of the Underlying is at or "
            f"above {pct(lvls, style)} of the Initial Level, the Notes redeem early at 100% of the Notional Amount plus the "
            f"Coupon then due. Autocall Observation Dates: {dl}.")


BOILER_RISK = (
    "RISK FACTORS (SUMMARY). An investment in the Notes involves risks. Investors may lose some or all of their "
    "investment. The Notes are unsecured obligations of the Issuer and are subject to the credit risk of the Issuer. "
    "The secondary market, if any, may be illiquid; a bid price, where available, may be up to 3.00% below the "
    "theoretical value of the Notes. Past performance of the Underlying is not a reliable indicator of future "
    "performance. A 10% decline in the Underlying does not translate into a 10% decline in the value of the Notes; "
    "the relationship is non-linear and depends on remaining maturity, volatility and interest rates."
)
BOILER_FEES = (
    "Fees and distribution: the Issue Price includes distribution fees of up to 1.50% of the Notional Amount payable "
    "to the distributor. The Issuer's hedging costs are estimated at 0.35% per annum. These amounts are not Coupons "
    "and are not payable to Noteholders."
)
BOILER_LEGAL = (
    "This document is an indicative term sheet and does not constitute an offer. The Notes will be issued under the "
    "Issuer's " + PROGRAMME + " and are subject to the Base Prospectus and the applicable Final Terms. In the event of "
    "inconsistency between this term sheet and the Final Terms, the Final Terms prevail. Not for distribution in the "
    "United States or to U.S. persons. Governing law: Ontario. Calculation Agent: the Issuer."
)


# ----------------------------------------------------------------------------- rendering
def product_title(p: dict) -> str:
    names = " and ".join(INDEX_NAME[u] for u in p["underlyings"])
    kind = ("Autocallable " if p["autocall_observation_dates"] != "ABSENT" else "")
    kind += "Contingent Coupon Notes" + (" with Memory" if p["coupon_memory"] else "")
    return f"{'Worst-of ' if len(p['underlyings']) > 1 else ''}{kind} linked to {names}"


def underlying_phrase_v2(p: dict) -> str:
    if p["underlyings"] == ["BVERSA10"]:
        return 'the Bloomberg Versa 10 Index (Bloomberg: BVERSA10 Index) (the "Underlying")'
    return underlying_phrase(p)


def coupon_clause(p: dict, s: str) -> str:
    freq = freq_adverb(p["coupon_frequency"])
    cb = p.get("coupon_barrier_pct")
    cond = (f"provided the closing level of the Underlying on the relevant Coupon Observation Date is at or above the Coupon Barrier of {pct(cb, s)} of the Initial Level"
            if cb else "on each Coupon Payment Date on which the Coupon Condition is satisfied")
    return (f"The Notes pay a conditional Coupon of {rate_phrase(p, s)}, payable {freq} in arrears, {cond}. "
            f"Coupon amounts accrue on a {DAYCOUNT_WORD[p['day_count']]} day count basis.")


FMT = {"clauses": "prose", "prose": "clauses", "table": "table", "letter": "letter"}


def render_context(p: dict) -> dict:
    s = FMT[p["layout"]]
    dates, lvls = p["autocall_observation_dates"], p["autocall_level_pct"]
    if dates == "ABSENT":
        ac_dates, ac_level = "Not applicable", "Not applicable"
    else:
        ac_dates = ", ".join(d(x, s) for x in dates)
        ac_level = (" / ".join(pct(l, s) for l in lvls) + " of the Initial Level (per observation date)" if isinstance(lvls, list)
                    else f"{pct(lvls, s)} of the Initial Level")
    if p["barrier_type"] == "none":
        ki_type, ki_row = "None (capital protected at maturity)", ""
    else:
        ki_type = "European (Final Valuation Date only)" if p["barrier_type"] == "european" else "American (continuous observation)"
        ki_row = "" if p["barrier_level_pct"] == "ABSENT" else f"{pct(p['barrier_level_pct'], s)} of the Initial Level"
    return dict(
        layout=p["layout"], accent=ACCENT[p["layout"]], issuer=ISSUER, programme=PROGRAMME, desk=DESK,
        product_title=product_title(p), trade_id=p["trade_id"],
        notional=money(p["notional"], p["currency"], s), currency=p["currency"],
        trade_date=d(p["trade_date"], s), issue_date=d(p["issue_date"], s), maturity_date=d(p["maturity_date"], s),
        final_valuation_date=d(p["final_valuation_date"], s) if p.get("final_valuation_date") else None,
        underlyings_short="; ".join(f"{INDEX_NAME[u]} ({u})" for u in p["underlyings"]),
        underlying_phrase=underlying_phrase_v2(p),
        underlying_prose=("The Underlying is " + underlying_phrase(p).replace("the worst performing of ", "the worst performing of ")
                          if p["underlyings"] != ["BVERSA10"] else ""),
        initial_level=pct(p["initial_level_pct"], s),
        index=VERSA10 if "BVERSA10" in p["underlyings"] else None,
        coupon_phrase=rate_phrase(p, s), coupon_clause=coupon_clause(p, s),
        coupon_frequency_word=p["coupon_frequency"].capitalize(), coupon_memory=p["coupon_memory"],
        coupon_barrier=pct(p["coupon_barrier_pct"], s) if p.get("coupon_barrier_pct") else None,
        memory_clause=memory_clause(p), autocall_clause=autocall_clause(p, s), barrier_clause=barrier_clause(p, s),
        day_count_word=DAYCOUNT_WORD[p["day_count"]], autocall_dates_text=ac_dates, autocall_level_text=ac_level,
        knockin_type_text=ki_type, knockin_level_row=ki_row,
        settlement_word=p["settlement"].capitalize(), bdc_word=BDC_WORD[p["business_day_convention"]],
        dist_fee=f"{p.get('dist_fee_pct', 1.50):.2f}%", hedge_cost=f"{p.get('hedge_cost_pct', 0.35):.2f}%",
    )


_env = Environment(loader=FileSystemLoader(str(TEMPLATES)), undefined=StrictUndefined, autoescape=False,
                   trim_blocks=True, lstrip_blocks=True)


def render_html(p: dict) -> str:
    if p.get("product") == "otc_option":
        return _env.get_template("option.html.j2").render(**option_context(p))
    return _env.get_template("note.html.j2").render(**render_context(p))


DAYS_WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}


def option_context(p: dict) -> dict:
    s = "prose"  # the approved option layout uses "8 May 2026" / "100%"
    return dict(
        trade_id=p["trade_id"], buyer=p["buyer"], trade_date=d(p["trade_date"], s), effective_date=d(p["effective_date"], s),
        notional=money(p["notional"], p["currency"], s), valuation_date=d(p["valuation_date"], s),
        expiration_date=d(p["expiration_date"], s), premium_payment_date=d(p["premium_payment_date"], s),
        premium_pct=pct(p["premium_pct"], s), premium_amount=money(p["premium_amount"], p["currency"], s),
        strike=pct(p["strike_level_pct"], s), participation=pct(p["participation_rate_pct"], s),
        settlement_days_word=DAYS_WORD[p["cash_settlement_days"]], settlement_currency=p["settlement_currency"],
        option_style_word=p["option_style"].capitalize(), option_type_word=p["option_type"].capitalize(),
        index=VERSA10,
    )


def html_to_text(html: str) -> str:
    """Canonical TXT of the document: the same content, one line per block/table cell."""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["style", "script"]):
        t.decompose()
    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text) + "\n"


def html_to_pdf(html: str, out: Path) -> int:
    from weasyprint import HTML
    doc = HTML(string=html, base_url=str(TEMPLATES)).render()
    doc.write_pdf(str(out))
    return len(doc.pages)


# ----------------------------------------------------------------------------- outputs
def truth_of(p: dict) -> dict:
    """The document's own truth in canonical (comparison-key) space: coupon per annum."""
    if p.get("product") == "otc_option":
        return {k: p[k] for k in OPTION_FIELDS}
    t = {k: (ISSUER if k == "issuer" else p[k]) for k in FIELDS}
    if p["coupon_rate_basis"] == "per_period":
        t["coupon_rate_pct"] = round(p["coupon_rate_pct"] * PERIODS[p["coupon_frequency"]], 6)
    return t


def booking_of(p: dict) -> dict:
    """Booking = canonical truth (no basis field: bookings are per annum) + planted overrides."""
    b = truth_of(p)
    b.pop("coupon_rate_basis", None)
    b.update(deepcopy(p["booking_overrides"]))
    return {k: v for k, v in b.items() if v != "ABSENT"}  # bookings simply omit absent fields


def main() -> None:
    for sub in ("termsheets", "pdf", "html", "bookings", "truth"):
        (GOLDEN / sub).mkdir(parents=True, exist_ok=True)
    manifest = {"version": 2,
                "generator": "scripts/gen_golden.py",
                "history": [{"date": "2026-09-11", "note": "initial labels, generated from parameters (ADR-13)"},
                            {"date": "2026-09-12", "note": "v0.2 CS1: PDF+HTML+TXT per document from approved templates; G12 economics replaced by the approved template's (ADR-20); Versa docs carry the Underlying Index section"},
                            {"date": "2026-09-12", "note": "v0.2 CS3: OTC option product (schema option_v1): G13 = approved OP-2026-0114 (clean control), G14 participation 100->95, G15 premium off the wrong notional (MISMATCH + RELATION_VIOLATION)"}],
                "documents": []}
    pages = {}
    for p in DOCS + OPTIONS:
        html = render_html(p)
        (GOLDEN / "html" / f"{p['id']}.html").write_text(html)
        pages[p["id"]] = html_to_pdf(html, GOLDEN / "pdf" / f"{p['id']}.pdf")
        text = html_to_text(html)
        (GOLDEN / "termsheets" / f"{p['id']}.txt").write_text(text)
        (GOLDEN / "truth" / f"{p['id']}.json").write_text(json.dumps(truth_of(p), indent=2) + "\n")
        (GOLDEN / "bookings" / f"{p['trade_id']}.json").write_text(json.dumps(booking_of(p), indent=2) + "\n")
        entry = {"id": p["id"], "layout": p.get("layout", "approved-option"), "product_type": p.get("product", "note"), "trade_id": p["trade_id"],
                 "termsheet": f"termsheets/{p['id']}.txt", "pdf": f"pdf/{p['id']}.pdf", "html": f"html/{p['id']}.html",
                 "booking": f"bookings/{p['trade_id']}.json",
                 "truth": f"truth/{p['id']}.json",
                 "planted": [dict(pl, severity="critical" if pl["field"] not in
                                  ("issue_date", "autocall_observation_dates", "autocall_level_pct", "settlement", "business_day_convention",
                                   "effective_date", "automatic_exercise", "premium_payment_date", "cash_settlement_days",
                                   "settlement_currency", "calculation_agent")
                                  else "minor") for pl in p["planted"]]}
        if p.get("traps"):
            entry["traps"] = p["traps"]
        if p.get("clean_control"):
            entry["clean_control"] = True
        manifest["documents"].append(entry)
    (GOLDEN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    alldocs = DOCS + OPTIONS
    words = [len((GOLDEN / "termsheets" / f"{p['id']}.txt").read_text().split()) for p in alldocs]
    print(f"wrote {len(alldocs)} docs (html+pdf+txt) -> {GOLDEN}; words min/max {min(words)}/{max(words)}; pages {pages}; "
          f"planted {sum(len(p['planted']) for p in alldocs)}; products {sorted({p.get('product', 'note') for p in alldocs})}")


if __name__ == "__main__":
    main()
