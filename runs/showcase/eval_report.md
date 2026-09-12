# eval_report.md — run 20260912-191532 — source: pdf

Every number below is a count over a stated n, from this one run, with no retries. Red means the claim it supports does not hold on this run.

## 1. Headline: did the gate catch what was planted, and did it flag what was clean?

| metric | result | n |
|---|---|---|
| **catch_rate (right field AND right finding type)** | 🟢 17/17 (100.0%) | 17 |
| catch_rate_field_only (diagnostic: any non-clean finding on the planted field) | 🟢 17/17 (100.0%) | 17 |
| **false_flag_rate (clean fields that were flagged)** | 🟢 0/417 (0.0%) | 417 |
| clean control documents NOT auto-cleared | 🟢 0/3 (0.0%) | 3 |
| **auto_clear_correctness (nothing planted was auto-cleared; must be 100%)** | 🟢 17/17 (100.0%) | 17 |
| cross-family agreement (fields where both families read the same value) | 🟢 396/396 (100.0%) | 396 |
| G09 normalizer trap resolved as CLEAN (per-quarter vs per-annum) | 🟢 1/1 (100.0%) | 1 |

## 2. Extraction accuracy per family (vs the golden truth files)

| family | correct fields | n |
|---|---|---|
| gemini | 🟢 396/396 (100.0%) | 396 |
| claude | 🟢 396/396 (100.0%) | 396 |

## 3. Per product type

| product | documents | planted | strict catch | clean fields | false flags |
|---|---|---|---|---|---|
| note | 12 | 12 | 12/12 | 317 | 0/317 |
| otc_option | 3 | 5 | 5/5 | 100 | 0/100 |

## 4. Parse tax

Source for this run: parsed PDF. Run `cg ablation --txt-run <txt run> --pdf-run <this run>` to append the text-vs-parsed comparison here.

## 5. Reference lane (term sheet claims vs the Bloomberg Versa methodology)

| metric | result |
|---|---|
| lane ran (methodology parsed + extracted by both families, merged by code) | yes |
| planted reference incoherences caught (right field, type REFERENCE_INCONSISTENT) | 2/2 |
| reference checks performed (documents with an Underlying Index section × mapped rules) | 36 |
| reference flags raised | 2 |
| flags on parameters the methodology defers or merely defaults (must be 0) | 🟢 0 |
| checks not evaluable (families disagreed on the rule or the claim) | 0 |

A parameter the methodology defers to the index-specific document (e.g. Volatility Target) is reported as `deferred`, never as a flag; the term sheet's value is checked against the booking's static data instead.

## 6. Effort sweep (ADR-15 / ADR-19): one variable changed, everything else identical

| setting | run | strict catch | false flags | agreement | auto-clear ok | cost/doc | note |
|---|---|---|---|---|---|---|---|
| Gemini thinking = medium (SHIPPED) | 20260911-220517 | 9/9 | 3/218 | 225/228 | 9/9 | $0.114 | Gemini median 27 s, worst 720 s |
| Gemini thinking = low | 20260911-222706 | 8/9 | 3/218 | 224/228 | 9/9 | $0.072 | Gemini median 3 s, worst 6 s; one field mis-mapped on the step-down schedule (G07) |

## 7. Cost

| scope | USD |
|---|---|
| per document (both extractions + triage where run, traced tokens × pinned prices) | $0.1472 (min $0.0812, max $0.2943) |
| per book of 15 documents (this run) | $2.2075 |
| parsing | not reported by the vendor API; parse latency is in the trace |

## 8. Models (pinned)

| family | model | pinned | $/1M in | $/1M out |
|---|---|---|---|---|
| gemini | gemini-3.8-flash | True | 0.75 | 3.75 |
| claude | claude-opus-5 | True | 5.0 | 25.0 |
| claude | claude-opus-5 | True | 5.0 | 25.0 |

## 9. Planted findings (mutants)

