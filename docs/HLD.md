# HLD.md — Coherence Gate: high-level design

## 1. Context and problem

A structured-note term sheet (desk intent, prose + terms table) and its booking record
(books-and-records truth, structured) must say the same thing. Today the check is manual and
scales with trade count. The dangerous failure is silent: one barrier level, day count, or
memory-coupon flag that differs, invisible until a confirmation or coupon payment exposes it.

Coherence Gate is a gate, not a chatbot: given a document and a trade id it produces typed,
per-field verdicts with provenance, auto-clears what it can prove, and drafts the desk query
for what it cannot.

## 2. Design principles (from SKILL.md, enforced by structure)

| Principle | Where it lives structurally |
|---|---|
| Eval before product | `golden/` + `eval/` exist and run at 0% before any extractor code |
| Models extract and explain; code decides | Only `extract/` and `triage/` call models. `normalize.py`, `merger.py`, `comparator.py`, `lanes.py` are pure Python with unit tests |
| Absence announces itself | Extraction type is a closed sum: `EXTRACTED(value, citation)` or `DECLARED_ABSENT`; `schema_guard.py` turns any other shape into a `MALFORMED_EXTRACTION` finding |
| Two families, no arbitration | Merger is a per-field equality check on normalized values; disagreement is a finding type, not a prompt |
| Tiered autonomy | `lanes.py`: per-field AUTO_CLEAR requires agree ∧ CLEAN; document AUTO_CLEAR requires every field to |
| Version the judgment | `schema/termsheet_v1.json`, `prompts/*_v1.md`, tolerance table in code, `golden/manifest.json` with history; model ids pinned in `config/models.yaml` and written to every trace line |
| Honest ceiling | `eval/scoring.py` refuses to write a rate without its n and prints the ceiling section unconditionally |
| Cost and trace are features | `trace.py` is the only way a model call is made (extractors go through it); cost is computed from trace tokens × pinned prices |

## 3. System architecture

```
   term sheet (PDF or text)            booking store (books & records)      Versa methodology (PDF)
            │                                      │                                  │
            ▼                                      │                                  ▼
     parse(pdf)   vendor ML, cached, swappable     │                     reference lane: both families
            │     parsed markdown is what is cited │                     read the rulebook once, cached
            ▼                                      │                                  │
  ┌──────────────────────────────┐                 │                                  │
  │ extract A (Gemini)           │  independent    │                                  │
  │ extract B (Claude)           │  never told     │                                  │
  └──────────────┬───────────────┘  about each other                                  │
                 ▼                                 │                                  │
       schema_guard   span must be verbatim; char offsets recomputed in code           │
                 ▼                                 │                                  │
       normalize ──► merge        agree or EXTRACTOR_DISAGREEMENT, never arbitrated    │
                 │                                 ▼                                  │
                 │                    booking_lookup(trade_id)  ── MCP only ──┐        │
                 └─────────────┬───────────────────────────────────────────────┘       │
                               ▼                                                       │
                      comparator (tolerance table, in code) ── relations ──────────────┘
                               │                               arithmetic      claims vs rules
                               ▼
                       findings[] typed:  CLEAN · MISMATCH · TS_ABSENT · BOOKING_ABSENT
                               │          EXTRACTOR_DISAGREEMENT · MALFORMED_EXTRACTION
                               │          RELATION_VIOLATION · REFERENCE_INCONSISTENT · NOT_EVALUABLE
                               ▼
                 lanes:   AUTO_CLEAR          TRIAGE                 INFO
                          zero human touch    triage agent (LLM)     a check that was not performed:
                                              drafts the desk query  never a pass, never a flag
                               │
  trace.jsonl ◄── every step, every model call, OTel-shaped spans ──┘
                               │
   runs/<ts>/   findings · extractions · merged · booking · triage · summary (attested hashes)
                desk_view.html · run_report.html · <doc>/provenance.svg · eval_report.md
                               │
        ┌──────────────────────┼───────────────────────┐
        ▼                      ▼                       ▼
  BigQuery sink          desk feedback            eval/scoring vs manifest.json
  (cost, never-           → proposals →           catch rate · false flags · ceiling
   completed, drift)       human + eval gate
```

### 3.1 Components

