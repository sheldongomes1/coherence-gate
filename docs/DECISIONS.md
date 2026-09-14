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

## ADR-13: The golden set is generated from one parameter table

**Date:** 2026-09-11
**Status:** Accepted (checkpoint decision)

**Context:** Twelve realistic term sheets with varied layouts, each with a truth file, a
booking and a manifest label, hand-written, would drift: a truth file saying 65 while the text
says 65.0%. A schema change would mean 36 hand edits.

**Decision:** `scripts/gen_golden.py` holds the parameter rows and the layout renderers; text
(later HTML/PDF/TXT), truth, booking and manifest all come from the same row, and planted
discrepancies are applied to the booking only. Regenerable in one command.

**Alternatives considered:** Hand-written documents (most realistic, slowest, label drift).
Generated then hand-edit three (some variance, some drift protection); deferred to Phase 2.

**Consequences:** Four layout families and machine-uniform phrasing, stated in every honest-
ceiling section. Approved hand-made templates later became the house style (ADR-20).

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

## ADR-22: Desk-view trust states are derived from finding types by a fixed table; consequences state direction only

**Date:** 2026-09-12
**Status:** Accepted (v0.2 CS5)

**Context:** The desk view is the front door: one row per position, one trust state, one line
of consequence. Anything a model wrote here would be a second, unverified verdict.

**Decision:** Trust state is computed from the run's typed findings: any `MISMATCH`,
`TS_ABSENT`, `BOOKING_ABSENT` or `RELATION_VIOLATION` → MISMATCH (red); otherwise any
`EXTRACTOR_DISAGREEMENT` or `MALFORMED_EXTRACTION` → DISAGREEMENT (amber); otherwise
ATTESTED (green); STALE (grey) when the attested document or booking hash has moved (CS7c).
The consequence line comes from a `(finding type, field) → template` table with `{ts}` and
`{bk}` values, direction words computed by code (booked lower than documented → "under-hedged"),
never a magnitude. Risk figures are labelled indicative fixtures. Rows sort red → stale →
amber → green and link to the run report anchor.

**Alternatives considered:** Letting the triage agent write the desk line (a model verdict
on the front page); showing greeks computed by the system (out of scope, GOAL.md).

**Consequences:** A new finding type or field needs a template row or falls back to the
generic "{field} booked {bk} vs {ts} documented" line, which is honest but flat.

## ADR-23: Reference lane semantics — rule, default, deferred

**Date:** 2026-09-12
**Status:** Accepted (v0.2 CS4)

**Context:** The Bloomberg Versa methodology fixes some things unconditionally (Type I is
Excess Return; rebalance every Index Business Day; Index Value floored at zero; the
administrator), states others as defaults "unless the index-specific document states
otherwise" (deduction factor, transaction cost, determination lag), and merely defines
others without a value (Volatility Target). A naive check would flag a term sheet's 10%
volatility target against a rulebook that never states one.

**Decision:** The methodology schema carries `binding: rule | default | deferred` per field
and a `claim` mapping to the term-sheet field it governs. Only `rule` bindings can produce
`REFERENCE_INCONSISTENT`; `default` and `deferred` produce CLEAN findings whose detail says
why they were not checked. The return-treatment rule is checked as a pair: the term sheet's
(Type, treatment) against the methodology's type→treatment map. Reference findings use the
`ref:<claim>` key so they coexist with the booking comparison on the same field, and they
count in the false-flag denominator only for documents that make index claims. The
methodology is extracted by both families and merged by code; a rule the families disagree
on is "not evaluable", never a flag. Extractions are cached by (markdown sha, prompt sha,
model) because the rulebook does not change between runs; the trace says CACHED.

**Alternatives considered:** Checking every term-sheet index parameter against the
methodology (flags on deferred parameters, exactly the false-positive class that kills desk
trust). An LLM judging whether a claim "is consistent with" the methodology (a decision in a
prompt).

**Consequences:** Three planted reference cases: G09 (Type I called Total Return), G14
(monthly rebalancing), G03 (vol target: booking-static mismatch only, deferred in the
rulebook by design). Volatility Target is the demo's "the gate knows what it cannot check".

## ADR-24: Output shape amended to two maps plus an `absent` list (grammar limit at 27 fields)

**Date:** 2026-09-12
**Status:** Accepted (amends ADR-16)

**Context:** With the index sub-fields, the note schema has 27 fields and the option schema 28.
The three-map shape (status/value/citation) hit Claude's "compiled grammar is too large" at
that size; every Claude extraction in the first 15-document runs failed with HTTP 400, which
the pipeline reported as MALFORMED on every field (1/17 catch). Probes on a ten-token
document: three maps 400; two maps compile; two maps + `absent` array with an enum of field
names compiles for both products.

