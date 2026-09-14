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
- Transport resilience learned in Phase 1: Gemini calls on a consumer connection hung or
  retried for hours until timeouts and retry bounds were made explicit; Gemini 3.8 Flash's
  thinking volume varies 1k–30k tokens per identical call. Phase 2 routes both families
  through Vertex AI (regional endpoint, quota, VPC-SC) and pins a thinking level chosen by the
  effort sweep in `eval_log.md`.
- Parse stage drops page header/footer elements (Mixedbread element types) so a sentence split by a page break can still be cited verbatim; the v0.2 ablation's one residual failure is exactly this case.
- Triage gets the guard-located neighbourhood of the field (±N lines around the citation), so
  an explanatory clause elsewhere can be noticed without handing it the whole document.

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


## 7. v0.2 status (2026-09-12, from docs/V2-CHANGES.md; order per ADR-20)

| Change set | Status | Evidence |
|---|---|---|
| CS1 PDF golden set | done | `make golden`: 15 HTML/PDF/TXT from the approved templates, 4 layouts |
| CS2 Mixedbread ingestion + citation chain + parse-tax ablation | done | `golden/parsed/`, `--source pdf|txt`, `parse_tax.md`; guard hardened for parsed tables |
| CS6 eval report v2 + brief v2 | done | `eval_report.md` sections 1–11; `make brief` |
| CS3 option product + arithmetic relation | done (code + fixtures) | `option_v1.json`, `rel:premium_arithmetic`, G13–G15 |
| CS5 desk view | done | `desk_view.html` per run, ADR-22 |
| CS7a live check | done | `make check DOC=… TRADE=…`, `scripts/rehearse_check.py` |
| CS7c STALE | done | attested hashes in `summary.json`; `test_stale.py` |
| CS4 Versa reference lane | done (code + fixtures) | `reference/`, ADR-23, G09/G14/G03 planted |
| CS7b model-swap diff | done | `eval_diff.md` (medium vs low sweep), `make eval-diff` |
| CS8a OTel-shaped traces | done | `otel` span on every trace line (ADR-25); no exporter wired |
| CS8b desk feedback capture | done | `cg feedback <doc>:<field> --verdict … --note …` → `feedback/feedback.jsonl`; desk-view marker |
| CS8c feedback → proposals | done, one real cycle in git history (feedback → proposal → apply → eval → diff → HELD) | `proposals/`, `eval_diff_cycle.md`, `proposals/DECISIONS.md` |
| Release run on 15 docs, pdf source, reference lane | done: v0.2.0 run 20260912-191532 (17/17, 0/417); v0.2.1 run 20260913-113753 (17/17, 0/399, resumed per ADR-31) | `runs/showcase`, `eval_log.md` |
| MODEL-RISK filled, showcase frozen, v0.2.0 tag | done | `MODEL-RISK.md`, `BRIEF.md`, tag v0.2.0 |
| CS9 provenance graph per deal (2026-09-14) | done | `report/provenance.py`, ADR-33; in the evidence modal and the run report |
| v0.2.1 review pass (2026-09-13): independent review → P0/P1/P2 fixed | done | ADR-29 fast relaunch, ADR-30 NOT_EVALUABLE/INFO lane, cost breakdown by source, web hardening (containment, escaping, MCP, atomic writes), report column 'calls that never completed', `cg eval --resume` (ADR-31), tag v0.2.1 |
| Live-check rehearsal (6 booking edits) | 4/6 caught; 1 Gemini deadline event, 1 masked by the tolerance under test | `eval_log.md` |