| Component | Kind | Responsibility | Decides? |
|---|---|---|---|
| `extract/gemini.py`, `extract/claude.py` | model | Produce a schema-shaped extraction with a verbatim citation span per field, or an explicit absence | No |
| `extract/schema_guard.py` | code | Validate shape and provenance (span found verbatim in the source; char offsets recomputed); demote violations to `MALFORMED_EXTRACTION` findings | Yes (validity only) |
| `normalize.py` | code | Canonical forms: ISO dates, `Decimal` percents, upper-stripped tickers, per-period coupon → per-annum | Yes |
| `merger.py` | code | Field-wise agreement of the two normalized extractions | Yes |
| `booking/mcp_server.py` + `client.py` | tool | The only path to booking truth. MCP over stdio; JSON per trade id | No |
| `comparator.py` | code | Merged value vs booking value under the v1 tolerance table (all exact) | Yes |
| `lanes.py` | code | AUTO_CLEAR vs TRIAGE, per field and per document | Yes |
| `triage/agent.py` | model | For each non-clean finding: classify (advisory) and draft the desk query from the finding, its citations and the booking field (never the whole document, ADR-17) | No |
| `trace.py` | code | Append one JSON line per step; wraps every model call | — |
| `ingest/` | vendor + code | `parse(pdf)` behind one interface (Mixedbread, local fallback); parsed markdown is cached and is what every citation anchors into | No |
| `reference/lane.py` | model + code | Extract the index methodology once (both families, cached); check term-sheet claims against its rules; `binding=default\|deferred` → NOT_EVALUABLE | Yes (the check; the rule is read by models) |
| `report/` | code | Desk view, run report, trace pretty-print | — |
| `report/provenance.py` | code | Per-deal graph drawn from the stored artifacts; every box links to the artifact that step produced (ADR-33) | — |
| `web/app.py` | code | The demo service: desk view, booking edit, relaunch (recheck vs full re-read), desk feedback | — |
| `sink/bq.py` | code | Load a run's trace into BigQuery, partitioned and clustered, with the drift views (ADR-35) | — |
| `adk/` | code | The same functions composed as ADK workflow agents for Agent Engine; no LLM planner (ADR-34) | No |
| `eval/` | code | Run all golden docs; binary scoring; `eval_report.md` with ceiling | — |

### 3.2 Data flow for one document (happy path, G11)
1. `load` reads the `.txt`, computes sha256 (goes in the trace).
2. Extractors A and B run (concurrently) with the same rendered prompt. Each returns 20
   fields; each field is `EXTRACTED` with a span, or `DECLARED_ABSENT`.
3. `schema_guard` verifies every span is a verbatim substring; recomputes `char_range`.
4. `normalize` canonicalizes both extractions.
5. `merger` compares field by field: all 20 agree → merged extraction carries both citations.
6. `booking client` calls `booking_lookup("SN-…")` over MCP; the record and the transport
   used are logged.
7. `comparator` yields 20 `CLEAN` findings.
8. `lanes` marks 20/20 fields AUTO_CLEAR → document AUTO_CLEAR. Nothing is sent to triage;
   the auto-clear is logged with the evidence (both citations, booking value).

### 3.3 Data flow for a discrepancy (G10, barrier omitted)
Steps 1–4 as above. Both extractors `DECLARED_ABSENT` on `barrier_level_pct`. Merger: agree
on absence. Booking has 70 → comparator emits `TS_ABSENT` (critical). Lanes: the other
fields auto-clear; `barrier_level_pct` goes to TRIAGE. Triage agent receives the finding, its
citations and the booking field (not the document), and drafts the query. Document lane = TRIAGE.

### 3.4 Data flow for the normalizer trap (G09)
Extractor A may return `coupon_rate_pct=2.0625, basis=per_period`; B may return `8.25,
per_annum`. `normalize` produces `coupon_rate_pct_pa = 8.25` for both. Merger agrees on the
canonical value; comparator matches booking 8.25 → CLEAN. No prompt did arithmetic.

## 4. Trust boundaries and failure containment

- **Model output is untrusted input.** Everything from a model passes `schema_guard` before
  any deterministic step sees it. A malformed field is a finding on that field; the rest of
  the document proceeds. A malformed whole response is 20 `MALFORMED_EXTRACTION` findings and
  the document lands in TRIAGE. There is no crash path and no retry-until-pass.
