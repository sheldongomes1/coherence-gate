# GOAL.md — Coherence Gate

## What this is

A working mini-product called **Coherence Gate**: an eval-gated agent that checks
whether a structured-note **term sheet** (the desk's intent, a PDF/text document)
and the **booking record** (the bank's truth, a structured record) say the same
thing — and catches the divergence *before* it costs money.

One sentence: **"The term sheet is the desk's intent, the booking is the bank's
truth — this agent closes the gap between them before it costs money."**

## Who it is for

A single evaluator: a hardcore-technical Head of Equities Technology at a major
bank (ex-SocGen/JPMorgan, French quant-engineering culture). He will not be
impressed by a chatbot. He will be impressed by:

- evals built BEFORE the product, with a golden set and binary PASS/FAIL
- deterministic code wherever correctness matters; models only where judgment is needed
- silent failures made impossible by design (every absence announces itself)
- an honest eval report that states its own ceiling (small n, directional)
- architecture that would survive a bank's model-risk review

He is NOT evaluating UI polish. A clean CLI + generated HTML report beats a
half-finished web app.

## Deadline and effort budget

Hard deadline: **Sunday night**. Roughly 3 days of part-time work.
Everything in INSTRUCTIONS.md is scoped to that. When in doubt, cut scope,
never cut the eval report.

## Success criteria (in priority order)

1. `make demo` (or one documented command) runs end-to-end on the sample data
   with zero manual setup beyond API keys.
2. The eval report exists, is honest, and reports BOTH catch rate on planted
   errors AND false-flag rate on clean documents.
3. Every extracted field carries a citation (source text span) or an explicit
   `DECLARED_ABSENT` finding. There is no code path that yields a silent blank.
4. Clean documents flow through with zero human touch (the tiered-autonomy
   story); discrepant documents produce a triage note citing clause + booking field.
5. One observability trace can be shown for a full run (models, versions,
   tokens, latency per step).
6. A one-page BRIEF.md summarizes problem → architecture → results, punchline first.

## Explicitly OUT of scope (do not build)

- No pricing, no P&L, no greeks, no market data.
- No fine-tuning of any model.
- No multi-agent orchestration beyond the single pipeline (no A2A).
- No authentication, no deployment, no Docker unless it is trivial.
- No real term sheets — all documents are synthetic, written by us.
- No retry-until-it-passes logic in the eval harness. Evals report reality.

## The honest-ceiling rule

Wherever a number is reported (catch rate, agreement rate), the report must
state n, how it was measured, and the sentence "directional, not statistically
significant" where n is small. Never round up. A demo that admits its own
limits is the product.
