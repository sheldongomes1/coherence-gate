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

## ADR-15: Extraction runs at medium effort on both families; high is a logged sweep

**Date:** 2026-09-11
**Status:** Accepted

**Context:** Claude Opus 5 exposes `output_config.effort`; Gemini 3.8 Flash exposes a
thinking level. Extraction is copy-and-cite, but G09 (per-period vs per-annum) and G10
(deferred barrier level) reward care. Cost per document is a reported metric.

**Decision:** Default `claude_effort: medium`, `gemini_thinking_level: medium`
(`config/models.yaml`). After the first full eval, one rerun at high on both, logged in
`eval_log.md` with both rates and cost, decides the shipped default.

**Alternatives considered:** High from the start (best demo odds, tens of seconds per Opus
call, no evidence the extra spend buys anything). Low (cheapest; likely over-flags, and the
false-flag row would be the first place it shows).

**Consequences:** The effort sweep is itself eval material: "here is what reasoning depth
bought on this task, in catch rate, false flags and dollars."

## ADR-16: One flat, union-free, string-typed output schema for both families

**Date:** 2026-09-11
**Status:** Accepted

**Context:** The first Claude call failed with HTTP 400: the structured-output compiler
limits a schema to 16 union-typed parameters; the Pydantic-derived schema had 60 (`anyOf`
for nullable values and citations). Gemini accepted the union schema and scored 19/19 on G11.

**Decision (amended same day after a second 400, "compiled grammar too large", on 20 nested
per-field objects):** Both extractors are constrained with the same hand-built schema of
three flat maps keyed by field, `status` / `value` / `citation`. Every value is a string "as
written" (array of strings for list fields), "" stands for null. Zero unions, zero nested
per-field objects. The per-field `note` is dropped from the extraction contract (triage is
where explanation lives). The guard enforces the pairing invariants; the normalizer turns
strings into canonical types. Output ceilings are per family because Gemini's cap includes
thinking tokens (32k Gemini, 16k Claude).

**Alternatives considered:** Keep unions for Gemini and strings for Claude (two contracts to
version, and the asymmetry would confound the agreement rate). Fewer fields (schema is
frozen). Turn off structured outputs on Claude and parse free JSON (loses the guarantee that
every field is present).

**Consequences:** Values "as written" are strings by nature, so the contract is more honest,
not less. A one-element list for a stepping field stays a list; a flat level is a scalar.

## ADR-17: Triage sees the finding, its citations and the booking field, not the document

**Date:** 2026-09-11
**Status:** Accepted

**Context:** The triage agent drafts one desk query per non-clean finding. It could be given
the whole term sheet (richest context) or only what the deterministic pipeline already
anchored.

**Decision:** Per finding, the prompt contains: field and its schema description, finding
type with its meaning, severity, both extracted values, the booking field and value, the
comparator's detail string, and the verbatim citation spans from both extractors. No full
document, no full booking record. One Opus call per finding, structured output, ~400 input
tokens.

**Alternatives considered:** Full document per call (~8× the tokens on Opus; the query can
drift into terms nobody flagged; and it re-opens a door for the model to "re-decide" the
match). One batched call per document (cheaper on multi-finding documents, harder to
validate per finding; the golden set has one finding per document anyway).

**Consequences:** The desk query can only cite what the extractors cited, which is exactly
the provenance the desk should see. A discrepancy explained by an unrelated clause elsewhere
will not be noticed by triage; that is a Phase 2 item (give triage the guard-located
neighbourhood of the field).

## ADR-18: A wholesale extractor failure gets one code-written note, not N triage calls

**Date:** 2026-09-11
**Status:** Accepted

**Context:** In the first `make demo`, Gemini timed out on G11 while a full eval was running
concurrently. All 19 fields became `MALFORMED_EXTRACTION`, the document went to TRIAGE (correct),
and the triage agent drafted 19 near-identical desk queries for one technical event ($0.32).

**Decision:** If every field of one extractor is `Malformed` for the same reason (API error,
timeout, refusal, non-JSON), the pipeline attaches a deterministic `TriageNote`
("No desk action: extraction failed wholesale … rerun the gate") to each affected finding,
writes a `SKIPPED_WHOLESALE_FAILURE` trace line, and makes no triage calls. Per-field
malformations (one bad citation) still go to the model.

**Alternatives considered:** One batched triage call for the group (still a model explaining
a timeout). Retrying the extractor (retry-until-pass is banned in the eval path; SDK-level
bounded retries already ran).

**Consequences:** Technical failures are visible, cheap and honest: the document does not
auto-clear, the desk is not spammed, and the trace says why.

