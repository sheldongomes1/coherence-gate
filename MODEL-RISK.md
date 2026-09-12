# MODEL-RISK.md — Concord: model-risk summary (pre-filled for review)

Prepared in the format a model risk / non-financial risk committee would
expect for a system containing nondeterministic components. Bracketed values
are filled from the current eval report at release time. This document ships
with the demo: the approval question answered before it is asked.

## 1. System purpose and materiality

Concord checks coherence between trade documents (term sheets / OTC option
confirmations), booking records, and, where applicable, the governing index
methodology, before and after booking. It produces findings and drafted desk
queries; it does not book, amend, price, or move money. Failure materiality:
a missed finding leaves an existing manual-control gap unchanged (no new
risk); a false finding costs desk review time. The system is decision-support
with a human disposition on every non-clean outcome.

## 2. Component inventory — model vs. code

| # | Component | Type | What it DECIDES | What it produces |
|---|---|---|---|---|
| 1 | Document parsing (Mixedbread, swappable) | Vendor ML | nothing | canonical parsed text, versioned artifact + job id |
| 2 | Extractor A (Gemini family, pinned) | LLM | nothing | field values + citations into parsed text, or DECLARED_ABSENT |
| 3 | Extractor B (Claude family, pinned) | LLM | nothing | same, independently |
| 4 | Agreement merger | Code | disagreement → automatic finding | merged extraction |
| 5 | Normalizer (dates, rates, tickers) | Code | rejects ambiguity (e.g. ambiguous slash dates → finding, never a guess) | normalized values |
| 6 | Comparator + arithmetic relations | Code | match / no-match, tolerances, cross-field arithmetic | typed findings, severity |
| 7 | Reference check (methodology lane) | Code (over model-extracted reference schema) | claim-vs-rule inconsistency; knows which parameters the methodology defers | REFERENCE_INCONSISTENT findings |
| 8 | Triage agent | LLM | nothing | classification + drafted desk query, citing ONLY spans already anchored by 2/3 |
| 9 | Lane assignment (auto-clear vs review) | Code | autonomy per field: agree + match + clean → auto-clear; anything else → human | queue |

Design rule, enforced in code review: no model makes the match decision,
applies a tolerance, computes a number, or cites text that was not anchored
by the extraction step. Models read and explain; code decides.

## 3. Controls on the nondeterministic components

- Dual-family independence: two model families extract independently; any
  disagreement is automatically a finding (no LLM arbitration). An evaluator
  can only miss what it would itself get wrong; two families narrow that set.
- Grounding: every extracted field carries a citation (character span) into
  the versioned parsed text, or an explicit DECLARED_ABSENT. No silent
  blanks; ambiguity is refused, not resolved by guess.
- Containment of the triage agent: input is the finding + anchored citations
  + booking field only — it cannot introduce claims from elsewhere in the
  document. Known limitation (stated): it also cannot exculpate a finding
  using an unflagged clause; production design escalates to a
  document-scoped call only on desk rejection.
- Autonomy is earned per field, not granted globally: auto-clear requires
  family agreement AND deterministic match; everything else is human-
  dispositioned.

## 4. Evaluation evidence (release v0.2.0, run 20260912-191532, date 2026-09-12)

- Golden set: 15 documents (15 parsed PDF / 0 text; every document exists in both forms), 17 planted
  discrepancies across 4 finding types (MISMATCH, REFERENCE_INCONSISTENT, RELATION_VIOLATION, TS_ABSENT), 3 clean controls, mutation-
  testing style.
- Strict catch rate (field AND type): 17/17. Field-level (diagnostic): 17/17.
- False-flag rate on clean fields: 0/417 (equal prominence by policy).
- Auto-clear correctness: 17/17 (100%) — nothing planted was auto-cleared.
- Cross-family extraction agreement: 396/396.
- Parse tax (text vs parsed-PDF ablation): gemini 368/396→396/396 (+28), claude 396/396→396/396 (+0); 0 field(s) degraded, listed in eval_report.md.
- Honest ceiling: n is small — directional, not statistically significant;
  synthetic documents, 4 layout families, single parsing vendor; the eval
  cannot see error classes it does not plant. Full iteration history in
  eval_log.md (one variable per iteration).

## 5. Ongoing monitoring (production design)

- Auto-clear correctness as a standing metric on sampled human re-review of
  auto-cleared fields; any planted-audit failure gates the auto-clear lane
  down to review-all.
- False-flag rate tracked weekly; desk-rejection of drafted queries feeds an
  error register (desk trust dies from false positives faster than misses).
- Attestation freshness: attestations are hashed to (parsed document,
  booking record); any amendment invalidates to STALE and queues re-check —
  trust is continuous, not one-shot.
- Drift alarm: cross-family agreement rate trended; a sustained drop signals
  model or document-population drift before accuracy visibly degrades.
- Desk dispositions feed a proposal queue for golden-set and judgment
  changes; proposals are human-approved and admitted through the same eval
  gate (see eval_diff.md); no feedback path alters model or pipeline
  behavior directly.

## 6. Model change management

All judgment artifacts — schema, prompts, tolerance tables, golden set,
consequence templates — are versioned in the repository. Model identities are
pinned configuration recorded in every trace. On any model change
(deprecation, version bump, effort change):
1. change the single pinned reference in config;
2. rerun the full eval against the unchanged golden set;
3. `make eval-diff` renders the before/after (catch, false-flag, agreement,
   auto-clear, cost, per-field deltas) — see eval_diff.md for a real example;
4. accept, hold, or remediate on the diff.
A deprecation is therefore a rerun and a comparison, not a rebuild: the
judgment is versioned, not the model.

## 7. Exclusions and honest limits

- No model participates in booking, amendment, payment, pricing, or any
  greek computation; risk figures displayed on the desk view are indicative
  fixtures and the trust column asserts direction of concern only, never
  magnitude.
- Vendor parsing is single-sourced in the demo; the interface is one module
  and swappable (local fallback implemented).
- Sample sizes are demo-scale throughout; production onboarding requires a
  larger, layout-diverse, partly hand-written golden set (Phase 2, DESIGN.md).

