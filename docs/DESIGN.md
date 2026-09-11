# DESIGN.md — Coherence Gate: product phases, priorities, cut lines

**Deadline:** Sunday 2026-09-13 night. **Audience:** one Head of Equities Technology (GOAL.md).
**Rule:** if time runs out we ship a complete, honest product with fewer features, never a
half-built one. Priority order below IS the build order.

## 1. The product in one paragraph

Coherence Gate reads a structured-note term sheet, extracts it twice with two independent
model families (Gemini, Claude), merges the two extractions deterministically, compares the
result against the booking record fetched through an MCP tool, and emits typed per-field
findings. Fields where both families agree and the comparison passes auto-clear with zero
human touch. Everything else goes to a triage lane where an LLM drafts a desk query citing
the exact clause and booking field. An eval harness, built before the pipeline, reports
catch rate on planted discrepancies and false-flag rate on clean fields, with its own
ceiling stated.

## 2. Product phases

### Phase 1 — The gate (this weekend). Everything in GOAL.md and INSTRUCTIONS.md.
Deliverables, in priority order. Each step leaves a demoable product.

| Step | What ships | Checkpoint (binary) | Budget |
|---|---|---|---|
| **S0 Eval first** | `schema/termsheet_v1.json`, 12 term sheets + 12 bookings + 12 truth files, `manifest.json`, eval harness + scoring, stub pipeline | `make eval` runs, prints 0/10 catch in red, writes `eval_report.md` | Fri night |
| **S1 Deterministic core** | `normalize.py`, `merger.py`, `comparator.py`, `lanes.py`, `types.py`, booking store + MCP server/client, unit tests | comparator over hand-written extraction fixtures reproduces manifest findings 10/10, G09 resolves CLEAN, G11/G12 zero findings | Sat AM |
| **S2 Extraction** | `extract_v1.md` prompt, Gemini + Claude extractors, `schema_guard.py`, trace writer | `make eval` end-to-end with real models; iterate prompt only; every iteration logged in `eval_log.md` | Sat PM |
| **S3 Triage + lanes** | `triage/agent.py`, `triage_v1.md`, auto-clear lane logging | G01 triage note reads like a desk query; auto_clear_correctness = 100% | Sat night |
| **S4 Surfaces** | `run_report.html`, `trace_view.py`, `make demo`, README demo script, BRIEF.md results table filled from `eval_report.md`, `runs/showcase/` committed | 5-minute walkthrough runs from a clean clone with only the two keys | Sun |

**Cut lines inside Phase 1** (apply from the bottom up if Sunday afternoon arrives early):
1. `run_report.html` → fall back to a Rich table in the terminal (trace + eval_report.md
   are the real evidence). 
2. MCP server → plain function with the same signature, flagged `transport: "direct"` in the
   trace and one line in BRIEF.md. Timebox for MCP: 2 hours.
3. PDF rendering of 2–3 term sheets → skip; `.txt` only.
4. Triage classification enum → keep the drafted query, drop the classification.
Never cut: the golden set, the eval harness, the false-flag rate, the honest ceiling, the
trace.

### Phase 2 — Hardening (post-interview, 1–2 weeks). Stated in docs, not built.
- Golden set to n≈50 with a second and third layout family (table-first, prose-first,
  bilingual boilerplate), plus PDF ingestion (layout-aware text extraction, page-anchored
  citations).
- Second prompt variant per family and a prompt A/B in the eval log; effort/thinking sweeps
  with cost printed next to each.
- Vertex AI routing for both families (same code path; `GOOGLE_GENAI_USE_VERTEXAI` for
  Gemini, `AnthropicVertex` for Claude) so one governance surface holds both.
- ADK agent wrapper (steps as tools) + Agent Engine deploy; BigQuery sink for `trace.jsonl`;
  Cloud Run job for batch runs.
- Per-field autonomy policy derived from eval history: a field earns AUTO_CLEAR only after
  N consecutive evals with 0 false flags on it.

### Phase 3 — Extension (the roadmap line in BRIEF.md).
- Reconciliation break triage: same gate over two structured records (front-office vs
  back-office) with the extractor step replaced by a loader.
- P&L attribution commentary: model explains, code computes; the eval plants known
  attribution errors.
- Confirmation-draft check: the outbound confirmation as a third "document".

## 3. What is fixed vs open

Fixed by INSTRUCTIONS.md (not redesigned): architecture, schema fields, finding types,
tolerance table (all exact), tech stack, phase order, golden set contents.

Decisions we made on top (see `docs/DECISIONS.md`): `coupon_rate_basis` added to the schema
(ADR-1); model pins gemini-3.8-flash + claude-opus-5 (ADR-2); citation offsets recomputed in
code, model supplies only the verbatim span (ADR-3); merger compares normalized values
(ADR-4); uv + pyproject (ADR-5); MCP over stdio, in-process spawn (ADR-6).

## 4. Time plan (part-time, ~3 days)

| When | Work |
|---|---|
| Fri 11 Sep (tonight) | Design sign-off → S0 (schema loader, golden set, manifest, harness, stub) → commit "S0: eval exists, 0/10" |
| Sat 12 Sep AM | S1 core + tests → commit "S1: fixtures reproduce manifest 10/10" |
| Sat 12 Sep PM | S2 extractors + schema guard + trace → first real eval → prompt iterations logged |
| Sat 12 Sep night | S3 triage + lanes → commit |
| Sun 13 Sep | S4 report, demo, README walkthrough, BRIEF results, showcase run, final eval, tag `v0.1.0` |

## 5. The 5-minute demo script (what S4 must make true)

1. `make demo` → G11 (clean) runs: both extractors agree on 20/20 fields, comparator CLEAN,
   document AUTO_CLEAR, zero human touch, one trace line per step.
2. G10 (barrier omitted): both extractors DECLARE ABSENT → `TS_ABSENT` critical finding →
   triage drafts "Term sheet has no knock-in level; booking shows 70%. Confirm intent."
   The absence announced itself.
3. G09 (per-quarter vs per-annum): Gemini and Claude may extract different raw numbers;
   `normalize.py` maps both to 8.25 p.a.; merger agrees; comparator CLEAN. Code decided.
4. `eval_report.md`: catch rate, false-flag rate, agreement, auto-clear correctness, cost per
   document, honest ceiling. `eval_log.md`: every prompt iteration and what it did.
5. `make trace`: one run, every model call with model id, version, tokens, latency, cost.

## 6. Success criteria mapping (GOAL.md → step)

| GOAL criterion | Delivered by |
|---|---|
| 1. one command end-to-end | S4 `make demo` (S0 already gives `make eval`) |
| 2. honest eval report, both rates | S0 harness + S2 real numbers |
| 3. citation or DECLARED_ABSENT, no silent blank | S1 types + S2 schema guard |
| 4. clean docs zero-touch; discrepant docs triage note | S1 lanes + S3 triage |
| 5. one observability trace | S2 trace writer, S4 trace view |
| 6. one-page BRIEF | S4 |
