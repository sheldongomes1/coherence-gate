# LLD.md — Coherence Gate: low-level design

Module-by-module contracts. Section numbers are referenced from the stub docstrings in
`src/coherence_gate/`. Types are Pydantic v2 unless noted. `Decimal` is `decimal.Decimal`.

## 1. `pipeline.py` — orchestration

```python
def run_document(doc_path: Path, trade_id: str | None, ctx: RunContext) -> DocumentResult
```
Steps, each a tool-shaped function `(inputs, ctx) -> outputs` that appends one trace line:
`load_document → extract_gemini ∥ extract_claude → guard → normalize → merge →
booking_lookup → compare → assign_lanes → triage (only TRIAGE findings) → persist`.
`trade_id` defaults to the `trade_id` field on which both extractors agree (after
normalization); if they do not,
the document cannot be looked up and every field becomes `BOOKING_ABSENT` with a note (this
is itself the correct verdict: an unidentifiable document cannot auto-clear).

`RunContext`: `run_id` (timestamp), `out_dir`, `config`, `tracer`, `booking_client`,
`extractors`, `triage_agent`, `stub: bool`.

`DocumentResult`: `doc_id, sha256, extractions{gemini, claude}, merged, booking, findings[],
lanes, triage_notes[], document_lane`.

## 2. `config.py`

Loads `config/models.yaml` and `.env` (`python-dotenv`). Env overrides:
`CG_MODEL_GEMINI`, `CG_MODEL_CLAUDE`, `CG_MODEL_TRIAGE`. Exposes `ModelPin(family, model,
price_in, price_out)`. A model id not in the YAML `alternatives` list logs a warning line to
the trace (`step="config", outcome="UNPINNED_MODEL"`), it does not block.

## 3. `types.py` — the closed vocabulary

```python
class Status(StrEnum): EXTRACTED, DECLARED_ABSENT
class FindingType(StrEnum): CLEAN, MISMATCH, EXTRACTOR_DISAGREEMENT, TS_ABSENT, BOOKING_ABSENT, MALFORMED_EXTRACTION
class Severity(StrEnum): critical, minor          # = schema `critical` flag
class Lane(StrEnum): AUTO_CLEAR, TRIAGE
class Family(StrEnum): gemini, claude

class Citation(BaseModel): text_span: str; char_range: tuple[int, int]   # range recomputed by guard
class FieldExtraction(BaseModel):
    status: Status; value: Any | None; citation: Citation | None; note: str | None
    # model_validator: EXTRACTED ⇒ value≠None ∧ citation≠None; DECLARED_ABSENT ⇒ value is None ∧ citation is None
class Extraction(BaseModel): family: Family; model: str; fields: dict[str, FieldExtraction]; raw: str
class NormalizedField(BaseModel): key: str; value: Any | None; absent: bool; source: FieldExtraction
class MergedField(BaseModel):
    key: str; agree: bool; value: Any | None; absent: bool
    a: NormalizedField; b: NormalizedField; malformed: list[Family]
class Finding(BaseModel):
    id: str            # f"{doc_id}:{field}"
    doc_id: str; field: str; type: FindingType; severity: Severity
    ts_value: Any | None; booking_value: Any | None
    citations: list[Citation]          # from both families when they agree
    detail: str                         # human string built by code, e.g. "TS 65 ≠ booking 70"
    lane: Lane
    triage: TriageNote | None = None
class TriageNote(BaseModel):
    classification: Literal["BOOKING_LIKELY_WRONG","DOCUMENT_LIKELY_WRONG","GENUINE_AMBIGUITY","EXTRACTION_QUALITY"]
    desk_query: str; cited_clause: str; booking_field: str; booking_value: str; rationale: str
```
`MALFORMED_EXTRACTION` is an addition to the INSTRUCTIONS closed set (ADR-7): it is how a
bad model response becomes a finding rather than a crash. It is scored as a false flag if it
lands on a clean field, so over-strict guarding is visible.

