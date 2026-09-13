# Coherence Gate

**The term sheet is the desk's intent. The booking record is the bank's truth. This agent
closes the gap between them before a confirmation goes out wrong.**

Two model families (Gemini, Claude) independently extract a structured-note term sheet into
a versioned schema. Every field is either cited to its source span or explicitly declared
absent. Deterministic code merges the two extractions, compares them with the booking record
(fetched through an MCP tool), and decides. Fields where both families agree and the
comparison passes auto-clear with zero human touch. Everything else becomes a typed finding
with an LLM-drafted desk query citing the clause and the booking field.

**Models extract and explain; code decides.** An eval built before the pipeline reports
catch rate on planted discrepancies and false-flag rate on clean fields, with its ceiling
stated.

> Status: **Phase 1 built end to end** (S0–S4). Numbers live in [`BRIEF.md`](BRIEF.md)
> (generated from a run, never typed) and every iteration is in [`eval_log.md`](eval_log.md).
> Phase plan and cut lines: [`docs/DESIGN.md`](docs/DESIGN.md).

## Quick start

```bash
git clone https://github.com/sheldongomes1/coherence-gate && cd coherence-gate
make setup                 # uv venv + deps; writes .env from .env.example
# fill GOOGLE_API_KEY and ANTHROPIC_API_KEY in .env
make test                  # deterministic core: 50+ unit tests, no API calls, ~2 s
make demo                  # the 5-minute walkthrough (3 documents, triage on, ~3 min, ~$0.40)
make eval                  # all 12 golden docs -> runs/<ts>/eval_report.md (~10 min, ~$1.40)
make trace                 # every model call of the latest run: model, version, tokens, latency, cost
make report RUN=...        # re-render run_report.html; make brief RUN=runs/<ts> regenerates BRIEF.md
make models                # list live model ids on both APIs (verify the pins in config/models.yaml)
```

Do not run `make demo` and `make eval` at the same time on one set of API keys: the runs compete for the same rate limits and a slow Gemini call can time out, which the gate reports honestly as a wholesale extraction failure (ADR-18) but which makes a poor demo.

**Feedback loop (CS8).** `uv run cg feedback G01:barrier_level_pct --verdict desk_rejected --note "…"`
records a desk disposition (in production, a button on the desk-view row; the CLI stands in for it).
`uv run cg propose` turns feedback into reviewable proposals under `proposals/`, each ending with
"PROPOSAL ONLY". Nothing is applied by the system: a human applies a proposal in its own commit, runs
`make eval`, and `make eval-diff` shows the effect. The model never learns.
One real cycle is in the history: the desk rejected G02's autocall-date finding, `cg propose` drafted a
3-day tolerance, it was applied in its own commit and measured (`eval_diff_cycle.md`): strict catch
17/17 → 16/17 and a planted case was auto-cleared, so the proposal was **held** and reverted
(`proposals/DECISIONS.md`). The proposal file stays on record, unapplied.

Other useful entry points: `uv run cg run golden/termsheets/G05.txt --triage` runs one
document; `uv run cg eval --stub` runs the harness with no model calls (the Phase 0 state);
`--booking direct` bypasses the MCP transport with the same interface.

## The 5-minute demo (v0.2)

1. **Open the OTC option PDF** (`templates/golden/OP-2026-0114_approved.pdf`): the shape of the
   real trade, an insurer hedging fixed-indexed-annuity crediting on Versa 10.
2. **`runs/showcase/desk_view.html`**, the 6am page: the attested book, the rows that need
   attention with one line of desk consequence each, and the cost line for the whole book.
3. **Click a red row**, for example the participation mismatch: the run-report anchor shows the
   typed finding, both families' verbatim citations into the parsed text (parse job id shown),
   and the drafted desk query.
   **3b. Change the booking yourself** (any field in `golden/bookings/<trade>.json`) and run
   `make check DOC=golden/pdf/G14.pdf`: the generic pipeline catches the edit class or, if it
   does not, that is a finding for the honest ceiling. Regenerate the desk view and the row is
   STALE until the re-check attests it again.
4. **The refused-ambiguity moment**: an all-numeric date like 03/04/2026 becomes a finding, not a
   guess (ADR-14).
5. **`eval_report.md`**: strict catch rate with the field-level row beneath, false flags at equal
   prominence, the parse tax, the effort sweep, and the honest ceiling. End on the ceiling.

The older three-document walkthrough (`make demo`) still runs: G11 auto-clears, G10 announces
its missing barrier, G09 survives the per-quarter/per-annum trap.

1. **G11, a clean document** auto-clears: both extractors agree on every field, the
   comparator passes, no human touch, one trace line per step.
2. **G10, barrier level omitted**: both extractors declare the field absent; the booking has
   70%; the gate raises a critical `TS_ABSENT` finding and drafts the desk query. The
   absence announced itself.
