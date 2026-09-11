# INSTRUCTIONS.md — Coherence Gate build plan

Read GOAL.md first. Follow SKILL.md (eval-first discipline) at every step.
Build in the phase order below. Each phase ends with a checkpoint that must
pass before the next phase starts. If time runs out, ship whatever phase is
complete — earlier phases are the product; later ones are polish.

---

## Architecture (fixed — do not redesign)

```
term_sheet.txt/.pdf ──► Extractor A (Gemini)  ──┐
                                                ├─► Agreement Merger (deterministic)
                    ──► Extractor B (Claude)  ──┘        │
                                                         ▼
booking_store (JSON/SQLite, ──► exposed as MCP tool ──► Comparator (deterministic)
 the "books & records")                                   │
                                                          ▼
                                              Findings (typed, per field)
                                                          │
                                        ┌─────────────────┴──────────────┐
                                        ▼                                ▼
                              AUTO_CLEAR lane                    Triage Agent (LLM)
                        (both extractors agree AND          (classifies each finding,
                         comparator passes → log only)       drafts desk query citing
                                                             clause + booking field)
                                                          │
                                                          ▼
                                        run_report.html + trace.jsonl + eval_report.md
```

Principles baked into the architecture (from cross-system philosophy):
- **Models extract and explain; code decides.** The comparator and merger are
  pure deterministic Python. No LLM ever decides "match / no match".
- **Dual-family extraction is the core mechanic**, not a bolted-on judge:
  two model families (Gemini + Claude) independently extract; a field where
  they disagree is AUTOMATICALLY a finding (`EXTRACTOR_DISAGREEMENT`). No LLM
  arbitration between them.
- **Absence announces itself.** Every schema field is either extracted WITH a
  citation or explicitly `DECLARED_ABSENT`. A blank is a bug.
- **Tiered autonomy.** Autonomy is earned per field, not granted globally:
  agree + match → auto-clear (zero human touch, logged); anything else →
  triage queue with a drafted query. Say this in the brief.

## Tech choices (fixed)

- Python 3.11+, plain `venv` + `requirements.txt` (or `uv`). A `Makefile` with
  `make demo`, `make eval`, `make test`.
- Model calls: `google-genai` for Gemini, `anthropic` for Claude, called
  directly for demo speed. In BRIEF.md note: "both families are first-class in
  Vertex Model Garden, so the same pipeline runs under one Vertex governance
  surface; ADK/Agent Engine deployable." Structure the pipeline as an ADK-style
  agent (steps as tools) if cheap; do NOT let ADK plumbing eat a day — the
  pattern matters, not the framework badge.
- Booking store: a JSON file per trade keyed by trade_id, wrapped in a tiny
  **MCP server** (`booking_lookup(trade_id) -> record`). The triage/extraction
  side reaches booking truth ONLY through this tool. If MCP integration burns
  more than ~2 hours, fall back to a plain function with an interface comment
  and a BRIEF.md note that it is MCP-shaped; do not lose the day.
- Traces: append one JSON line per pipeline step to `runs/<ts>/trace.jsonl`
  with: step, model, model_version, prompt_tokens, output_tokens, latency_ms,
  outcome. A tiny `trace_view.py` pretty-prints one run.
- Report: Jinja2 → static `run_report.html` (findings table, per-field lanes,
  citations shown inline). No web server.

## The schema (v1 — freeze it, version it)

`schema/termsheet_v1.json` — every field: name, type, description, and
`critical: true/false`. Fields:

| field | type | critical |
|---|---|---|
| trade_id | str | yes |
| issuer | str | yes |
| notional | decimal | yes |
| currency | ISO-4217 str | yes |
| trade_date | date | yes |
| issue_date | date | no |
| maturity_date | date | yes |
| underlyings | list[str] (Bloomberg tickers) | yes |
| initial_level_pct | decimal (per underlying) | yes |
| barrier_type | enum {european, american, none} | yes |
| barrier_level_pct | decimal or ABSENT | yes |
| coupon_rate_pct | decimal | yes |
| coupon_frequency | enum {monthly, quarterly, semiannual, annual} | yes |
| coupon_memory | bool | yes |
| autocall_observation_dates | list[date] or ABSENT | no |
| autocall_level_pct | decimal or list[decimal] or ABSENT | no |
| day_count | enum {30/360, ACT/360, ACT/365} | yes |
| settlement | enum {cash, physical} | no |
| business_day_convention | enum {following, mod_following, preceding} | no |

Extraction output per field: `{value, citation: {text_span, char_range}, status:
EXTRACTED | DECLARED_ABSENT}`. Normalization rules (dates → ISO, percents →
decimal, "8.25% per annum, paid quarterly" → rate 8.25 + frequency quarterly)
live in ONE deterministic `normalize.py` — never inside the prompt.

Comparator tolerance table (deterministic, in code, documented): dates exact;
decimals exact after normalization; tickers exact after uppercase/strip;
enums exact. No fuzzy matching in v1 — a near-miss IS a finding.