**Decision:** Both families and the reference extractor use `{value: {…}, citation: {…},
absent: [field names]}`. Absence stays an explicit declaration (a field must be *named* absent,
and then its value and citation must be empty); the guard enforces the pairing both ways and
still accepts the older three-map shape for stored outputs.

**Alternatives considered:** Dropping status entirely with "" meaning absent (loses the
explicit declaration). Splitting extraction into two calls per family (doubles cost and breaks
the one-contract symmetry). Free JSON without a grammar (loses the every-field guarantee).

**Consequences:** The smoke test on both products now precedes any full run (lesson learned
at the cost of two wasted evals). Prompt v2 and reference_v1 describe the new shape.

## ADR-25: OTel attributes are added to trace lines, not swapped in for the flat keys

**Date:** 2026-09-12
**Status:** Accepted (v0.2 CS8a)

**Context:** CS8a asks for trace records in the shape of the OpenTelemetry GenAI semantic
conventions. Three committed runs and every report reader consume the flat keys.

**Decision:** Every trace line gains an `otel` object (`name`, `kind`, `duration_ms`,
`attributes` with `gen_ai.request.model`, `gen_ai.response.model`,
`gen_ai.usage.input_tokens/output_tokens`, `gen_ai.provider.name`, `gen_ai.operation.name`,
tool spans for parse / booking lookup, `code.function` for deterministic steps, plus
`coherence_gate.*` attributes for run id, doc id, outcome and cost). The flat keys stay. No
exporter is wired; on Agent Engine the attributes map onto Cloud Trace without re-instrumentation.

**Alternatives considered:** Renaming the flat keys (breaks the frozen showcase runs and every
reader for a cosmetic gain). Wiring a real OTLP exporter (auth on the critical path, ruled
out by the plan).

**Consequences:** Trace lines are ~40% larger. `trace_view` is unchanged.

## ADR-26: The desk view leads with delta-equivalent exposure under check, not with cost

**Date:** 2026-09-13
**Status:** Accepted (amends CS5 / ADR-22)

**Context:** The header line "$2.44 to check the book" read as trivial against a desk that
manages billions; a trader's page should say what is at stake, not what the check cost.

**Decision:** The header states gross delta-equivalent exposure (indicative fixtures: delta %
× notional × indicative FX to USD) for the whole book, for attested positions, and for the
positions that require attention ("the red figure is delta exposure resting on positions whose
booking does not match the document"). A per-row USD-equivalent delta column is added. Cost
moves to the behind-the-scenes panel as total and per document, with the flat-marginal-cost
sentence. All risk figures stay labelled as fixtures not computed by the gate (GOAL.md: no
greeks).

**Alternatives considered:** Cost in context ("$2.44 to check USD 154mm of notional"): still
leads with the wrong number. Dropping cost entirely: loses the marginal-cost beat.

**Consequences:** `scripts/gen_golden.py --fixtures-only` regenerates fixtures without
touching PDFs (which would invalidate the parse cache). Sign convention fixed on 2026-09-13
after review: every row shows the delta of the booked position from the desk's side (sold call
and issued note are both short the index, negative), never the hedge; the earlier fixtures mixed
the two views.

## ADR-27: "At stake" is the position's delta on a mismatched booking, never the delta of the discrepancy

**Date:** 2026-09-13
**Status:** Accepted

**Context:** The desk asked for the dollar value of each mismatch, sorted largest first.

**Decision:** The desk view shows, for every non-attested row, the position's delta-equivalent
USD as "at stake" (with the count of critical findings), and sorts red rows by it descending.
The page states that this is the whole position's delta, not the delta attributable to the
discrepancy, because attributing it would require repricing booked versus documented terms.

**Alternatives considered:** Computing the delta difference between booked and documented
terms (a pricer; GOAL.md excludes greeks and V2-CHANGES forbids claiming magnitudes of greek
error). Weighting by severity only (loses the exposure ordering the desk asked for).

**Consequences:** True attribution is named as roadmap ("hedge-to-liability coherence"): plug
the desk's risk system, reprice both term sets, show the delta of the difference. Same-day
amendment: the separate "at stake" column was redundant with Δ USD-equiv. and was removed; the
Δ USD cell is rendered red on non-attested rows and the sort order (largest exposure first
within each trust state) is kept.

## ADR-28: Attestations bind to the booking's terms projection, not to the record

**Date:** 2026-09-13
**Status:** Accepted (amends CS7c)

**Context:** A live booking record changes hundreds of times a day (fixings, MTM, accruals,
lifecycle flags, version counters). Hashing the whole record would flip every attested row to
STALE within hours and make the state meaningless.

