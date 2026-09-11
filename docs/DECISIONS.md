# DECISIONS.md — architecture decision records

Short form. Status: accepted unless noted. Fixed choices from INSTRUCTIONS.md are not
re-recorded here.

## ADR-1 Add `coupon_rate_basis` to schema v1
**Context.** G09 quotes "2.0625% per quarter (8.25% p.a.)"; the booking stores 8.25 p.a.
INSTRUCTIONS require normalization in code, never in the prompt.
**Decision.** Extractors capture the rate as written plus a `per_annum | per_period` basis;
`normalize.py` computes the per-annum value from basis and frequency. The basis is not
compared to the booking.
**Consequence.** One extra schema field (20 total, 19 compared). Without it the model would
have to choose a number, which is prompt-side arithmetic.

## ADR-2 Model pins: `gemini-3.8-flash` and `claude-opus-5`
**Context.** Live ids verified 2026-09-11. Gemini 3.8 Flash is the newest GA (non-preview)
model on the key; Opus 5 is the current Anthropic flagship. Prices in `config/models.yaml`.
**Decision.** Pin these; keep `gemini-3.1-pro-preview` and `claude-sonnet-5` as listed
alternatives. Triage on `claude-opus-5`.
**Consequence.** Asymmetric cost (Claude ~7× Gemini per token). The eval reports cost per
document; a Sonnet swap is a one-line change plus a rerun and a diff (Rule 6).
**Note.** Triage uses the same family as extractor B. It does not judge extraction quality
or arbitrate; it drafts text from decisions already made in code, so Rule 5 is not
violated.

## ADR-3 Citation offsets are recomputed in code
**Context.** Models are unreliable at character offsets but reliable at copying spans.
**Decision.** The model supplies only `text_span`; `schema_guard` locates it in the source
(exact, then whitespace-collapsed) and writes `char_range`. Not found → MALFORMED.
**Consequence.** Provenance is verifiable by construction; a hallucinated quote cannot pass.

## ADR-4 Merger compares normalized values, not raw strings
**Context.** Two families legitimately write "17 April 2026" and "2026-04-17".
**Decision.** Normalize each extraction first, then merge. Disagreement is on canonical
values only.
**Consequence.** Agreement rate measures semantic agreement; format noise is not a finding.
Raw values are kept for the report.

## ADR-5 `uv` + `pyproject.toml`
**Context.** INSTRUCTIONS allow venv+requirements or uv. uv is installed and used elsewhere.
**Decision.** uv with a committed `uv.lock`; `make setup` is the only setup command.

## ADR-6 MCP over stdio, spawned in-process
**Context.** The booking tool must be MCP-shaped without a running service.
**Decision.** `FastMCP` server module; the pipeline spawns it over stdio per run. Direct
fallback with identical signature and a `transport` tag in the trace. 2-hour timebox.

## ADR-7 `MALFORMED_EXTRACTION` finding type
**Context.** INSTRUCTIONS: "a malformed extraction is itself a finding, never a crash", but
the closed set has no type for it.
**Decision.** Add `MALFORMED_EXTRACTION`, per field, severity from the schema. Counted as a
false flag when it lands on a clean field, so guard strictness is measured.

## ADR-8 Stub pipeline reports API_ERROR, not fake data
**Context.** Phase 0 checkpoint is "0% catch rate with a stub".
**Decision.** Stub extractors return an `API_ERROR` outcome; everything becomes MALFORMED;
catch 0/10, false flags 217/217, auto-clear correctness 100% (nothing cleared). All red, all
true.

## ADR-9 Repository is private until the demo is ready
**Decision.** Create `sheldongomes1/coherence-gate` private; flip to public (or add the
interviewer as a collaborator) on Sunday with the showcase run committed.

---
*From here on, ADRs follow Nygard format and are produced at Socratic checkpoints
(multiple-choice, fast mode). Alternatives are recorded with the reason they lost.*

## ADR-10: Catch scoring is strict on (field, type); field-only catch is a diagnostic row

**Date:** 2026-09-11
**Status:** Accepted

**Context:** `catch_rate` is the headline number. G10 plants `TS_ABSENT` on
`barrier_level_pct`. A pipeline could report `MISMATCH` on the same field (e.g. an extractor
hallucinates a level) and still "catch" the field while getting the story wrong.

**Decision:** Headline `catch_rate` counts a hit only when doc, field, and finding type all
match the manifest. A second row, `catch_rate_field_only`, counts any non-CLEAN finding on
the planted field. Both rows carry n=9: INSTRUCTIONS list ten discrepant documents, but G09 is
a must-not-flag trap and is scored as its own row (`trap_resolved`, n=1).

**Alternatives considered:** Strict only: hides type confusion, which is exactly the
absence-vs-mismatch distinction the product sells. Lenient only: lets a hallucinated barrier
level count as catching an omission; the silent-failure test would pass for the wrong reason.

**Consequences:** Type confusion is visible as the gap between the two rows. Prompt
iterations that trade one for the other show up in `eval_log.md`.

## ADR-11: BVERSA10 appears as an underlying index ticker in three documents

**Date:** 2026-09-11
**Status:** Accepted

**Context:** The evaluator (RBC, Head of Equities Technology) should see an underlying he
recognises. BVERSA10 is an index ticker.

**Decision:** BVERSA10 is the sole underlying in one clean control (G12), one underlying in
a two-index worst-of basket with SPTSX60 in one planted document (G03, day-count mismatch),
and the underlying in the G09 normalizer-trap document. Ticker normalization treats it like
any other: upper, strip, suffix removed.

**Alternatives considered:** Only in a clean doc (too easy to miss in the demo); in the G08
underlying-swap doc (would make the planted finding about the ticker the evaluator is
watching, which reads as staged).

**Consequences:** The demo shows BVERSA10 auto-clearing (G12) and surviving the trap (G09).

## ADR-12: Synthetic documents use a fictional issuer; no real bank is named

**Date:** 2026-09-11
**Status:** Accepted

**Context:** The demo is for RBC. Realistic term sheets need an issuer, parties, and
boilerplate.

**Decision:** Issuer is "Northbridge Capital Markets (Canada) Inc." (fictional), programme
"Structured Notes Programme, Series 2026". Documents are CAD/USD flavoured with SPTSX60,
SPX, SX5E, BVERSA10 as underlyings. GOAL.md already forbids real term sheets; this extends it
to real names.

**Alternatives considered:** Naming RBC as issuer for realism: fabricated documents carrying
a real bank's name are a liability in a portfolio repo and add nothing to the technical
demo.

**Consequences:** The G06 currency plant (USD vs CAD) is natural for a Canadian issuer.

## ADR-14: Ambiguous numeric dates are rejected, never guessed

**Date:** 2026-09-11
**Status:** Accepted

**Context:** "03/04/2026" is 3 April day-first and 4 March month-first. Documents are
European/Canadian desk paper, so day-first is the likely convention, but the gate's value is
that it does not guess.

**Decision:** `norm_date` accepts ISO, long-form, and dd-Mon-yyyy dates, and slash dates only
when the day part exceeds 12. Otherwise it raises `NormalizeError`, which the pipeline turns
into a `MALFORMED_EXTRACTION` finding on that field; the desk sees the date it must confirm.

**Alternatives considered:** Assume day-first (silent wrong date on a US-format document,
then a confident comparator verdict). Currency-conditional parsing (a hidden rule; fails
model-risk review).

**Consequences:** A document that only writes dates numerically and ambiguously will always
go to triage on those fields. That is the intended behaviour; the false-flag rate will show
its cost if it happens in the golden set (it does not: all four layouts use unambiguous forms).