### 3.1 `schema_loader.py`
`load_schema() -> Schema` reads `schema/termsheet_v1.json` into `FieldSpec(name, type,
critical, enum, description)` and exposes `names`, `comparison_keys` (19: all fields minus
`coupon_rate_basis`) and `prompt_table()`. The JSON file is the single source of truth for
the prompt table, the output schema (`extract/base.py::raw_extraction_json_schema`, see
§9.1a) and the comparison keys. (`build_extraction_model` still exists for tests; the
Pydantic-derived JSON schema is NOT what the models are constrained with, see ADR-16.)

## 4. `normalize.py` — canonical forms (pure functions, unit-tested)

| Field type | Rule | Examples |
|---|---|---|
| `date` | Parse `YYYY-MM-DD`, `DD Month YYYY`, `Month DD, YYYY`, `DD/MM/YYYY` (documents are European; day-first). Output ISO string. Ambiguous → `NormalizeError` → MALFORMED | `"17 April 2026"→"2026-04-17"` |
| `decimal` | Strip `,`, `%`, currency words, `mm/m/bn` multipliers; `Decimal(...).normalize()` so `8.25 == 8.2500` | `"USD 10,000,000"→10000000`; `"10mm"→10000000` |
| `iso4217` | Upper, strip; must be 3 letters | `"usd "→"USD"` |
| `ticker` | Upper, strip, drop ` Index`/` Equity` suffix and exchange suffix after space | `"SX5E Index"→"SX5E"` |
| `list[ticker]` | Each element as above; order preserved | |
| `list[date]` | Each element as date; order preserved | |
| `enum` | Lower, strip, synonym map in code: `{"modified following": "mod_following", "act/360": "ACT/360", "actual/360": "ACT/360", "30e/360": "30/360", "semi-annual": "semiannual", ...}` | |
| `bool` | Accept `true/false/yes/no` | |
| **coupon** | `coupon_rate_pct_pa = rate × periods(frequency)` if `basis == per_period` else `rate`; `periods = {monthly:12, quarterly:4, semiannual:2, annual:1}` | G09: `2.0625 × 4 = 8.25` |
| `barrier_level_pct`, `initial_level_pct`, `autocall_level_pct` | decimal, or list of decimal; a list of identical values is NOT collapsed (booking `[100,100,100]` vs TS `100` is a MISMATCH by shape — a near-miss IS a finding) | |

`normalize_extraction(ext: Extraction, schema) -> dict[str, NormalizedField]`. Derived key
`coupon_rate_pct` is replaced by its per-annum canonical value; `coupon_rate_basis` is kept
for the report but excluded from comparison and from the false-flag denominator (it has no
booking counterpart). Comparison keys = schema fields − `{coupon_rate_basis}` = 19.

## 5. `merger.py`

```python
def merge(a: dict[str, NormalizedField], b: dict[str, NormalizedField], schema) -> dict[str, MergedField]
```
Per comparison key, truth table:

| A | B | agree | merged |
|---|---|---|---|
| value x | value x (equal after normalize) | True | x, citations [a, b] |
| value x | value y | False | — → `EXTRACTOR_DISAGREEMENT` |
| ABSENT | ABSENT | True | absent |
| value x | ABSENT | False | — → `EXTRACTOR_DISAGREEMENT` |
| MALFORMED | anything | False | — → `MALFORMED_EXTRACTION` (families listed) |

Equality: `Decimal` compare after `normalize()`; lists element-wise and length; strings
exact. No fuzzy matching anywhere.

## 6. `comparator.py`

```python
TOLERANCE_V1 = {"date": "exact", "decimal": "exact", "iso4217": "exact", "ticker": "exact", "enum": "exact", "bool": "exact", "list": "exact_ordered"}
def compare(merged: dict[str, MergedField], booking: dict | None, schema) -> list[Finding]
```
Per comparison key:

