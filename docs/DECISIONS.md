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
