# V2-CHANGES.md — Concord v0.2 build plan

Read alongside GOAL.md, INSTRUCTIONS.md, SKILL.md (all still in force — SKILL.md
rules govern every change below). v0.1.0 is tagged and is the fallback: if any
change set below fails, ship v0.1.0 plus whatever change sets completed.

Execute the CHANGE SETS in the order listed. Each has a checkpoint and a
fallback. Do not start a change set until the previous one's checkpoint passes.

The product story v2 tells (keep this in view while building):
1. Desk view first — a trader's 6am page: what's trusted, what isn't, why it
   matters to their hedge.
2. Behind it, one agent with tools: Mixedbread parsing, dual-family extraction,
   MCP booking lookup, deterministic comparison, Versa reference check, triage.
3. Under it all, the eval: golden set, planted mutants, catch rate AND
   false-flag rate, parse-tax ablation, honest ceiling.

────────────────────────────────────────────────────────────────────
CHANGE SET 1 — PDF golden set (regenerate all documents as PDFs)
────────────────────────────────────────────────────────────────────
WHAT
- All golden documents become PDFs, rendered from HTML via WeasyPrint, using
  the two hand-approved templates in the repo root as the house style:
  * G12_bversa10.html            (note template — Northbridge letterhead,
                                  numbered clauses, terms tables, Underlying
                                  Index section, risk factors, footer)
  * OP_2026_0114_bversa10_call.html (OTC option template — ISDA-style,
                                  option-terms table, settlement formula)
- Extend scripts/gen_golden.py: keep the parameter table as the single source
  of truth; each row renders through ONE of the four layout variants, all
  derived from the approved templates (vary: clause order, table vs prose for
  terms, header styling) so extraction is not table-lookup. Same row still
  emits truth JSON + booking JSON.
- Keep emitting the .txt version of every document alongside the PDF. The
  .txt is ground truth for the ablation (Change Set 2) and the fallback path.
- BVERSA10-linked documents (the Versa subset) MUST carry the full
  "Underlying Index" section exactly as in the approved templates: ticker,
  administrator (BISL/FCA line), Return Treatment (Type I / Excess Return
  language), Volatility Target, EWMA + Volatility Value Selection, exposure
  bounds, Determination Lag, daily rebalancing, Deduction Factor, Transaction
  Cost Rate, Index Currency, zero-floor sentence.
- Every document keeps the synthetic-specimen footer line (fictitious
  entities, systems demonstration). Never a real bank's name.
CHECKPOINT
- `make golden` regenerates: N PDFs + N TXTs + truth + bookings + manifest in
  one command; PDFs open and paginate correctly; spot-check 3 visually.
FALLBACK
- If a layout variant misrenders, ship fewer variants, not fewer documents.

────────────────────────────────────────────────────────────────────
CHANGE SET 2 — Mixedbread ingestion + citation chain + parse-tax ablation
────────────────────────────────────────────────────────────────────
WHAT
- New ingestion stage: PDF → Mixedbread Parsing API → markdown.
  * Use the official skill if helpful: `npx skills add mixedbread-ai/skills`
    (mixedbread-parsing). API: POST /v1/parsing/jobs (async job: upload file,
    create job with return_format="markdown", mode="high_quality", poll to
    completion). Env var MXBAI_API_KEY.
  * Save the parsed output as a versioned artifact: parsed/<doc_id>.md, plus
    parsed/<doc_id>.meta.json (job id, mode, latency_ms, cost if reported,
    parser version/date).
- CITATION CHAIN (non-negotiable): the parsed markdown becomes the canonical
  source text. All extraction citations (text_span, char_range) anchor into
  parsed/<doc_id>.md, NOT the original .txt. The run report states, per
  document: "citations reference parsed text, parse job <id>". The PDF is
  upstream evidence; the parsed artifact is what the gate read.
- Pipeline flag: `--source pdf|txt` (default pdf). txt path bypasses parsing
  and cites into the .txt. This is both the Sunday-night fallback and the
  ablation lever.
- Trace the parse like a model call: one trace.jsonl line per parse (step=
  "parse", vendor="mixedbread", job id, latency, cost). Parsing joins the
  "$X to check the book" total.
- ABLATION (eval addition): run the full eval twice, --source txt and
  --source pdf, same models, same prompts. New eval_report section
  "Parse tax": per-extractor extraction accuracy txt vs pdf, fields degraded
  (list them), catch/false-flag deltas. One honest paragraph interpreting it.
