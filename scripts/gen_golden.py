"""Generate the golden set from parameters (ADR-13).

One parameter table -> 12 term sheets (4 layout families), 12 truth files, 12 booking
records, manifest.json. Text, truth, booking and manifest come from the same dict, so labels
cannot drift from the prose. Planted discrepancies are applied to the BOOKING only; the
term sheet is always the document's own truth.

Run: uv run python scripts/gen_golden.py   (idempotent; overwrites golden/)
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
ISSUER = "Northbridge Capital Markets (Canada) Inc."  # fictional (ADR-12)
PROGRAMME = "Structured Notes Programme, Series 2026"
PERIODS = {"monthly": 12, "quarterly": 4, "semiannual": 2, "annual": 1}
FREQ_WORD = {"monthly": "month", "quarterly": "quarter", "semiannual": "half-year", "annual": "year"}
DAYCOUNT_WORD = {"ACT/360": "Actual/360", "ACT/365": "Actual/365 (Fixed)", "30/360": "30/360"}
BDC_WORD = {"following": "Following", "mod_following": "Modified Following", "preceding": "Preceding"}
INDEX_NAME = {
    "SPX": "S&P 500 Index",
    "SX5E": "EURO STOXX 50 Index",
    "SPTSX60": "S&P/TSX 60 Index",
    "BVERSA10": "BVERSA10 Index",
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
    dict(id="G12", layout="letter", trade_id="SN-2026-0112", notional=6_000_000, currency="CAD",
         trade_date="2026-03-24", issue_date="2026-03-31", maturity_date="2029-04-02",
         underlyings=["BVERSA10"], initial_level_pct=100, barrier_type="european", barrier_level_pct=65,
         coupon_rate_pct=6.1, coupon_rate_basis="per_annum", coupon_frequency="semiannual", coupon_memory=False,
         autocall_observation_dates="ABSENT", autocall_level_pct="ABSENT",
         day_count="ACT/365", settlement="cash", business_day_convention="following",
         booking_overrides={}, planted=[], clean_control=True),
]

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


# ----------------------------------------------------------------------------- layouts
def layout_prose(p: dict) -> str:
    s = "prose"
    n_und = len(p["underlyings"])
    return f"""INDICATIVE TERM SHEET

{ISSUER}
{PROGRAMME}

{'Worst-of ' if n_und > 1 else ''}Autocallable Barrier Note linked to {', '.join(INDEX_NAME[u] for u in p['underlyings'])}
Reference: {p['trade_id']}
Dated {d(p['trade_date'], s)}

1. Summary of the transaction

{ISSUER} (the "Issuer") will issue notes (the "Notes") with reference {p['trade_id']} in an aggregate Notional Amount of {money(p['notional'], p['currency'], s)}. The Notes are linked to the performance of {underlying_phrase(p)}. The Trade Date is {d(p['trade_date'], s)}, the Issue Date is {d(p['issue_date'], s)} and the Scheduled Maturity Date is {d(p['maturity_date'], s)}, subject to the Business Day Convention below.

The Initial Level of each Underlying is {pct(p['initial_level_pct'], s)} of its official closing level on the Trade Date.

2. Coupon

The Notes pay a conditional Coupon of {rate_phrase(p, s)}, on each Coupon Payment Date on which the Coupon Condition is satisfied. Coupon amounts accrue on a {DAYCOUNT_WORD[p['day_count']]} day count basis. {memory_clause(p)}

3. Early redemption and barrier

{autocall_clause(p, s)}

{barrier_clause(p, s)}

4. Settlement

Settlement at maturity or upon early redemption is in {p['settlement']}, in {p['currency']}. Payment dates are adjusted in accordance with the {BDC_WORD[p['business_day_convention']]} Business Day Convention. Business Days: Toronto, New York and London.

5. Other

{BOILER_FEES}

{BOILER_RISK}

{BOILER_LEGAL}
"""


def layout_table(p: dict) -> str:
    s = "table"
    und = "; ".join(f"{INDEX_NAME[u]} ({u})" for u in p["underlyings"])
    basket = "Worst-of basket" if len(p["underlyings"]) > 1 else "Single index"
    ac_dates = ", ".join(d(x, s) for x in p["autocall_observation_dates"]) if p["autocall_observation_dates"] != "ABSENT" else "Not applicable"
    if p["autocall_level_pct"] == "ABSENT":
        ac_lvl = "Not applicable"
    elif isinstance(p["autocall_level_pct"], list):
        ac_lvl = " / ".join(pct(l, s) for l in p["autocall_level_pct"])
    else:
        ac_lvl = pct(p["autocall_level_pct"], s) + " of Initial Level"
    if p["barrier_type"] == "none":
        ki_type, ki_lvl_row = "None (capital protected at maturity)", ""
    else:
        ki_type = "European (Final Valuation Date only)" if p["barrier_type"] == "european" else "American (continuous observation)"
        ki_lvl_row = "" if p["barrier_level_pct"] == "ABSENT" else f"Knock-in Level               | {pct(p['barrier_level_pct'], s)} of Initial Level\n"
    return f"""{ISSUER.upper()}
{PROGRAMME}
FINAL TERMS SUMMARY — {p['trade_id']}