3. **G09, "2.0625% per quarter (8.25% p.a.)"**: the two families may extract different raw
   numbers; `normalize.py` maps both to 8.25 per annum; no finding. Code decided, not a
   prompt.
4. **`eval_report.md`** (`make eval`): catch rate on planted discrepancies, false-flag rate on
   clean fields, cross-family agreement, auto-clear correctness, cost per document, and the
   honest ceiling (n=12, directional). `eval_log.md` shows every iteration, including the
   run that hung and the normalizer fixes.
5. **`make trace`**: one full run, every model call with model id, provider-reported version,
   tokens, latency and cost.

## What the eval measures (and cannot)

Mutation-testing framing: each planted discrepancy is a mutant, catch rate is kill rate.
Nine planted findings, one must-not-flag trap (per-quarter vs per-annum coupon), two clean
controls that measure over-flagging. Strict catch requires the right field *and* the right
finding type; a field-only row is shown as a diagnostic. The eval only sees error classes it
plants, on four synthetic layout families, with one prompt per family. n=12: directional.

## Architecture

```
term_sheet.txt ──► Extractor A (Gemini) ──┐
               ──► Extractor B (Claude) ──┴─► schema guard ─► normalize ─► merger (deterministic)
                                                                              │
booking store (JSON) ─► MCP tool booking_lookup(trade_id) ─────────► comparator (deterministic)
                                                                              │
                                                                   findings, typed per field
                                                              ┌───────────────┴───────────────┐
                                                        AUTO_CLEAR lane                 TRIAGE agent (LLM)
                                                        (agree ∧ pass; log only)        drafts desk query
                                                                              │
                                                    run_report.html · trace.jsonl · eval_report.md
```

| Decided by code | Done by models |
|---|---|
| normalization, merge, match/no-match, tolerances, lanes, scoring | extraction with citations, declaring absence, drafting the desk query |

## Documents

| File | What |
|---|---|
| [`GOAL.md`](GOAL.md) | what, for whom, success criteria, out of scope |
| [`INSTRUCTIONS.md`](INSTRUCTIONS.md) | fixed architecture, schema, golden set, phases |
| [`SKILL.md`](SKILL.md) | eval-first discipline applied to every change |
| [`docs/DESIGN.md`](docs/DESIGN.md) | phases 1–3, priorities, cut lines, timeline |
| [`docs/HLD.md`](docs/HLD.md) | components, data flows, trust boundaries, autonomy model |
| [`docs/LLD.md`](docs/LLD.md) | module contracts, normalization and tolerance tables, scoring formulas |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | 17 ADRs, including the ones made at build checkpoints (schema shape, effort, triage context) |
| [`docs/lessons.md`](docs/lessons.md) | what broke during the build and what it taught |
| [`docs/V2-CHANGES.md`](docs/V2-CHANGES.md) | the v0.2 change sets (PDF ingestion, option product, reference lane, desk view, live check) |
| [`docs/MODEL-RISK.md`](docs/MODEL-RISK.md) | model-risk summary in committee format, values filled from a run |
| [`eval_diff.md`](eval_diff.md) | a model/effort change as a before/after diff: "a deprecation is a rerun and a comparison" |
| [`BRIEF.md`](BRIEF.md) | one page for the evaluator; results table generated from a run by `scripts/fill_brief.py` |
| [`eval_log.md`](eval_log.md) | every prompt/schema/normalizer iteration and what it did to both rates |

## Layout

```
schema/termsheet_v1.json     frozen schema, 20 fields, critical flags
golden/                      12 term sheets, 12 bookings, 12 truth files, manifest.json (generated: scripts/gen_golden.py)
prompts/                     extract_v1.md, triage_v1.md (versioned; a change = new file + eval_log line)
config/models.yaml           pinned model ids, prices, effort settings, timeouts
templates/                   run_report.html.j2
src/coherence_gate/          normalize · merger · comparator · lanes · booking/ (MCP) · extract/ · triage/ · eval/ · report/
tests/                       unit tests for the deterministic core, no network
runs/                        one directory per run (git-ignored); runs/showcase is committed
```

## Deployability

Both families are first-class in Vertex Model Garden: Gemini through `google-genai` with
`GOOGLE_GENAI_USE_VERTEXAI=true`, Claude through `AnthropicVertex`. The pipeline is a
sequence of tool-shaped steps with the booking store behind MCP, so it wraps as an ADK agent
on Agent Engine without redesign and runs under one existing Google Cloud governance
surface. Traces are newline JSON with an OpenTelemetry GenAI-shaped span on every line
(`gen_ai.request.model`, token usage, tool spans), so on Agent Engine they land in Cloud Trace
and Cloud Logging without re-instrumentation; export is not wired in this build.

— Sheldon Gomes
