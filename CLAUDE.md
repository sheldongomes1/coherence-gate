# CLAUDE.md — Coherence Gate

Read in this order: `GOAL.md` (what/why/success criteria) → `INSTRUCTIONS.md` (fixed
architecture, schema, golden set, phases) → `SKILL.md` (eval-first discipline; applies to
ALL work here) → `docs/DESIGN.md` (phase plan + cut lines) → `docs/HLD.md` → `docs/LLD.md`.

## Non-negotiables (from SKILL.md — enforce, don't re-derive)
- Eval exists before product. `make eval` must run (even at 0%) before any extractor code.
- Models extract and explain; **code decides**. No match/no-match, tolerance, or
  normalization logic in a prompt. If you see it drifting there, move it to `normalize.py`
  / `comparator.py` and add a unit test.
- Absence announces itself. Every field is `EXTRACTED` (with citation) or `DECLARED_ABSENT`.
  A silent blank anywhere is a P0 bug regardless of the current task.
- Two families, no arbitration. Gemini + Claude disagree → `EXTRACTOR_DISAGREEMENT`. Never
  add an LLM tie-breaker.
- Version the judgment: prompts (`prompts/*_v*.md`), schema (`schema/termsheet_v1.json`),
  tolerances (`comparator.py` table), golden set (`golden/manifest.json`) are versioned
  artifacts. Never edit a golden label in the same commit as the code it excuses.
- Every model call is traced (model, version, tokens, latency, outcome) to `trace.jsonl`.
- Every reported number carries n + "directional, not statistically significant" when n is
  small. False-flag rate gets equal billing with catch rate. Red numbers stay red.
- Each model-facing change → one line in `eval_log.md` (date, change, catch, false-flag, notes).

## Stack (fixed)
Python 3.11 + `uv`. `google-genai` (Gemini, extractor A) + `anthropic` SDK 1.x (Claude,
extractor B + triage). Pinned ids in `config/models.yaml` (verify with `make models`).
Booking store = JSON per trade under `golden/bookings/`, served by a stdio MCP server
(`booking_lookup(trade_id)`). Jinja2 → static `run_report.html`. No web server, no Docker,
no auth. Load the `claude-api` skill before touching any Anthropic SDK code (SDK 1.x has
breaking changes from 0.x; use `output_config.format` structured outputs, adaptive thinking).

## Commands
`make setup` · `make test` (no API calls) · `make eval` · `make demo` · `make trace` ·
`make models`. Run outputs land in `runs/<timestamp>/` (git-ignored except `runs/showcase/`).

## Layout
```
schema/termsheet_v1.json      frozen field schema (critical flags)
golden/termsheets/G01..G12.txt  synthetic docs; golden/bookings/G01..G12.json; manifest.json
prompts/extract_v1.md          one prompt, rendered per family; triage_v1.md
src/coherence_gate/
  normalize.py  comparator.py  merger.py  findings.py   deterministic core (unit-tested)
  booking/      mcp_server.py + client.py (booking truth reaches the pipeline ONLY via MCP)
  extract/      base.py gemini.py claude.py schema_guard.py
  triage/       agent.py lanes.py
  report/       html.py trace_view.py
  eval/         harness.py scoring.py
  pipeline.py   cli.py  trace.py  config.py
tests/          unit tests (core) + fixtures (hand-written extractions for Phase 1 checkpoint)
docs/           DESIGN.md HLD.md LLD.md DECISIONS.md
eval_log.md     iteration history (deliverable)
```

## Working style for this repo
- Deadline is Sunday night 2026-09-13. Phase order in `docs/DESIGN.md` is a priority order:
  a complete earlier phase beats a half-built later one. When cutting, cut from the end.
- Prefer small deterministic functions with tests over clever abstractions. No ADK plumbing
  unless it is <1 hour; the pattern (steps as tools) matters, not the badge.
- Commit per phase checkpoint with the checkpoint result in the message.
