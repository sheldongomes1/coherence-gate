# eval_log.md — iteration history (SKILL.md Rule 8)

One line per model-facing change. Change ONE variable per line (prompt OR schema OR
normalizer). Rates are counts, never averages. n = 12 documents / 9 planted findings + 1 trap /
2 clean controls unless stated. Directional, not statistically significant.

| date | change | catch_rate | false_flag_rate | agreement | auto_clear_ok | cost/doc | notes |
|---|---|---|---|---|---|---|---|
| 2026-09-11 | S0: stub pipeline (no model calls, API_ERROR outcome) | 0/9 | 218/218 | 0/228 | 9/9 | $0.0000 | eval exists before product. field-only catch reads 9/9 because MALFORMED lands on every field: that is why the strict row is the headline (ADR-10) |
| 2026-09-11 | S2 first real run, prompt extract_v1 (sha 54aedf9a8801), medium effort both; ABORTED after 4/12 docs (Gemini G05 call hung 2h, no client timeout) | 4/4 on G01-G04 | 1/76 (G02 barrier_type: Gemini wrote 'American (continuous observation)', enum normalizer rejected the parenthetical) | 75/76 | 4/4 | ~$0.15 (Gemini thinking 17-31k tokens/doc) | partial; not a headline number |