- Swappability note for BRIEF: the gate consumes parsed markdown; the parsing
  vendor is a replaceable layer behind one interface (parse(pdf) -> markdown
  + meta). Enforce that interface in code (one module, no mxbai imports
  elsewhere).
CHECKPOINT
- One document round-trips: PDF -> parsed markdown -> extraction with valid
  citations into the parsed text -> comparator findings unchanged in type.
- Full eval runs on --source pdf; ablation table renders.
TIME-BOX / FALLBACK
- If Mixedbread integration exceeds ~3 hours or the API misbehaves: implement
  the same interface with a local extractor (pdfplumber/pdftotext -layout) as
  "parser: local-fallback", note it in the report, keep the ablation (txt vs
  locally-parsed pdf still measures a parse tax). Do NOT let parsing block
  the eval.

────────────────────────────────────────────────────────────────────
CHANGE SET 3 — Option product type (schema v2 with product discriminator)
────────────────────────────────────────────────────────────────────
WHAT
- schema v2: add top-level `product_type: note | otc_option` discriminator.
  * note: existing fields unchanged.
  * otc_option fields: buyer, seller, option_style (european), option_type
    (call/put), notional, currency, trade_date, effective_date,
    strike_level_pct, participation_rate_pct, valuation_date,
    expiration_date, automatic_exercise (bool), premium_pct, premium_amount,
    premium_payment_date, cash_settlement_days, settlement_currency,
    calculation_agent. Underlying Index sub-schema shared with note.
- Add the approved option document as golden case G13 (render from the
  option template) with its booking. Plant TWO new mutants:
  * G13a participation: documented 100%, booked 95% (critical — the classic
    FIA under-hedge).
  * G13b premium arithmetic: premium_pct 4.15% and premium_amount
    USD 1,037,500 documented; booking carries premium_amount computed off the
    wrong notional. NEW COMPARATOR RELATION: cross-field arithmetic check —
    premium_pct × notional must equal premium_amount within cents. This is a
    deterministic rule in the comparator, documented in the tolerance table.
  (Two option documents: one clean + one carrying a planted issue, or one
  document run against two bookings — implementer's choice; manifest decides.)
- Extraction prompts: one shared instruction set, schema-driven per
  product_type. Do not fork the pipeline; the gate is product-agnostic,
  schemas are pluggable — that IS the brief sentence.
CHECKPOINT
- Eval covers both product types; option mutants caught; the arithmetic
  relation fires on G13b and stays silent on clean docs.
FALLBACK
- If time is short: ONE option document, ONE mutant (participation). The
  arithmetic relation is the first thing to cut, named in DESIGN.md phase 2.

────────────────────────────────────────────────────────────────────
CHANGE SET 4 — Versa reference-document lane (as scoped in the accepted
checkpoint option 1)
────────────────────────────────────────────────────────────────────
WHAT (recap of the accepted scope — build exactly this, no more)
- Third document class: the real Bloomberg Versa Indices Methodology PDF,
  ingested through the SAME Mixedbread stage, extracted dual-family into a
  small index schema: return treatment types, default Determination Lag,
  default Exposure Direction, rebalance cadence, deduction/transaction-cost
  defaults ("unless index-specific document states otherwise" semantics —
  represent defaults as defaults), administrator, zero-floor rule.
- Versa-linked term sheets carry the Underlying Index section (Change Set 1
  guarantees this). Bookings gain underlying static data (return_type,
  vol_target_pct, deduction_factor_pct, rebalance_frequency, administrator).
- Comparator gains one relation: claim-in-term-sheet vs rule-in-methodology
  (e.g., a Type I index described as "total return" = finding
  REFERENCE_INCONSISTENT, critical; a parameter the methodology defers to the
  index-specific document is NOT checkable against the methodology — that
  distinction must be explicit in code and report).
- Three planted incoherences (from the accepted plan): Type I called total
  return; vol target mismatch TS vs booking static; rebalance frequency
  contradicting the rulebook.
CHECKPOINT
- The three reference mutants are caught; a clean Versa document produces no
  reference findings; the "defers to index-specific document" case produces
  no false flag.
FALLBACK
- v0.1.0 + Change Sets 1–3 still ship; reference lane becomes the demo's
  spoken roadmap instead of shown feature.

────────────────────────────────────────────────────────────────────
CHANGE SET 5 — Desk view (desk_view.html, the new front door)
────────────────────────────────────────────────────────────────────
WHAT
- New static page desk_view.html generated per run, same CSS variables as
  run_report.html (one product, two pages). NO JS framework, no charts, no
  server.
- Header: book name, run timestamp, one line: "N positions · X attested ·
  Y require attention · $C to check the book" (C = models + parsing).
- One row per trade, SORTED red -> amber -> green:
  * columns: reference, product type, underlying, notional, maturity/expiry,
    indicative risk figures FROM FIXTURE DATA clearly labeled "indicative"
    (do NOT compute greeks; do NOT claim magnitudes of greek error),
    and the TRUST column.
  * trust states (exactly three):
    - ATTESTED (green): "booking attested against term sheet — <n> fields,
      both families agree" (+ "· reference-checked vs index methodology"
      when the Versa lane ran).
    - DISAGREEMENT (amber): extractor conflict or malformed extraction —
      "reading uncertain — human review queued".
    - MISMATCH (red): one line of DESK CONSEQUENCE, direction not magnitude:
      e.g. "barrier booked 70 vs 65 documented — knock-in risk computed off
      the wrong level"; "participation booked 95 vs 100 documented — client
      payout under-hedged"; "memory booked off vs on documented — coupon
      liability understated". Consequence phrasing lives in a small
      finding-type -> consequence-template table, deterministic.
  * every non-green row links to run_report.html#<doc_id> (anchors exist).