Product                      | {basket} Autocallable Note
Issuer                       | {ISSUER}
Trade Reference              | {p['trade_id']}
Notional Amount              | {money(p['notional'], p['currency'], s)}
Currency                     | {p['currency']}
Trade Date                   | {d(p['trade_date'], s)}
Issue Date                   | {d(p['issue_date'], s)}
Maturity Date                | {d(p['maturity_date'], s)}
Underlying(s)                | {und}
Initial Level                | {pct(p['initial_level_pct'], s)} of closing level on Trade Date
Coupon                       | {rate_phrase(p, s)}
Coupon Frequency             | {p['coupon_frequency'].capitalize()}
Coupon Memory                | {'Yes' if p['coupon_memory'] else 'No'}
Day Count Fraction           | {DAYCOUNT_WORD[p['day_count']]}
Autocall Observation Dates   | {ac_dates}
Autocall Level               | {ac_lvl}
Knock-in Type                | {ki_type}
{ki_lvl_row}Settlement                   | {p['settlement'].capitalize()}
Business Day Convention      | {BDC_WORD[p['business_day_convention']]}
Business Days                | Toronto, New York, London
Calculation Agent            | Issuer
Governing Law                | Ontario

Notes to the table

{memory_clause(p)}

{barrier_clause(p, s)}

{autocall_clause(p, s)}

{BOILER_FEES}

{BOILER_RISK}

{BOILER_LEGAL}
"""


def layout_clauses(p: dict) -> str:
    s = "clauses"
    return f"""TERMS AND CONDITIONS OF THE NOTES
{ISSUER} — {PROGRAMME}
Tranche reference {p['trade_id']}

1. Issuer. The Notes are issued by {ISSUER}.

2. Notional Amount and Currency. The aggregate Notional Amount is {money(p['notional'], p['currency'], s)}. The Specified Currency is {p['currency']} and all payments under the Notes are made in {p['currency']}.

3. Dates. Trade Date: {d(p['trade_date'], s)}. Issue Date: {d(p['issue_date'], s)}. Maturity Date: {d(p['maturity_date'], s)}, subject to adjustment in accordance with Condition 9.

4. Underlying. The Notes are linked to {underlying_phrase(p)}. The Initial Level is {pct(p['initial_level_pct'], s)} of the official closing level of each Underlying on the Trade Date.

5. Coupon. Subject to the Coupon Condition, the Notes bear a Coupon of {rate_phrase(p, s)}. Coupons are payable {freq_adverb(p['coupon_frequency'])} in arrear and are calculated on the basis of {DAYCOUNT_WORD[p['day_count']]}.

6. Memory. {memory_clause(p)}

7. Automatic Early Redemption. {autocall_clause(p, s)}

8. Knock-in. {barrier_clause(p, s)}

9. Business Day Convention. Where any payment date would otherwise fall on a day that is not a Business Day, it shall be adjusted in accordance with the {BDC_WORD[p['business_day_convention']]} Business Day Convention. Business Days are days on which commercial banks are open in Toronto, New York and London.

10. Settlement. {p['settlement'].capitalize()} settlement.

11. Fees. {BOILER_FEES}

12. Risk. {BOILER_RISK}

13. General. {BOILER_LEGAL}
"""


def layout_letter(p: dict) -> str:
    s = "letter"
    und_lines = "\n".join(f"    - {INDEX_NAME[u]} (Bloomberg ticker {u})" for u in p["underlyings"])
    if p["autocall_observation_dates"] == "ABSENT":
        ac_annex = "  Automatic early redemption: not applicable."
    elif isinstance(p["autocall_level_pct"], list):
        ac_annex = "  Autocall schedule (observation date, trigger as % of Initial Level):\n" + "\n".join(
            f"    {d(x, s)}   {pct(l, s)}" for x, l in zip(p["autocall_observation_dates"], p["autocall_level_pct"]))
    else:
        ac_annex = f"  Autocall trigger: {pct(p['autocall_level_pct'], s)} of Initial Level on each of: " + ", ".join(d(x, s) for x in p["autocall_observation_dates"]) + "."
    return f"""{ISSUER}
Global Markets — Structured Products Desk
Toronto

{d(p['trade_date'], s)}

Dear Client,

