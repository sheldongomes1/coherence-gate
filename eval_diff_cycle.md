# eval_diff.md — model/effort change, before vs after

**A model deprecation is this diff: rerun, compare, accept or hold. The judgment (schema, prompts, tolerances, golden set) is versioned and did not change.**

| | baseline (txt, no tolerance) | proposal applied (3-day date tolerance) | delta |
|---|---|---|---|
| run id | 20260912-180705 | 20260912-200709 | |
| strict catch (field + type) | 17/17 | 16/17 | -1 |
| field-level catch (diagnostic) | 17/17 | 16/17 | -1 |
| false flags on clean fields (lower is better) | 28/411 | 27/417 | -1 |
| cross-family agreement | 368/396 | 369/396 | +1 |
| auto-clear correctness | 17/17 | 16/17 | -1 |
| extraction accuracy gemini | 368/396 | 369/396 | +1 |
| extraction accuracy claude | 396/396 | 370/396 | -26 |
| cost per document (USD) | $0.1307 | $0.1499 | +0.0192 |

## Planted findings whose reported outcome moved

| doc | field | before | after |
|---|---|---|---|
| G02 | autocall_observation_dates | MISMATCH | CLEAN |

## Wholesale extractor events (not attributable to the change under test)

- claude G11: lost every field in the candidate run — a deadline/API/truncation event in that run; the rows above that move because of it (false flags, agreement, accuracy for that family) are NOT effects of the change
- gemini G11: lost every field in the candidate run — a deadline/API/truncation event in that run; the rows above that move because of it (false flags, agreement, accuracy for that family) are NOT effects of the change
- gemini G13: lost every field in the baseline run — a deadline/API/truncation event in that run; the rows above that move because of it (false flags, agreement, accuracy for that family) are NOT effects of the change

## Extraction fields whose correctness moved

| family | doc:field | before | after |
|---|---|---|---|
| claude | G11:autocall_level_pct | ok | wrong |
| claude | G11:autocall_observation_dates | ok | wrong |
| claude | G11:barrier_level_pct | ok | wrong |
| claude | G11:barrier_type | ok | wrong |
| claude | G11:business_day_convention | ok | wrong |
| claude | G11:coupon_frequency | ok | wrong |
| claude | G11:coupon_memory | ok | wrong |
| claude | G11:coupon_rate_pct | ok | wrong |
| claude | G11:currency | ok | wrong |
| claude | G11:day_count | ok | wrong |
| claude | G11:index_administrator | ok | wrong |
| claude | G11:index_deduction_factor_pct | ok | wrong |
| claude | G11:index_rebalance_frequency | ok | wrong |
| claude | G11:index_return_treatment | ok | wrong |
| claude | G11:index_return_type | ok | wrong |
| claude | G11:index_transaction_cost_rate_pct | ok | wrong |
| claude | G11:index_vol_target_pct | ok | wrong |
| claude | G11:initial_level_pct | ok | wrong |
| claude | G11:issue_date | ok | wrong |
| claude | G11:issuer | ok | wrong |
| claude | G11:maturity_date | ok | wrong |
| claude | G11:notional | ok | wrong |
| claude | G11:settlement | ok | wrong |
| claude | G11:trade_date | ok | wrong |
| claude | G11:trade_id | ok | wrong |
| claude | G11:underlyings | ok | wrong |
| gemini | G09:barrier_type | ok | wrong |
| gemini | G11:autocall_level_pct | ok | wrong |
| gemini | G11:autocall_observation_dates | ok | wrong |
| gemini | G11:barrier_level_pct | ok | wrong |
| gemini | G11:barrier_type | ok | wrong |
| gemini | G11:business_day_convention | ok | wrong |
| gemini | G11:coupon_frequency | ok | wrong |
| gemini | G11:coupon_memory | ok | wrong |
| gemini | G11:coupon_rate_pct | ok | wrong |
| gemini | G11:currency | ok | wrong |
| gemini | G11:day_count | ok | wrong |
| gemini | G11:index_administrator | ok | wrong |
| gemini | G11:index_deduction_factor_pct | ok | wrong |
| gemini | G11:index_rebalance_frequency | ok | wrong |
| gemini | G11:index_return_treatment | ok | wrong |
| gemini | G11:index_return_type | ok | wrong |
| gemini | G11:index_transaction_cost_rate_pct | ok | wrong |
| gemini | G11:index_vol_target_pct | ok | wrong |
| gemini | G11:initial_level_pct | ok | wrong |
| gemini | G11:issue_date | ok | wrong |
| gemini | G11:issuer | ok | wrong |
| gemini | G11:maturity_date | ok | wrong |
| gemini | G11:notional | ok | wrong |
| gemini | G11:settlement | ok | wrong |
| gemini | G11:trade_date | ok | wrong |
| gemini | G11:trade_id | ok | wrong |
| gemini | G11:underlyings | ok | wrong |
| gemini | G13:automatic_exercise | wrong | ok |
| gemini | G13:buyer | wrong | ok |
| gemini | G13:calculation_agent | wrong | ok |
| gemini | G13:cash_settlement_days | wrong | ok |
| gemini | G13:currency | wrong | ok |
| gemini | G13:effective_date | wrong | ok |
| gemini | G13:expiration_date | wrong | ok |
| gemini | G13:index_administrator | wrong | ok |
| gemini | G13:index_deduction_factor_pct | wrong | ok |
| gemini | G13:index_rebalance_frequency | wrong | ok |
| gemini | G13:index_return_treatment | wrong | ok |
| gemini | G13:index_return_type | wrong | ok |
| gemini | G13:index_transaction_cost_rate_pct | wrong | ok |
| gemini | G13:index_vol_target_pct | wrong | ok |
| gemini | G13:notional | wrong | ok |
| gemini | G13:option_style | wrong | ok |
| gemini | G13:option_type | wrong | ok |
| gemini | G13:participation_rate_pct | wrong | ok |
| gemini | G13:premium_amount | wrong | ok |
| gemini | G13:premium_payment_date | wrong | ok |
| gemini | G13:premium_pct | wrong | ok |
| gemini | G13:seller | wrong | ok |
| gemini | G13:settlement_currency | wrong | ok |
| gemini | G13:strike_level_pct | wrong | ok |
| gemini | G13:trade_date | wrong | ok |
| gemini | G13:trade_id | wrong | ok |
| gemini | G13:underlyings | wrong | ok |
| gemini | G13:valuation_date | wrong | ok |

n: 15 documents in both runs. Directional, not statistically significant.