| doc | field | expected | reported | strict | field-only | detail |
|---|---|---|---|---|---|---|
| G01 | barrier_level_pct | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 65 ≠ booking 70 |
| G02 | autocall_observation_dates | MISMATCH | MISMATCH | 🟢 | 🟢 | TS ['2027-05-12', '2027-11-12', '2028-05-12'] ≠ booking ['2027-05-12', '2027-11-15', '2028-05-12'] |
| G03 | day_count | MISMATCH | MISMATCH | 🟢 | 🟢 | TS ACT/360 ≠ booking 30/360 |
| G03 | index_vol_target_pct | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 10 ≠ booking 12 |
| G04 | coupon_memory | MISMATCH | MISMATCH | 🟢 | 🟢 | TS True ≠ booking False |
| G05 | notional | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 10000000 ≠ booking 1000000 |
| G06 | currency | MISMATCH | MISMATCH | 🟢 | 🟢 | TS USD ≠ booking CAD |
| G07 | autocall_level_pct | MISMATCH | MISMATCH | 🟢 | 🟢 | TS [Decimal('100'), Decimal('95'), Decimal('90')] ≠ booking [Decimal('100'), Decimal('100'), Decimal('100')] |
| G08 | underlyings | MISMATCH | MISMATCH | 🟢 | 🟢 | TS ['SX5E'] ≠ booking ['SPX'] |
| G09 | ref:index_return_treatment | REFERENCE_INCONSISTENT | REFERENCE_INCONSISTENT | 🟢 | 🟢 | term sheet calls a type_i index 'total_return'; the methodology says type_i is excess_return |
| G09 | index_return_treatment | MISMATCH | MISMATCH | 🟢 | 🟢 | TS total_return ≠ booking excess_return |
| G10 | barrier_level_pct | TS_ABSENT | TS_ABSENT | 🟢 | 🟢 | term sheet declares barrier_level_pct absent; booking has 70 |
| G14 | participation_rate_pct | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 100 ≠ booking 95 |
| G14 | ref:index_rebalance_frequency | REFERENCE_INCONSISTENT | REFERENCE_INCONSISTENT | 🟢 | 🟢 | term sheet claims index_rebalance_frequency = monthly; methodology rule rebalance_frequency = daily |
| G14 | index_rebalance_frequency | MISMATCH | MISMATCH | 🟢 | 🟢 | TS monthly ≠ booking daily |
| G15 | premium_amount | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 1037500 ≠ booking 830000 |
| G15 | rel:premium_arithmetic | RELATION_VIOLATION | RELATION_VIOLATION | 🟢 | 🟢 | violated on booking — premium_arithmetic: term sheet [4.15×0.01 × 25000000 = 1.0375E+6 vs premium_amount 1.0375E+6]; booking [4.15×0.01 × 25 |

## 10. False flags on clean fields (0)

none

## 11. Honest ceiling

- n = 15 synthetic documents, 17 planted findings plus 1 normalizer trap, 3 clean controls. **Directional, not statistically significant.**
- Documents are synthetic, generated from one parameter table through four layout families in one house style; phrasing is machine-uniform. Real desk paper has more layouts, scans, multi-page annexes and hand edits.
- One prompt per extractor family; no prompt ensemble. One run per number: no retries, no reruns, no best-of.
- The eval can only see error classes it plants. Unplanted classes (wrong observation-date count, swapped issuer/guarantor, a coupon barrier read as a knock-in) are invisible to it unless they happen to hit a planted field.
- The triage agent sees only the finding, its citations and the booking field; it cannot exculpate a finding using an unflagged clause elsewhere in the document.
- Parsing is single-sourced (one vendor, one mode) behind one interface; the local fallback exists but its parse tax is not measured here.
- Field-level false-flag denominator counts every non-planted comparison key on every document, including fields absent in both term sheet and booking.
- Cost is computed from traced tokens × pinned list prices (current list prices); parsing cost is not reported by the vendor.

## Parse tax (ablation: canonical text vs parsed PDF)

Runs: txt = 20260912-180705, pdf = 20260912-191532. Same models, prompts, golden set; only the source text differs.

| metric | txt | pdf | delta |
|---|---|---|---|
| catch_rate (strict) | 17/17 | 17/17 | +0 |
| catch_rate_field_only | 17/17 | 17/17 | +0 |
| false_flag_fields (lower is better) | 28/411 | 0/417 | -28 |
| clean docs NOT auto-cleared (lower is better) | 1/3 | 0/3 | -1 |
| cross-family agreement | 368/396 | 396/396 | +28 |
| extraction_accuracy (gemini) | 368/396 | 396/396 | +28 |
| extraction_accuracy (claude) | 396/396 | 396/396 | +0 |
| cost per document (USD, models only) | $0.1307 | $0.1472 | +0.0165 |

**Fields degraded by parsing (0):** none
**Fields improved by parsing (28):** gemini G13:automatic_exercise, gemini G13:buyer, gemini G13:calculation_agent, gemini G13:cash_settlement_days, gemini G13:currency, gemini G13:effective_date, gemini G13:expiration_date, gemini G13:index_administrator, gemini G13:index_deduction_factor_pct, gemini G13:index_rebalance_frequency, gemini G13:index_return_treatment, gemini G13:index_return_type, gemini G13:index_transaction_cost_rate_pct, gemini G13:index_vol_target_pct, gemini G13:notional, gemini G13:option_style, gemini G13:option_type, gemini G13:participation_rate_pct, gemini G13:premium_amount, gemini G13:premium_payment_date, gemini G13:premium_pct, gemini G13:seller, gemini G13:settlement_currency, gemini G13:strike_level_pct, gemini G13:trade_date, gemini G13:trade_id, gemini G13:underlyings, gemini G13:valuation_date

**Wholesale events, not parse tax:** gemini G13 lost every field in the txt run (extractor failure in that run: deadline/API/truncation), so its 'improvement' under pdf is not a parsing effect

**Interpretation.** The parsed PDF reproduced the canonical text closely enough that extraction accuracy did not move; on this synthetic set (clean, machine-rendered PDFs) the parse tax is nil. Real desk paper (scans, multi-column, annexes) would be where a tax appears, and this ablation is the instrument that would show it.
Parsing cost is not reported by the vendor API and is therefore not in the cost line; parse latency is in each trace.