## ADR-19: Gemini ships at medium thinking; the low-thinking numbers are the documented trade-off

**Date:** 2026-09-11
**Status:** Accepted (closes the sweep promised in ADR-15)

**Context:** Two full runs differing only in Gemini's thinking level (`eval_log.md`
iterations 3 and 4). Medium: 9/9 strict catch, Gemini median 27 s, worst 720 s, $0.114 per
document. Low: 8/9 (Gemini wrote an observation date into `autocall_level_pct` on the
step-down schedule, G07), median 3 s, worst 6 s, $0.072 per document. False flags were 3/218
in both, all verbose enum forms, fixed in the normalizer afterwards. Claude Opus 5 at medium
was 228/228 on extraction accuracy in every run.

**Decision:** `gemini_thinking_level: medium` stays the pinned default. The low-thinking run
stays in `eval_log.md` and is named in the brief as the measured cost/latency alternative.
`CG_GEMINI_THINKING=low` switches it without editing the pinned file.

**Alternatives considered:** Ship low and report 8/9 (cheaper and 9× faster, but the miss was
a genuine mis-mapping on the one field type that steps, and the headline number is the
product). A second low run to test whether the miss is stable (worth doing in Phase 2 with a
larger golden set; one more run on n=12 would not settle it).

**Consequences:** Gemini is the slow, variable-cost extractor in this pipeline (its thinking
volume swings 1k–32k tokens per identical call). The 240 s timeout and 2-attempt retry bound
make that variance visible rather than fatal. Phase 2 routes Gemini through Vertex AI and
re-runs the sweep on n≈50.

## ADR-20: v0.2 scope and order (from docs/V2-CHANGES.md)

**Date:** 2026-09-12
**Status:** Accepted

**Context:** Sheldon delivered a v0.2 plan (seven change sets), two approved document
templates (note G12, OTC option OP-2026-0114), a model-risk summary to fill, and the Versa
methodology. v0.1.0 is tagged as the floor. About 36 wall-clock hours remain, part-time.

**Decision:** Build order: CS1 PDF golden set → CS2 Mixedbread parsing + citation chain +
parse-tax ablation → CS6 eval report/brief v2 → **CS3 in full** (option product, participation
mutant AND premium arithmetic relation; chosen over CS3-minimal because the demo script opens
on the option) → CS5 desk view → CS7a live check + CS7c STALE → CS4 Versa reference lane →
CS7b model-swap diff (from the logged medium/low sweep if no second model) → MODEL-RISK
filled from the final run. Each change set ends at a committed checkpoint; the cut line falls
wherever the clock stops, and anything cut is named in DESIGN.md and the brief.

**Alternatives considered:** The written priority (CS3 last) contradicts the demo script's
first and third beats; CS3-minimal was offered and declined in favour of the full set.

**Consequences:** CS4 (reference lane) is now the most likely casualty. Rendering: no
WeasyPrint or system Chrome on this machine; a Playwright Chromium is present. Parser:
Mixedbread behind `parse(pdf) -> markdown + meta`, pdftotext as `local-fallback`.
**Approved templates override the parameter table** where they differ (G12's economics
change to the approved document's).

## ADR-21: Pluggable product schemas, code-side product detection, relations as schema data

**Date:** 2026-09-12
**Status:** Accepted (v0.2 CS3)

**Context:** The OTC option (approved OP-2026-0114) needs its own fields, and CS3 asks for a
cross-field premium arithmetic check. The gate must stay product-agnostic.

**Decision:** `schema/products.json` registers product types → schema files
(`termsheet_v1.json`, `option_v1.json`). Product detection is deterministic title-keyword
matching in code (`detect_product`), recorded in the trace; the manifest may also state it.
Cross-field rules live in the schema as data (`relations: product_equals`) and are evaluated
by `comparator.check_relations` on the term sheet AND the booking; each relation always yields
one finding: CLEAN (holds, or "not evaluable: <missing>" stated), or `RELATION_VIOLATION`
naming the failing side and the arithmetic. Relation checks count as clean fields in the
false-flag denominator (`rel:<name>` keys).

**Alternatives considered:** A model classifying the product (a decision in a prompt);
folding option fields into one union schema (breaks the strict output contract);
evaluating relations only on the booking (misses a self-inconsistent term sheet).

**Consequences:** The Underlying Index sub-schema is deferred to CS4 (reference lane) to keep
CS3 focused. Golden set grows to 15 documents, 12 planted findings, 1 trap, 3 clean controls.