- Behind-the-scenes panel (collapsed <details> at the bottom): the agent's
  tool inventory for this run — parse (Mixedbread), extract (two families),
  booking lookup (MCP), compare (deterministic), reference check (Versa),
  triage — each with call counts from the trace. Truthful, no inflation.
CHECKPOINT
- Demo arc clicks end-to-end: desk_view -> red row -> run_report anchor
  (finding + citations + drafted desk query) -> eval_report. Three clicks.
FALLBACK
- If styling drags, plain table with the three states and links is enough;
  polish is the first casualty, the trust column is not.

────────────────────────────────────────────────────────────────────
CHANGE SET 6 — Eval report v2 + BRIEF v2 alignment
────────────────────────────────────────────────────────────────────
WHAT
- eval_report.md gains/keeps, in this order: headline strict catch rate
  (field+type) with field-level diagnostic row beneath; false-flag rate at
  equal prominence; auto_clear_correctness (must be 100%, red if not);
  cross-family agreement; PARSE TAX ablation section; per-product-type
  breakdown (note vs option); reference-lane results; effort-level sweep
  results (from the accepted medium-first sweep) with cost/latency deltas;
  cost per document and per book; Honest Ceiling updated for v2: n, synthetic
  documents, four layout families, machine-uniform phrasing, "the eval cannot
  see error classes it does not plant", triage agent cannot use unflagged
  clauses elsewhere in the document, parse vendor single-sourced.
- eval_log.md continues: one line per iteration, one variable per iteration.
- BRIEF.md updates (keep it one page): product sentence unchanged; add one
  sentence each for: two product types / pluggable schemas; ingestion is
  measured (parse tax); reference lane checks Versa claims against the
  governing methodology; desk view as the front door; swappable parser.
  Roadmap line becomes: reconciliation break triage, P&L drift triage
  (clause-cited residual explanation off official published levels — never a
  re-implementation), hedge-to-liability coherence (option terms vs annuity
  crediting parameters).
CHECKPOINT
- A reader can go desk_view -> run_report -> eval_report and never meet an
  unexplained number. Every rate has an n. Nothing green that shouldn't be.

────────────────────────────────────────────────────────────────────
PRIORITY ORDER IF TIME COLLAPSES
────────────────────────────────────────────────────────────────────
1 (must): Change Sets 1+2 through the eval with ablation  — the measured-
   ingestion story.
2 (must): Change Set 6 eval report v2 — the report IS the product.
3 (strong): Change Set 5 desk view — the front-office frame.
4 (strong): Change Set 4 reference lane — the RBC-specific wow.
5 (nice): Change Set 3 full option support — degrade to one doc/one mutant.
Anything cut is named in DESIGN.md and the BRIEF roadmap — cut scope, never
cut honesty.

────────────────────────────────────────────────────────────────────
DEMO SCRIPT (write into README as the 5-minute walkthrough)
────────────────────────────────────────────────────────────────────
1. Open the OTC option PDF (OP-2026-0114): "this is the shape of the real
   trade — an insurer hedging FIA crediting on Versa 10."
2. desk_view.html: the 6am page — attested book, three attention rows,
   cost line.
3. Click the participation-mismatch row -> run_report anchor: finding, both
   families' citations into the parsed text, drafted desk query.