**Decision:** The attestation is a hash, and the hash is computed over the booking fields
that affect the terms of the deal (the schema's comparison keys), sorted and canonicalised;
the field list is stored with the attestation so the page recomputes the same hash later. A
fixing, mark, accrual or lifecycle flag does not touch a term and cannot invalidate the row;
an amendment to a term (barrier, coupon memory, participation…) does. An event that genuinely
changes a term (an autocall trigger shortening maturity) is a term change and should
invalidate, which is correct. Where a booking platform versions trade terms separately from
events, its terms-version id is an acceptable substitute for the hash; the hash is the
platform-independent form and the one shipped.

**Alternatives considered:** Whole-record hash (fails under intraday updates). Ignoring
booking changes entirely (defeats STALE). Time-based expiry (a timer is not evidence).

**Consequences:** `attested_hashes.booking_terms_keys` in `summary.json`; older runs fall
back to the whole-record hash. Test: fixings, MTM and version bumps leave the row attested;
a coupon-memory change makes it STALE.

## ADR-29: A relaunch after a booking change reuses the attested extraction

**Date:** 2026-09-13
**Status:** Accepted

**Context:** The first live relaunch re-read the term sheet with both families (about two
minutes) although only the booking had changed. The extraction is attested to the document's
hash; the comparison is attested to the booking's deal-terms hash. They change independently.

**Decision:** `recheck_document` reuses the stored extractions of both families when the
document hash is unchanged and re-runs normalize → merge → compare → relations → reference →
lanes; triage runs only for findings that are new since the prior result (unchanged findings
keep their desk query). The trace records `load: REUSED_EXTRACTION` and `extract: CACHED`.
A full re-read is a separate, explicit action ("re-read term sheet"). The demo service builds
its run context (extractors, parser, cached methodology rules) once per process and warms it
at startup; Cloud Run runs with CPU always allocated so background jobs are not throttled.

**Alternatives considered:** Always re-extract (honest but wasteful: two model calls to learn
nothing new about an unchanged document). Skipping triage on recheck (the desk query for a new
finding is the point of the relaunch).

**Consequences:** A booking edit is checked in seconds; model calls happen when a document is
first read, when it is deliberately re-read, and once per new finding for the desk query.

## ADR-30: A check the gate cannot perform is NOT_EVALUABLE, never CLEAN

**Date:** 2026-09-13
**Status:** Accepted (from the independent review)

**Context:** Reference checks on deferred or default parameters, relations with missing
inputs, and rules the two families disagreed on were emitted as `CLEAN` with an explanatory
detail. That placed 24 unperformed checks among the 418 "auto-cleared" findings of the release
run and inside the false-flag denominator, while MODEL-RISK claimed auto-clear requires
agreement and a deterministic match.

**Decision:** New finding type `NOT_EVALUABLE` and lane `INFO`: recorded with its reason,
excluded from the auto-clear count, the false-flag denominator and the attested-field count,
never a flag. A document auto-clears when every *performed* check is CLEAN. Families
disagreeing on a methodology rule is `NOT_EVALUABLE` (the rule is unusable), never CLEAN. The
eval report lists not-performed checks by reason; the desk view and modal show them as their
own group.

**Alternatives considered:** Keep CLEAN with a detail (what the review caught: an unperformed
check counted as attested). Treat as TRIAGE (a human queue full of checks nobody can act on).

**Consequences:** Headline denominators shrink slightly and the attested-fields figure is
now what it says. If the methodology cannot be loaded, every index claim becomes
`NOT_EVALUABLE` with the reason and the trace says `reference_check: UNAVAILABLE`, instead of
the lane silently disappearing.

## ADR-31: An eval can resume; it reuses only extractions whose calls completed, and says so

**Date:** 2026-09-13
**Status:** Accepted (checkpoint taken without the user: three release runs in a row were lost to the environment, not the code, with the deadline hours away; logged as a skip with reason)

**Context:** The v0.2.1 release run failed three times in one morning for reasons outside the pipeline: an exhausted Anthropic credit balance (HTTP 400 on the last two documents), then twice a host that went to sleep mid-call (both families TIMEOUT at the same instant, 6,784 s and 1,541 s against a 540 s deadline). Each restart repeated 40 minutes and about $2 of calls that had already produced attested extractions. SKILL.md's "one pass, no retries, scored as it fell" is about not re-rolling the dice on a model answer; it says nothing about re-paying for answers that already exist.

**Decision:** `cg eval --resume <prior run>`. A document is reused only when the prior trace shows that the LAST extraction call of EACH family completed (OK, MALFORMED or CACHED) and its summary exists; it is then re-checked through the ADR-29 path (stored extractions attested to the document hash, deterministic steps re-run, triage only for new findings), with the prior extraction cost carried into this run's per-document cost. Any document with a TIMEOUT, API_ERROR, REFUSAL or suspended-process outcome is extracted again in full. The report header names the prior run, the reused documents and the re-extracted ones; the trace records RESUME, REUSED_EXTRACTION and RESUME_FALLBACK events.

**Alternatives considered:** (a) Keep restarting from zero: honest but three restarts cost a morning and proved nothing new. (b) Retry the failed call inside the run: rejected, it re-rolls the model on the same document within one scored pass (ADR-10 / SKILL.md). (c) Splice the missing documents into the old run's report by hand: rejected, an unreproducible number. (d) Run the eval off the laptop (Cloud Run job): right for later, but new plumbing on the release path at 11:30 on deadline day.

**Consequences:** A stall costs one document, not the run. A resumed run is a composite and is labelled as one; the eval_log line for a release must say "resumed from X" when it applies. A MALFORMED reading is deliberately reusable: it is the model's answer and must count against it. The web service's relaunch is unchanged (it never carries prior cost, because its summaries are the same file being overwritten).

## ADR-32: A report-format change is a rescore from stored artifacts, never a rerun

**Date:** 2026-09-13
**Status:** Accepted (taken during the second review pass; no user checkpoint, logged as a skip: the alternative was paying $2.50 and 40 minutes to change the wording of three table rows)

**Context:** The second independent review asked for label and attribution changes in `eval_report.md` (§5 reason wording, a desk-queries row in §7, roles in §8, the resume caveat in §11, the prior run's failed call named under §2). The release report is frozen from a run; the scoring code that wrote it had moved on. Re-running the eval to regenerate prose would spend money and, worse, could change the numbers by chance while the intent was to change only their presentation.

**Decision:** `cg rescore --run <dir>`: reload each document's stored extractions, re-normalize them (deterministic), take findings, merges, lanes and costs as persisted, read the trace back, and run the current `scoring.score` + `render_markdown`. The report header states that it was rescored, on what date, with which code, and what the previous headline was; `summary.json` is rewritten. Appendices written by other commands (`cg ablation`, `cg triage`) are re-appended by those commands. First use: the v0.2.1 release run, rescored with identical numbers (17/17, 0/399, 396/396, $0.1672/doc) and §7 now showing the $0.2344 of desk queries the previous format hid.

**Alternatives considered:** (a) Re-run the eval: money and a chance of a different result for a presentational change. (b) Edit the frozen report by hand: forbidden by the project's own rule that numbers are generated, never typed. (c) Resume the run into a new run id (ADR-31): works, but creates a new run whose trace no longer holds the desk-query lines, losing the very cost the change was meant to show.

**Consequences:** Presentation and measurement are separated: the measurement is the artifacts, the report is a pure function of them. A rescore can only reflow what was stored; anything not persisted (an intermediate value) cannot be reported after the fact, which is an argument for persisting more, not for re-running. The rescore test asserts identical numbers on a stub run.

## ADR-33: Provenance is drawn from stored artifacts, not from a new instrumentation layer

**Date:** 2026-09-14
**Status:** Accepted

**Context:** The desk view answers "what is wrong with this trade" and the run report answers "on what evidence", but neither answers the question a model-risk reviewer actually asks first: *where did this number come from, step by step, and what did each step cost?* The trace already holds that (every model call with model, version, tokens, latency, cost and outcome) and each stage already persists its own artifact, but a reviewer had to read a JSONL file to see it.

**Decision:** A per-deal provenance graph rendered as plain SVG from the run's own artifacts: inputs (document hash, booking record, methodology) on the left, then parse, the two independent readings, normalize and merge, the deterministic decision, the lanes, the drafted desk queries, and the findings with their attestation hashes. Every box that produced an artifact links to that artifact, so the picture is a way into the payload rather than a decoration. Colour carries the one distinction the numbers hide: green completed, blue reused under an unchanged document hash, red never completed, dark grey for the code steps where no model is consulted. The graph is inlined in the evidence modal and in the run report, and written to `<run>/<doc>/provenance.svg` as an artifact in its own right.

**Alternatives considered:** (a) Graphviz or a JS graph library: a dependency and a build step for a fixed six-stage DAG whose layout is known in advance; Graphviz is not even installed on the build box. (b) Mermaid in the page: needs a CDN script, which the static bundle and the offline copies would not have. (c) Emit a new trace format for visualisation: a second source of truth about the same run, which is exactly the thing that later disagrees with the first. (d) Cloud Trace only: right for production (the spans are already OTel-shaped) but invisible in an offline artifact and unavailable to anyone without project access.

**Consequences:** Observability now costs nothing at run time: no step is re-run, no extra call is made, and a test asserts that drawing a graph leaves every other file in the run byte-identical. The graph can therefore be produced for any past run, including the ones parked as invalid, which is how a failed run is explained rather than argued about. The cost is that the picture can only ever show what was persisted; anything a step keeps in memory is not drawable after the fact, which is an argument for persisting more, not for re-running. Page weight grows by about 12 KB per document, which the desk view absorbs (387 KB, no external requests).