- **Booking truth is reached only through the tool.** No module imports the JSON files
  except the MCP server. The pipeline cannot "peek".
- **Triage cannot change a verdict.** Its output is attached to a finding; it cannot alter
  `type`, `severity`, or lane.
- **Absence cannot be silent.** The extraction model's `value` is `Optional` only under
  `DECLARED_ABSENT`; the guard enforces the pairing. Findings are computed from the closed
  set of schema fields, so a missing field cannot vanish, it becomes `MALFORMED_EXTRACTION`.

## 5. Autonomy model (tiered)

| Condition on a field | Lane | Human touch |
|---|---|---|
| A = B (normalized) ∧ comparator CLEAN | AUTO_CLEAR | none; logged with both citations |
| check not performable (deferred parameter, missing input, families disagree on a rule) | INFO (`NOT_EVALUABLE`) | none; listed, never attested, never a flag |
| A ≠ B | TRIAGE (`EXTRACTOR_DISAGREEMENT`) | desk query drafted |
| A = B ∧ booking differs | TRIAGE (`MISMATCH`) | desk query drafted |
| A = B = ABSENT ∧ booking present | TRIAGE (`TS_ABSENT`) | desk query drafted |
| A = B present ∧ booking missing | TRIAGE (`BOOKING_ABSENT`) | desk query drafted |
| guard violation on A or B | TRIAGE (`MALFORMED_EXTRACTION`) | desk query drafted |

Document lane is AUTO_CLEAR only if every field is. The eval metric
`auto_clear_correctness` verifies no planted field was ever auto-cleared; if it is not 100%
the report prints it in red and the autonomy story is declared dead in the same sentence.

## 6. Observability

`runs/<ts>/trace.jsonl`: one line per step with `run_id, doc_id, step, model, model_version,
prompt_tokens, output_tokens, latency_ms, outcome, cost_usd, detail`. Model version is the
provider-reported id from the response where available. Cost uses `config/models.yaml`
prices. `make trace` renders the latest run as a table; the eval report sums cost per
document from these lines, never from estimates. Two things read the trace and neither changes it:

- **Per-deal provenance graph** (ADR-33, `report/provenance.py`): the six stages for one document —
  inputs, parse, the two readings, normalize and merge, the deterministic decision, lanes and output —
  with what flowed on each edge, what each step cost, and a link from every box to the artifact that
  step produced. Colour separates completed from reused-under-an-unchanged-hash from never-completed,
  so a resumed run cannot read as a cheap one. Drawn from stored artifacts, so it can be produced for
  any past run, including the ones parked as invalid.
- **BigQuery sink** (ADR-35, `cg trace-export`): the same lines, partitioned by day and clustered by
  run, step and document, with two derived columns — `family` and `completed` — and three views:
  cost by run split into readings and desk queries, calls that never completed by family, and the
  per-family latency and thinking profile. The questions that only exist across runs are SQL.

On Agent Engine the OTel-shaped spans land in Cloud Trace without a second instrumentation; the sink
is the offline path for runs that happen on a laptop.

## 7. Evaluation architecture

Mutation-testing framing: each planted finding is a mutant; catch rate is kill rate.
`manifest.json` is the oracle. Scoring is binary per (doc, field, expected type). Metrics:
catch_rate, false_flag_rate (field-level and document-level for G11/G12), extraction
accuracy per family vs `golden/truth/`, agreement rate, auto_clear_correctness, cost per
document. Every number carries its n. See LLD §14.

## 8. Deployability (Google Cloud posture)

Both model families are first-class in Vertex Model Garden: Gemini via `google-genai` with
`GOOGLE_GENAI_USE_VERTEXAI=true`, Claude via `AnthropicVertex`. The pipeline is a sequence of
tool-shaped functions (ADK pattern) with the booking store already behind an MCP tool, so
wrapping it as an ADK agent on Agent Engine is a packaging step, not a redesign — and as of v0.3.0 it
is built (`src/coherence_gate/adk/`, ADR-34): a `SequentialAgent` over a `ParallelAgent` for the two
readings, composed of the same functions the direct path calls, with no `LlmAgent` anywhere in the
tree. The acceptance test is the artifact: the same document through both paths produces identical
findings, identical lanes and identical attestation hashes, so the framework demonstrably changes
nothing about the result. ADK is an optional install and is absent from the lock, because adding it
moved two of the demo image's transitive pins — a framework that quietly changes the service's
dependency floor belongs in its own environment, which is what Agent Engine provides.

