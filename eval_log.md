# eval_log.md — iteration history (SKILL.md Rule 8)

One line per model-facing change. Change ONE variable per line (prompt OR schema OR
normalizer). Rates are counts, never averages. n = 12 documents / 9 planted findings + 1 trap /
2 clean controls unless stated. Directional, not statistically significant.

| date | change | catch_rate | false_flag_rate | agreement | auto_clear_ok | cost/doc | notes |
|---|---|---|---|---|---|---|---|
| 2026-09-11 | S0: stub pipeline (no model calls, API_ERROR outcome) | 0/9 | 218/218 | 0/228 | 9/9 | $0.0000 | eval exists before product. field-only catch reads 9/9 because MALFORMED lands on every field: that is why the strict row is the headline (ADR-10) |
| 2026-09-11 | S2 first real run, prompt extract_v1 (sha b1cca6dbcc44), medium effort both; ABORTED after 4/12 docs (Gemini G05 call hung 2h, no client timeout) | 4/4 on G01-G04 | 1/76 (G02 barrier_type: Gemini wrote 'American (continuous observation)', enum normalizer rejected the parenthetical) | 75/76 | 4/4 | ~$0.15 (Gemini thinking 17-31k tokens/doc) | partial; not a headline number |
| 2026-09-11 | S2 FULL BASELINE run 20260911-193808: prompt extract_v1 (sha b1cca6dbcc44 after the three-map reshape, ADR-16), medium effort both, timeouts on, enum-parenthetical fix in normalizer | **8/9** (field-only 9/9) | **0/218**; clean docs auto-cleared 2/2 | 227/228 | 9/9 | $0.112 (min 0.071, max 0.160; Gemini thinking 1.2k-24k tokens/doc) | miss = G07 autocall_level_pct: BOTH families wrote the step-down as a JSON array inside the string value ('["100 per cent.", ...]'); normalizer rejected -> MALFORMED (caught field-only, wrong type). trap G09 CLEAN 1/1 |
| 2026-09-11 | iteration 2, run 20260911-194608: normalizer unwraps JSON-array strings (G07 fix); same prompt/effort | 8/9 (G07 now MISMATCH ✓; G02 lost to a Gemini ReadTimeout that surfaced after 7,985 s, i.e. SDK retries far beyond the 240 s per-call budget) | 18/218 (all 18 = the same G02 Gemini timeout, MALFORMED on every field) | 209/228 | 9/9 | $0.099 | Claude 228/228 vs truth; Gemini 209/228 with the 19 timeout fields, otherwise 100%. Quality fixes done; remaining failure class is Gemini transport/retry behaviour |
