# Coherence Gate — term sheet vs. booking, checked before it costs money

**The term sheet is the desk's intent. The booking record is the bank's truth.
This agent closes the gap between them before a confirmation goes out wrong.**

## Problem

Document-to-booking coherence is checked by hand today, and the hours scale
linearly with strategy and trade count. The dangerous failure is silent: a
barrier level, a day count, a memory-coupon clause that differs between the
document and the system — invisible until reconciliation, a confirmation, or a
coupon payment surfaces it. I have paid for this failure class personally: a
seven-figure loss on an order that silently never reached the execution tool.
This is the system I wish had existed upstream of it.

## What it does

Two model families (Gemini, Claude) independently extract the term sheet into
a versioned schema — every field either cited to its source span or explicitly
declared absent. A deterministic comparator checks the merged extraction
against the booking record (retrieved through an MCP tool, the way it would
integrate with real books-and-records). Where both families agree and the
comparison passes, the trade auto-clears with zero human touch. Anything
else — a mismatch, a family disagreement, a declared absence — becomes a
finding, triaged by an LLM into a drafted desk query citing the exact clause
and booking field.

**Models extract and explain; code decides.** No LLM ever makes the
match/no-match call, applies a tolerance, or normalizes a value. Autonomy is
earned per field, not granted globally — the review queue exists by design,
not as an apology.

## Results (12 synthetic documents, 10 planted discrepancies, 2 clean controls)

| Metric | Result |
|---|---|
| Planted-discrepancy catch rate | [X/10] |
| False flags on clean fields | [X/N] |
| Auto-clear correctness (nothing planted was auto-cleared) | [must be 100%] |
| Cross-family extraction agreement | [X%] |
| Cost per document | [$X.XX] |

Planted set includes the hard cases: a rate quoted per-quarter in the document
and per-annum in the booking (must resolve as a match through deterministic
normalization, not get flagged), and a document that genuinely omits its
barrier level (must produce a finding, not a blank).

**Honest ceiling:** n=12 documents — directional, not statistically
significant. Synthetic documents, one layout family per document, one prompt
per extractor. The eval cannot see error classes it does not plant. Full
iteration history in `eval_log.md`: every prompt change and what it did to
both rates.

## Why this architecture survives a bank

Independent implementations that must agree before a result is trusted — the
same principle as external replication of an index level, applied to
extraction. Every model call traced (model, version, tokens, latency); every
run reproducible; prompts, schema, tolerances and golden set versioned, so a
model deprecation is a rerun and a diff, not a quarter of rework. Built on
ADK patterns; both model families are first-class in Vertex Model Garden, so
the whole pipeline runs under one existing Google Cloud governance surface.

## Where this goes

The gate pattern — golden set first, dual-family extraction, deterministic
decision, eval-gated autonomy — extends directly to reconciliation break
triage and P&L attribution commentary: the same judgment-heavy hours that
grow with every strategy onboarded. The measure of success is the one you
named: the marginal cost of the next strategy falls, and you don't hear
about it.

— Sheldon Gomes
