# eval_report.md — run 20260911-223332

## Results

| metric | result | n |
|---|---|---|
| catch_rate (doc+field+type) | 🟢 9/9 (100.0%) | 9 |
| catch_rate_field_only (diagnostic) | 🟢 9/9 (100.0%) | 9 |
| false_flag_rate (clean fields flagged) | 🟢 0/218 (0.0%) | 218 |
| clean documents NOT auto-cleared | 🟢 0/2 (0.0%) | 2 |
| G09 normalizer trap resolved as CLEAN | 🟢 1/1 (100.0%) | 1 |
| auto_clear_correctness (planted never auto-cleared) | 🟢 9/9 (100.0%) | 9 |
| cross-family agreement (fields) | 🟢 228/228 (100.0%) | 228 |
| extraction_accuracy (gemini) vs truth | 🟢 228/228 (100.0%) | 228 |
| extraction_accuracy (claude) vs truth | 🟢 228/228 (100.0%) | 228 |
| cost per document (USD) | $0.1131 (min $0.0690, max $0.1856, total $1.3576) | 12 |

## Models

| family | model | pinned | $/1M in | $/1M out |
|---|---|---|---|---|
| gemini | gemini-3.8-flash | True | 0.75 | 3.75 |
| claude | claude-opus-5 | True | 5.0 | 25.0 |
| claude | claude-opus-5 | True | 5.0 | 25.0 |

## Planted findings (mutants)

| doc | field | expected | reported | strict | field-only | detail |
|---|---|---|---|---|---|---|
| G01 | barrier_level_pct | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 65 ≠ booking 70 |
| G02 | autocall_observation_dates | MISMATCH | MISMATCH | 🟢 | 🟢 | TS ['2027-05-12', '2027-11-12', '2028-05-12'] ≠ booking ['2027-05-12', '2027-11-15', '2028-05-12'] |
| G03 | day_count | MISMATCH | MISMATCH | 🟢 | 🟢 | TS ACT/360 ≠ booking 30/360 |
| G04 | coupon_memory | MISMATCH | MISMATCH | 🟢 | 🟢 | TS True ≠ booking False |
| G05 | notional | MISMATCH | MISMATCH | 🟢 | 🟢 | TS 10000000 ≠ booking 1000000 |
| G06 | currency | MISMATCH | MISMATCH | 🟢 | 🟢 | TS USD ≠ booking CAD |
| G07 | autocall_level_pct | MISMATCH | MISMATCH | 🟢 | 🟢 | TS [Decimal('100'), Decimal('95'), Decimal('90')] ≠ booking [Decimal('100'), Decimal('100'), Decimal('100')] |
| G08 | underlyings | MISMATCH | MISMATCH | 🟢 | 🟢 | TS ['SX5E'] ≠ booking ['SPX'] |
| G10 | barrier_level_pct | TS_ABSENT | TS_ABSENT | 🟢 | 🟢 | term sheet declares barrier_level_pct absent; booking has 70 |

## False flags on clean fields (0)

none

## Honest ceiling

- n = 12 synthetic documents, 9 planted findings plus 1 normalizer trap, 2 clean controls. **Directional, not statistically significant.**
- Documents are synthetic and generated from parameters across 4 layout families; real desk paper has more layouts, OCR noise and multi-page annexes.
- One prompt per extractor family; no prompt ensemble. One run per number: no retries, no reruns, no best-of.
- The eval can only see error classes it plants. Unplanted classes (e.g. wrong observation-date count, swapped issuer/guarantor) are invisible to it.
- Field-level false-flag denominator counts every non-planted comparison key on every document, including fields that are absent in both term sheet and booking.
- Cost is computed from traced tokens × pinned prices in config/models.yaml (current list prices).