Re: {p['trade_id']} — {'Worst-of ' if len(p['underlyings']) > 1 else ''}Autocallable Note on {' and '.join(INDEX_NAME[u] for u in p['underlyings'])}

Further to our conversation, we are pleased to confirm the indicative terms of the above transaction. {ISSUER} will issue Notes in a total Notional Amount of {money(p['notional'], p['currency'], s)} under its {PROGRAMME}. The Notes were traded on {d(p['trade_date'], s)}, will be issued on {d(p['issue_date'], s)} and mature on {d(p['maturity_date'], s)}.

The Notes pay a conditional coupon of {rate_phrase(p, s)}, accruing on a {DAYCOUNT_WORD[p['day_count']]} basis. {memory_clause(p)}

{autocall_clause(p, s)}

{barrier_clause(p, s)}

All payments are made in {p['currency']} by {p['settlement']} settlement and payment dates follow the {BDC_WORD[p['business_day_convention']]} convention (Toronto, New York and London business days).

Please review the Annex and revert with any comments before we proceed to booking.

Kind regards,
Structured Products Desk

ANNEX — KEY TERMS
  Reference: {p['trade_id']}
  Issuer: {ISSUER}
  Underlying(s):
{und_lines}
  Initial Level: {pct(p['initial_level_pct'], s)} of closing level on {d(p['trade_date'], s)}
  Notional: {money(p['notional'], p['currency'], s)}
  Coupon: {rate_phrase(p, s)}; memory: {'yes' if p['coupon_memory'] else 'no'}
  Day count: {DAYCOUNT_WORD[p['day_count']]}
{ac_annex}
  Knock-in: {('none' if p['barrier_type'] == 'none' else p['barrier_type'].capitalize() + (' at ' + pct(p['barrier_level_pct'], s) if p['barrier_level_pct'] != 'ABSENT' else ', level per Final Terms'))}

{BOILER_FEES}

{BOILER_RISK}

{BOILER_LEGAL}
"""


LAYOUTS = {"prose": layout_prose, "table": layout_table, "clauses": layout_clauses, "letter": layout_letter}


# ----------------------------------------------------------------------------- outputs
def truth_of(p: dict) -> dict:
    """The document's own truth in canonical (comparison-key) space: coupon per annum."""
    t = {k: (ISSUER if k == "issuer" else p[k]) for k in FIELDS}
    if p["coupon_rate_basis"] == "per_period":
        t["coupon_rate_pct"] = round(p["coupon_rate_pct"] * PERIODS[p["coupon_frequency"]], 6)
    return t


def booking_of(p: dict) -> dict:
    """Booking = canonical truth (no basis field: bookings are per annum) + planted overrides."""
    b = truth_of(p)
    b.pop("coupon_rate_basis")
    b.update(deepcopy(p["booking_overrides"]))
    return {k: v for k, v in b.items() if v != "ABSENT"}  # bookings simply omit absent fields


def main() -> None:
    for sub in ("termsheets", "bookings", "truth"):
        (GOLDEN / sub).mkdir(parents=True, exist_ok=True)
    manifest = {"version": 1,
                "generator": "scripts/gen_golden.py",
                "history": [{"date": "2026-09-11", "note": "initial labels, generated from parameters (ADR-13)"}],
                "documents": []}
    for p in DOCS:
        text = LAYOUTS[p["layout"]](p)
        (GOLDEN / "termsheets" / f"{p['id']}.txt").write_text(text)
        (GOLDEN / "truth" / f"{p['id']}.json").write_text(json.dumps(truth_of(p), indent=2) + "\n")
        (GOLDEN / "bookings" / f"{p['trade_id']}.json").write_text(json.dumps(booking_of(p), indent=2) + "\n")
        entry = {"id": p["id"], "layout": p["layout"], "trade_id": p["trade_id"],
                 "termsheet": f"termsheets/{p['id']}.txt", "booking": f"bookings/{p['trade_id']}.json",
                 "truth": f"truth/{p['id']}.json",
                 "planted": [dict(pl, severity="critical" if pl["field"] not in
                                  ("issue_date", "autocall_observation_dates", "autocall_level_pct", "settlement", "business_day_convention")
                                  else "minor") for pl in p["planted"]]}
        if p.get("traps"):
            entry["traps"] = p["traps"]
        if p.get("clean_control"):
            entry["clean_control"] = True
        manifest["documents"].append(entry)
    (GOLDEN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    words = [len((GOLDEN / "termsheets" / f"{p['id']}.txt").read_text().split()) for p in DOCS]
    print(f"wrote {len(DOCS)} docs; words min/max {min(words)}/{max(words)}; planted {sum(len(p['planted']) for p in DOCS)}")


if __name__ == "__main__":
    main()