| merged | booking | finding |
|---|---|---|
| not agree | — | `EXTRACTOR_DISAGREEMENT` / `MALFORMED_EXTRACTION` (from merger) |
| absent | present | `TS_ABSENT` |
| absent | absent | `CLEAN` (both silent on an optional field is coherent) |
| value | missing key | `BOOKING_ABSENT` |
| value | equal | `CLEAN` |
| value | different | `MISMATCH` |
| any | booking record NOT_FOUND | `BOOKING_ABSENT` on every key, detail "trade_id not found" |

Booking values pass through the same `normalize` functions before comparison, so booking
`"2026-04-17"` and `"17/04/2026"` are equal; booking is expected canonical but is not trusted
to be. Severity = schema `critical` flag. `detail` is composed by code from both values.

## 7. `lanes.py`

```python
def assign(findings: list[Finding]) -> tuple[list[Finding], Lane]
```
Field lane: `AUTO_CLEAR` iff `type == CLEAN` (CLEAN already implies agreement). Document
lane: `AUTO_CLEAR` iff all fields AUTO_CLEAR, else `TRIAGE`. Auto-cleared fields are written
to `auto_clear.json` with both citations and the booking value: the zero-touch path still
leaves an audit trail.

## 8. `booking/` — the MCP tool

Store: `golden/bookings/<TRADE_ID>.json`, one flat JSON object per trade, keys = schema
comparison keys (booking values already per-annum, ISO dates, canonical enums). A `trades/`
index file is not needed; the file name is the key.

Server (`mcp_server.py`): `FastMCP("booking-store")` with one tool
`booking_lookup(trade_id: str) -> dict` returning `{"found": true, "record": {...}}` or
`{"found": false, "trade_id": ...}`. Runs over stdio: `python -m coherence_gate.booking.mcp_server --store golden/bookings`.

Client (`client.py`): `BookingClient.lookup(trade_id) -> BookingLookup(found, record,
transport)`. Spawns the server as a subprocess via `mcp.client.stdio` once per run, holds the
session, `asyncio.run` bridging for the sync pipeline. `transport="mcp-stdio"` is written to
the trace. Fallback (`--booking-transport direct`): `DirectBookingClient` with the identical
signature calling the same store function; `transport="direct"`. Timebox 2h (DESIGN §2).

## 9. `extract/` — dual-family extraction

### 9.1 Prompt (`prompts/extract_v1.md`, Jinja2)
One instruction set rendered for both families with `{{ schema_table }}` (name, type,
description, from the JSON schema) and `{{ document }}`. Instruction content: extract every
field; for each give `status`, `value` as written in the document (no unit conversion, no
arithmetic, no inference from market convention), and `citation.text_span` copied verbatim
from the document; if the document does not state a field, set `DECLARED_ABSENT` and do not
guess. No tolerances, no normalization rules, no examples of arithmetic (Rule 3). Family
idiom differences are limited to: system vs user placement and the structured-output
mechanism.

### 9.1a Output contract (as built, ADR-16)
Both families are constrained with ONE hand-built, union-free JSON schema of three flat maps
keyed by field name: `status` (enum EXTRACTED | DECLARED_ABSENT), `value` (string as written;
array of strings for list fields; "" / [] when absent), `citation` (verbatim span string; ""
when absent). No per-field `note`. Claude's structured-output grammar compiler rejected both
the Pydantic-derived schema (60 union-typed parameters, limit 16) and 20 nested per-field
objects ("compiled grammar too large"); the three-map shape compiles on both APIs. The guard
(`_per_field`) converts the maps to per-field records before validation.

### 9.2 `gemini.py`
`google-genai`: `client.models.generate_content(model=pin, contents=prompt,
config=GenerateContentConfig(system_instruction=SYSTEM, response_mime_type="application/json",
response_json_schema=<three-map schema>, temperature=0, max_output_tokens=32000,
thinking_config=ThinkingConfig(thinking_level=<config>)))`. The output cap INCLUDES thinking
tokens on Gemini 3.x (an 8k cap truncated the JSON). `HttpOptions(timeout=ms,
retry_options=HttpRetryOptions(attempts=2))`: without explicit bounds one call retried for
2.2 h. Usage from `usage_metadata` (thoughts billed as output); `model_version` from the response.