## Finding types (closed set)

`MISMATCH` (extractors agree, booking differs) · `EXTRACTOR_DISAGREEMENT`
(families differ → automatic flag, no arbitration) · `TS_ABSENT` (schema field
declared absent in term sheet but present in booking) · `BOOKING_ABSENT`
(present in TS, missing in booking) · `CLEAN` (per-field pass).
Severity = `critical` flag from schema.

## Golden set (build this BEFORE any pipeline code — SKILL.md rule 1)

`golden/` contains 12 synthetic term sheets + 12 booking records + a
`manifest.json` labeling every planted finding (file, field, type, expected
severity). Ten discrepant documents, one planted finding each unless noted:

1. **G01 barrier level**: TS 65%, booking 70%.
2. **G02 observation date**: one autocall observation date shifted +1 business day.
3. **G03 day count**: TS ACT/360, booking 30/360.
4. **G04 memory coupon**: TS has memory feature clause; booking `coupon_memory: false`.
5. **G05 notional magnitude**: TS USD 10,000,000; booking 1,000,000.
6. **G06 currency**: TS USD, booking CAD.
7. **G07 autocall step-down**: TS autocall levels 100/95/90; booking flat 100/100/100.
8. **G08 underlying**: TS SX5E; booking SPX.
9. **G09 rate-vs-frequency semantics**: TS "2.0625% per quarter (8.25% p.a.)";
   booking coupon_rate_pct 8.25 + frequency quarterly. NOT a mismatch —
   normalization must resolve it. This one tests the normalizer, and it is the
   planted trap for naive extraction.
10. **G10 declared absence**: TS genuinely omits barrier level; booking has 70%.
    Expected finding: `TS_ABSENT`, critical. This is the silent-failure test.

Plus **G11, G12: clean documents** — zero findings expected. These measure the
false-flag rate; without them the eval cannot see over-flagging, and desk
trust dies from false positives faster than from misses.

Term sheets: realistic prose (title, parties, product description, the terms
embedded in sentences and a terms table, some boilerplate/risk language as
distractors). Vary layout across documents so extraction is not table-lookup.
Write them as `.txt` (render 2–3 to PDF only if trivial).

## Eval harness (`make eval`)

Runs the full pipeline over all 12 documents, then scores against
`manifest.json`, mutation-testing style — each planted finding is a mutant,
catch rate is kill rate:

- **catch_rate**: planted findings correctly reported (right field, right type) / planted
- **false_flag_rate**: findings reported on clean fields / total clean fields
  (report G11+G12 separately as document-level false alarms too)
- **extraction_accuracy** per extractor vs golden field values
- **agreement_rate** between the two families
- **auto_clear_correctness**: no field auto-cleared that manifest says is planted
  (this number must be 100% or the tiered-autonomy story is dead — if it is
  not 100%, say so in red, do not hide it)

Output `eval_report.md`: results table, per-finding detail, and an
**Honest Ceiling** section stating n=12 documents / 10 planted findings,
"directional, not statistically significant", what the eval cannot catch
(unplanted error classes, layout families not represented, one prompt per
extractor), and the cost per document (tokens × current prices).

## Phases and checkpoints

- **Phase 0 (½ day): schema + golden set + manifest + eval harness skeleton.**
  Checkpoint: `make eval` runs with a stub pipeline and reports 0% catch rate.
  The eval exists before the product. Non-negotiable.
- **Phase 1 (½ day): deterministic core.** normalize.py, comparator, merger,
  booking store + MCP tool, finding types. Unit tests on G09-style
  normalization. Checkpoint: comparator over hand-written extraction fixtures
  reproduces manifest findings exactly (100%).
- **Phase 2 (1 day): extraction.** One prompt per family (same instructions,
  family-idiomatic), citation + DECLARED_ABSENT enforced by output schema
  validation; a malformed extraction is itself a finding, never a crash.
  Checkpoint: `make eval` end-to-end; iterate on the PROMPT only until catch
  rate plateaus. Log every iteration's scores in `eval_log.md` (the fix
  history is demo material).
- **Phase 3 (½ day): triage agent + lanes.** LLM classifies each finding,
  drafts the desk query citing clause text + booking field; auto-clear lane
  logs. Checkpoint: G01's triage note reads like something a desk would accept.
- **Phase 4 (½ day): traces, run_report.html, BRIEF.md, README with the demo
  script (the exact 5-minute walkthrough: clean doc auto-clears → G10 absence
  announces itself → G09 normalizer resolves the trap → eval report → one trace).**

## BRIEF.md (one page, punchline first)

Problem (2 sentences, headcount-scaling document work; silent divergence) →
the sentence handle → architecture diagram → what the AI decides vs what code
decides → results table from eval_report → honest ceiling → roadmap line
("the same gate pattern extends to reconciliation break triage and P&L
attribution commentary") → deployability line ("built on ADK patterns, both
model families first-class in Vertex Model Garden, tools via MCP — runs inside
an existing Google Cloud governance posture unchanged").