The demo itself runs as a FastAPI service on Cloud Run (one instance, secrets from Secret Manager,
no CPU throttling) with the booking store reached through the same MCP tool the eval uses.
`scripts/deploy_agent_engine.py` preflights the Agent Engine path (auth, project, API, staging
bucket, agent tree, pinned requirements) and only deploys behind an explicit flag.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Extractors over-flag (false positives kill desk trust) | G11/G12 clean controls; false-flag rate has equal billing; iterate prompt against both rates |
| Citation spans not verbatim (whitespace, quotes) | Guard normalizes whitespace for matching, records exact source offsets; still MALFORMED if not found |
| MCP plumbing eats time | 2-hour timebox; same-signature direct fallback flagged in trace and brief |
| Model deprecation between now and the call | Pins in one file; `make models` lists live ids; rerun eval and diff (Rule 6) |
| Cost surprise | Two calls per doc + ≤20 triage calls; printed per document in the report |
| ChromeOS dev box memory (6 GB, no swap) | No parallelism beyond 2 concurrent model calls; runs are small |


## 10. v0.2 additions (2026-09-12; docs/V2-CHANGES.md, ADR-20..23)

```
 document.pdf ──► parse(pdf) ─► parsed/<doc>.md (versioned, hashed) ─► [detect product: code]
 (note | OTC option)  Mixedbread | local-fallback        │
                                                         ├─► Extractor A / B (schema per product) ─► guard ─► normalize ─► merge
 methodology.pdf ─► same parse ─► Extractor A / B (reference schema) ─► merge ─► ReferenceRules
                                                         │                                   │
 booking (MCP) ─────────────────────────────────────────► comparator + relations + reference check (code)
                                                         │
                                          findings (typed; rel:* and ref:* keys) ─► lanes ─► triage (LLM)
                                                         │
                       desk_view.html (trust states, STALE by hash) · run_report.html · eval_report.md (parse tax, sweep)
```

| Component | Kind | Decides? | Notes |
|---|---|---|---|
| `ingest/` | vendor ML behind one interface | no | canonical text = parsed markdown; citations anchor into it; artifacts hashed and cached |
| `schema/products.json` + `detect_product` | code | product type | keyword detection; manifest may state it |
| `comparator.check_relations` | code | cross-field arithmetic | `product_equals`; CLEAN states "not evaluable" rather than staying silent |
| `reference/` | models extract the rulebook; code checks | rule vs claim | `binding: rule | default | deferred` (ADR-23); `ref:*` findings |
| `report/desk_view.py` | code | trust state, consequence line | fixed tables (ADR-22); STALE from hashes (CS7c) |
| `cli check` | orchestration | — | one document live, any booking edit; same pipeline |

Trust boundaries unchanged: models never decide; the parse vendor is swappable; the reference
lane can only flag `rule` bindings; a wholesale extractor failure short-circuits triage.

## 11. v0.3 additions (2026-09-14; ADR-33..35)

| Change | Where | Why it is here |
|---|---|---|
| Per-deal provenance graph | `report/provenance.py`, evidence modal, run report, `<doc>/provenance.svg` | "Where did this finding come from" was answerable only by reading a JSONL file |
| ADK packaging | `adk/app.py`, `cg run --via adk`, `make adk-check` | The Agent Engine path, proven equivalent by test rather than asserted |
| BigQuery trace sink | `sink/bq.py`, `cg trace-export`, three views | Drift, cost and failure questions only exist across runs |
| Agent Engine preflight | `scripts/deploy_agent_engine.py`, `make agent-engine` | Deployability checked, not claimed; deploy is behind a flag |
| Hardening from four review passes | `web/app.py`, `pipeline.py`, `eval/harness.py` | A recheck that re-drafted a desk query cost money on every click; public endpoints answered bad input with tracebacks; a stub run skipped the reference lane silently |

The state after those passes: a re-check of an unchanged book makes zero model calls and takes
0.1 s for fifteen documents; the desk view is cached on a fingerprint of the run, the store and the
recorded verdicts (2.4 ms warm, 277 req/s); a full re-read is staged and swapped under the page lock
so no page can pair new findings with an old summary; and the eval's answer key is no longer served
next to the demo it grades.