### 9.3 `claude.py`
`anthropic` SDK 1.x: `client.messages.create(model=pin, max_tokens=16000, system=SYSTEM,
messages=[...], output_config={"effort": <config>, "format": {"type": "json_schema",
"schema": <three-map schema>}})`; JSON is the first text block. Adaptive thinking is the
model default. `Anthropic(timeout=240, max_retries=2)`. `stop_reason == "refusal"` is a
`REFUSAL` outcome (all fields Malformed), no fallback model is invoked (the trace must name
the pinned model that actually ran).
Both extractors are wrapped by `trace.timed_call(step="extract:<family>")`, which records
tokens, latency, and outcome (`OK | MALFORMED | API_ERROR`). An API error after the SDK's own
retries is an outcome, not an exception: every field becomes `MALFORMED_EXTRACTION` with
detail = error class.

### 9.4 `schema_guard.py`
```python
def guard(raw: str | dict, document: str, schema) -> tuple[Extraction, list[GuardViolation]]
```
Checks, per field: present; status in enum; value/citation pairing invariant; `text_span`
found in `document` (exact first, then whitespace-collapsed; the match position in the
ORIGINAL document becomes `char_range`; model-supplied offsets are ignored). Type-shape check
against the schema type (a string where a list is expected). Each violation demotes that
field to a `MALFORMED` marker consumed by the merger. The rest of the extraction survives.

## 10. `trace.py`

```python
class Tracer:
    def step(self, *, doc_id, step, outcome, model=None, model_version=None, prompt_tokens=0, output_tokens=0, latency_ms=0, detail=None) -> None
    @contextmanager
    def timed(self, doc_id, step, model_pin=None): ...   # measures latency, computes cost_usd from pin prices
```
Line schema (`trace.jsonl`): `{ts, run_id, doc_id, step, model, model_version,
prompt_tokens, output_tokens, latency_ms, cost_usd, outcome, detail}`. Append-only, flushed
per line so a crash mid-run still leaves a readable trace.

## 11. `triage/agent.py`

Input per finding (ADR-17): the `Finding`, its schema description, the finding type's
meaning, both extracted values, the booking field name and value, the comparator detail and
both citation spans. NOT the full document and NOT the full booking record. Prompt `prompts/triage_v1.md`: "Classify and draft a desk query. Do not
decide whether the values match; that has been decided. Cite the clause verbatim and the
booking field by name." Output constrained to `TriageNote` via structured outputs. Model:
`claude-opus-5` (pin). One call per TRIAGE finding, traced as `triage:<field>`. A malformed
triage response yields `TriageNote(classification="EXTRACTION_QUALITY", desk_query="<triage
unavailable: {reason}>")`; the finding still reaches the queue.

Clean documents never invoke triage (zero model calls after extraction), which is the
tiered-autonomy cost story in the report. A wholesale extractor failure (every field of one
family Malformed for one reason: timeout, API error, refusal, non-JSON) gets a deterministic
note from the pipeline and no triage calls (ADR-18); the trace line is
`triage / SKIPPED_WHOLESALE_FAILURE`.

## 12. `cli.py`

| Command | Effect |
|---|---|
| `cg run <termsheet.txt> [--trade-id X] [--out runs]` | one document → `runs/<ts>/` |
| `cg eval --golden golden --out runs [--stub]` | all 12 → `eval_report.md` (+ line appended to nothing; `eval_log.md` is edited by hand, Rule 8) |
| `cg demo` | scripted walkthrough: G11, G10, G09, then prints where the report, eval report, and trace live |
| `cg trace --latest runs` | table of the latest run's trace |
| `cg report --latest runs` | re-render `run_report.html` |

## 13. `report/`

`html.py`: Jinja2 template `templates/run_report.html.j2` → one static page per run:
document header (id, sha, lane), findings table (field, type, severity, TS value, booking
value, lane), citations inline (span + offsets), triage notes, per-step trace summary, cost.
No JS dependencies; inline CSS. `trace_view.py`: Rich table of `trace.jsonl`.

