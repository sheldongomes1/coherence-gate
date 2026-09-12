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
