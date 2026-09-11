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

> Status: **design complete, build in progress** (Phase 1, step S0). See
> [`docs/DESIGN.md`](docs/DESIGN.md) for the phase plan and
> [`eval_log.md`](eval_log.md) for the numbers as they move.

## Quick start

```bash
git clone https://github.com/sheldongomes1/coherence-gate && cd coherence-gate
make setup                 # uv venv + deps; writes .env from .env.example
# fill GOOGLE_API_KEY and ANTHROPIC_API_KEY in .env
make test                  # deterministic core, no API calls
make eval                  # 12 golden docs -> runs/<ts>/eval_report.md
make demo                  # the 5-minute walkthrough
make trace                 # every model call of the latest run: model, version, tokens, latency, cost
```

## The 5-minute demo

1. **G11, a clean document** auto-clears: both extractors agree on every field, the
   comparator passes, no human touch, one trace line per step.
2. **G10, barrier level omitted**: both extractors declare the field absent; the booking has
   70%; the gate raises a critical `TS_ABSENT` finding and drafts the desk query. The
   absence announced itself.
3. **G09, "2.0625% per quarter (8.25% p.a.)"**: the two families may extract different raw
   numbers; `normalize.py` maps both to 8.25 per annum; no finding. Code decided, not a
   prompt.
4. **`eval_report.md`**: catch rate, false-flag rate, cross-family agreement, auto-clear
   correctness, cost per document, and the honest ceiling (n=12, directional).
5. **`trace.jsonl`**: one full run, every model call traced.

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
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | ADRs |
| [`BRIEF.md`](BRIEF.md) | one page for the evaluator (results filled from the eval report) |
| [`eval_log.md`](eval_log.md) | every prompt/schema/normalizer iteration and what it did to both rates |

## Layout

```
schema/termsheet_v1.json     frozen schema, 20 fields, critical flags
golden/                      12 term sheets, 12 bookings, 12 truth files, manifest.json
prompts/                     extract_v1.md, triage_v1.md (versioned)
config/models.yaml           pinned model ids and prices
src/coherence_gate/          normalize · merger · comparator · lanes · booking/ (MCP) · extract/ · triage/ · eval/ · report/
tests/                       unit tests for the deterministic core, no network
runs/                        one directory per run (git-ignored); runs/showcase is committed
```

## Deployability

Both families are first-class in Vertex Model Garden: Gemini through `google-genai` with
`GOOGLE_GENAI_USE_VERTEXAI=true`, Claude through `AnthropicVertex`. The pipeline is a
sequence of tool-shaped steps with the booking store behind MCP, so it wraps as an ADK agent
on Agent Engine without redesign and runs under one existing Google Cloud governance
surface. Traces are newline JSON, BigQuery-loadable as is.

— Sheldon Gomes