## 14. `eval/` — harness and scoring

`harness.run(golden_dir, out_dir, stub) -> EvalResult`: for each manifest document run the
pipeline (stub extractors when `--stub`: they return an API_ERROR outcome so every field is
MALFORMED and catch rate is 0/10 by construction; no fake successes).

Scoring (binary, counts):

| Metric | Definition |
|---|---|
| `catch_rate` | planted findings with a reported finding of the same (doc, field, type) / planted. v0.1: n = 9 (INSTRUCTIONS' tenth "discrepant" document, G09, is a must-NOT-flag trap and is scored separately); v0.2: n = 17 on the 15-document set. `NOT_EVALUABLE` checks are excluded from every denominator |
| `false_flag_rate_fields` | non-CLEAN findings on fields not planted / clean comparison fields. Denominator = 12 docs × 19 keys − planted(9) − trap(1) = 218 |
| `false_flag_docs` | count of G11, G12 not in document lane AUTO_CLEAR (0/2 is the target) |
| `trap_resolved` | G09 `coupon_rate_pct` is CLEAN (1/1) |
| `extraction_accuracy[family]` | fields whose normalized value equals `golden/truth/<doc>.json` / (12 × 19). Absent-in-truth counts as correct only if extractor DECLARED_ABSENT |
| `agreement_rate` | merged fields with `agree=True` / (12 × 19) |
| `auto_clear_correctness` | 1 − (planted fields whose lane is AUTO_CLEAR / planted). Must be 100%; else printed in red with the sentence "tiered autonomy claim does not hold on this run" |
| `cost_per_doc` | Σ trace `cost_usd` / 12, plus min/max |

`eval_report.md` sections: results table (each row with n), per-finding detail (planted vs
reported, hit/miss), false flags listed by doc/field, extraction accuracy per family, cost,
**Honest Ceiling** (fixed text + computed n's: 12 docs, 10 planted, 2 clean, one layout
family per doc, one prompt per extractor, synthetic docs, cannot see unplanted error
classes, "directional, not statistically significant").

## 15. Golden set formats

`golden/manifest.json`:
```json
{"version": 1,
 "history": [{"date": "2026-09-11", "note": "initial labels"}],
 "documents": [
  {"id": "G01", "termsheet": "termsheets/G01.txt", "booking": "bookings/SN-2026-0001.json", "truth": "truth/G01.json", "trade_id": "SN-2026-0001",
   "planted": [{"field": "barrier_level_pct", "type": "MISMATCH", "severity": "critical", "note": "TS 65, booking 70"}]},
  {"id": "G09", "...": "...", "planted": [], "traps": [{"field": "coupon_rate_pct", "expect": "CLEAN", "note": "2.0625% per quarter vs 8.25 p.a."}]},
  {"id": "G11", "...": "...", "planted": [], "clean_control": true}
 ]}
```
Planted map (from INSTRUCTIONS): G01 barrier_level_pct MISMATCH · G02
autocall_observation_dates MISMATCH · G03 day_count MISMATCH · G04 coupon_memory MISMATCH ·
G05 notional MISMATCH · G06 currency MISMATCH · G07 autocall_level_pct MISMATCH · G08
underlyings MISMATCH · G09 trap CLEAN · G10 barrier_level_pct TS_ABSENT · G11, G12 clean.

`golden/truth/Gxx.json`: `{field: value | "ABSENT"}` for all 19 comparison keys — the
document's own truth (so for G01 truth says 65, booking says 70).

Term sheets: 600–1200 words each, four layout families rotated (prose-first, table-first,
numbered-clauses, letter-style with annex), boilerplate risk language as distractors, terms
sometimes stated twice (prose and table) consistently.

## 16. Run directory

```
runs/<YYYYMMDD-HHMMSS>/
  trace.jsonl
  <doc_id>/ extraction_gemini.json extraction_claude.json merged.json booking.json findings.json auto_clear.json triage.json run_report.html
  eval_report.md          (eval runs only)
  summary.json
```
`runs/showcase/` is a hand-picked, committed run for the interview.

## 17. Tests (`make test`, no network)

- `test_normalize.py`: every rule in §4 incl. G09 arithmetic, list-vs-scalar non-collapse,
  date formats, `Decimal` equality.
- `test_merger.py`: the §5 truth table.
- `test_comparator.py`: the §6 table; booking NOT_FOUND.
- `test_lanes.py`: per-field and document lanes.
- `test_schema_guard.py`: missing field, bad pairing, span not found, whitespace-collapsed
  match, offsets recomputed.
- `test_fixtures_reproduce_manifest.py` (S1 checkpoint): hand-written extractions in
  `tests/fixtures/` run through normalize→merge→compare and reproduce every manifest finding
  exactly, with zero extra findings.
- `test_scoring.py`: metric arithmetic on a synthetic result.


## 18. v0.2 module contracts (added 2026-09-12)

- `ingest/parser.py`: `Parser.parse(pdf) -> ParseResult(markdown, meta)`; `MixedbreadParser`
  (files.create → parsing.jobs.create(markdown, high_quality, page) → poll; `timeout=60,
  max_retries=2`), `LocalParser` (pdftotext -layout). `parse_document(doc_id, pdf, parser,
  cache_dir) -> (result, cached)` keyed by pdf sha256 + vendor; artifacts `golden/parsed/<id>.md`
  + `.meta.json`. Trace step `parse` with outcome OK | CACHED | PARSE_ERROR (falls back to .txt).
- `schema_loader`: `Schema.product_type / non_compared / relations / relation_keys`;
  `load_products()`, `schema_for(pt)`, `all_schemas()`, `detect_product(text) -> (pt, how)`.
  `schema/termsheet_v2.json` (27 fields, 26 compared), `option_v1.json` (28/28),
  `index_methodology_v1.json` (14; `binding`, `claim`, `return_type_map`).
- `comparator.check_relations(doc_id, merged, booking, schema)`: one finding per relation, key
  `rel:<name>`, CLEAN with "not evaluable (…)" when inputs are missing.
- `reference/lane.py`: `load_reference(ctx) -> ReferenceRules | None` (parse + dual extraction,
  cached by (markdown sha, prompt sha, model) in `golden/reference/extraction_<family>.json`);
  `check_reference(doc_id, merged, rules, schema) -> [Finding]` with keys `ref:<claim>`;
  `rules_from_values()` for tests. Only documents with an Underlying Index section produce
  reference findings.
- `extract/schema_guard.locate`: exact → whitespace-insensitive → tag/pipe/entity-stripped view
  with an offset map back to the artifact; spans are cleaned of pasted tags, "\\n" escapes and
  entities before matching.
- `pipeline.run_document(doc_path, ctx, trade_id, pdf_path, product_type)`: steps
  `parse? → load → detect_product → extract×2 → merge → booking_lookup → compare (+relations,
  +reference_check) → triage → persist`; `summary.json` carries `source`, `parse`,
  `product_type`, `attested_hashes` (document sha, canonical booking sha).
- `report/desk_view.py`: `trust_state(findings)`, `consequence(finding)`, `render(run_dir)`;
  STALE when `attested_hashes` no longer match the current parsed text / booking store.
- `cli`: `eval --source pdf|txt --parser --no-reference`, `parse`, `ablation`, `check <doc>
  --trade --product --all --no-triage`, `report`, `demo`. Make: `golden parse eval eval-txt
  ablation check eval-diff brief showcase`.
- `eval/scoring`: per-document schema keys; `rel:*`/`ref:*` in the false-flag denominator when
  present; `field_accuracy`, `by_product`, `reference_lane` in `summary.json`; report v2 order.
- `eval/ablation.render_parse_tax(txt_run, pdf_run)` → `parse_tax.md` appended to the pdf run's
  report. `scripts/eval_diff.py`, `scripts/fill_brief.py`, `scripts/fill_model_risk.py`.