4. The refused-ambiguity moment: the date the gate would not guess.
5. eval_report.md: strict catch rate, false flags, parse tax, effort sweep,
   honest ceiling — end on the ceiling, not the wins.

────────────────────────────────────────────────────────────────────
CHANGE SET 7 — Elevations: live check, model-swap diff, STALE state
────────────────────────────────────────────────────────────────────
Build these AFTER Change Sets 1–6 pass their checkpoints (exception: 7a can
land any time after CS2, it is a thin wrapper). These are the interview
elevations — small code, large argument. Same SKILL.md rules.

7a. LIVE CHECK — `cg check <termsheet.pdf> --trade <trade_id>`
- One CLI verb that runs the full pipeline on a single document against its
  booking (via the MCP tool) and prints a compact verdict to stdout:
  per-field lanes, findings with one-line consequences, citations (span +
  parse job id), drafted desk query for any MISMATCH, and a cost/latency
  footer ("parsed + extracted x2 + compared + referenced in 31s, $0.11").
- Also writes the standard run artifacts (trace, report fragment) so the
  live run is auditable like any other.
- MUST be robust to an arbitrarily edited booking JSON: any field the
  demo audience changes (participation 100 -> 95, memory true -> false,
  knock-in 60 -> 65, premium off the wrong notional) is caught by the
  existing comparator/arithmetic relations. No special-casing — if the
  generic pipeline doesn't catch an edit class, that is a finding for the
  honest ceiling, not something to patch cosmetically for the demo.
- README demo script gains step 3b: "now you change the booking — any field
  — and we run it again." Rehearse with at least 5 different edits.
CHECKPOINT: cold run on the option doc completes < ~60s; 5/5 rehearsed edit
classes caught with correct type; cost footer accurate vs trace.
FALLBACK: if latency is ugly on high effort, run live mode at the swept
medium setting and SAY SO in the footer ("effort: medium — see eval sweep").

7b. MODEL-SWAP DIFF — `make eval-diff`
- Config already pins model versions. Add scripts/eval_diff.py: takes two
  eval output JSONs (baseline run + rerun after changing ONE pinned model in
  config) and renders eval_diff.md: side-by-side strict catch rate,
  field-level catch, false-flag rate, cross-family agreement, auto-clear
  correctness, cost/doc, latency/doc, and a per-field table of changed
  outcomes (which fields' extractions or lanes moved).
- Produce ONE real diff for the package: swap the Gemini extractor to an
  adjacent available version (or effort level if no second version is
  accessible — say which in the report), rerun, commit eval_diff.md.
- One sentence at the top of eval_diff.md, verbatim: "A model deprecation is
  this diff: rerun, compare, accept or hold. The judgment (schema, prompts,
  tolerances, golden set) is versioned and did not change."
CHECKPOINT: eval_diff.md renders from two real runs; every number traceable
to its run id.
FALLBACK: if no second model/effort variant is reachable, generate the diff
between the medium and high effort-sweep runs already required by CS6 —
the mechanism is identical; label it honestly.

7c. STALE STATE — attestation freshness on the desk view
- At attestation time, store content hashes: sha256 of parsed/<doc>.md and
  sha256 of the canonical booking JSON, inside the run's attestation record.
- desk_view generation recomputes both hashes against current files. If
  either differs from the attested hashes, the row renders in a FOURTH state:
  STALE (grey/amber): "attestation invalidated — booking amended since last
  check; re-check queued" (or "document changed" — say which hash moved).
  STALE rows sort between red and amber.
- Demo beat: after the live-check catch is fixed in the booking, the desk
  view now shows that row STALE (the old attestation no longer applies) ->
  run `cg check` again -> row returns to ATTESTED. That loop — trust is
  earned continuously, not granted once — is the closing argument of the
  desk-view demo.
- No watchers, no daemons: hash comparison at page-generation time only.
CHECKPOINT: amend a booking field on an ATTESTED trade -> regenerate
desk_view -> row is STALE with the correct reason; re-run check -> ATTESTED.
FALLBACK: none needed; this is ~30 lines. If it somehow fights the clock,
it degrades to a described roadmap line.

BRIEF v2 additions from this change set (one sentence each):
- booking-time gate, not overnight batch: the check runs when the trade is
  born or amended, when catching it is cheapest;
- the marginal-cost line in his units: ~$0.11/document, ~$1.36/book — the
  document-coherence layer's marginal cost per additional strategy is
  effectively flat;
- deprecation is a diff, not a quarter (point to eval_diff.md);
- attestation expires with amendment (STALE) — silence is earned
  continuously.
