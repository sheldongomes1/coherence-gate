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
                        ┌─────────────────────────────────────────────────────────────┐
                        │                     pipeline.py (one document)              │
                        │                                                             │
 termsheet.txt ────────►│  load ──► extract(A: Gemini) ──┐                            │
                        │       └─► extract(B: Claude) ──┴─► schema_guard ──► merger  │
                        │                                                     │       │
 golden/bookings/*.json │   booking MCP server ◄── booking client ◄───────────┤       │
 (books & records)      │   booking_lookup(trade_id)                          ▼       │
                        │                                                 comparator  │
                        │                                                     │       │
                        │                                          findings[] (typed) │
                        │                                                     │       │
                        │                                                   lanes     │
                        │                                        ┌────────────┴─────┐ │
                        │                                        ▼                  ▼ │
                        │                                  AUTO_CLEAR           TRIAGE │
                        │                                  (log only)        agent(LLM)│
                        │                                                     │        │
                        │  trace.jsonl ◄── every step ────────────────────────┘        │
                        └─────────────────────────────────────────────────────────────┘
                                                      │
                        runs/<ts>/  findings.json · extractions/ · triage.json · trace.jsonl · run_report.html
                                                      │
                        eval/harness.py runs 12 docs ─► eval/scoring.py vs manifest.json ─► eval_report.md
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
| `report/` | code | Static HTML + trace pretty-print | — |
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
document from these lines, never from estimates.

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
wrapping it as an ADK agent on Agent Engine is a packaging step, not a redesign. Traces are
newline JSON, loadable into BigQuery unchanged. None of this is built in Phase 1; it is what
keeps Phase 1 honest about "runs under an existing governance surface".

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
