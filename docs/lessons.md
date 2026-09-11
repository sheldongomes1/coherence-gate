# lessons.md — surprises, reversals, and reworks during the build (write-up fuel)

## 2026-09-11 — The normalizer trap forced a schema change before any code existed
- Situation: designing how G09 ("2.0625% per quarter (8.25% p.a.)") could resolve as a match without arithmetic in a prompt.
- What broke / what we assumed: the INSTRUCTIONS schema had `coupon_rate_pct` only; an extractor would have to choose which number to return, which is prompt-side decision-making.
- Lesson: if a model has to do arithmetic to fill a field, the schema is missing a fact. Capture the fact (rate basis) and let code compute.
- Fix / rework: added `coupon_rate_basis` to schema v1 (ADR-1) before freezing it.
- Post angle: "The first bug I fixed in my extraction pipeline was in the schema, and I fixed it before writing a line of code."
