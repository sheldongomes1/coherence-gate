# lessons.md — surprises, reversals, and reworks during the build (write-up fuel)

## 2026-09-11 — The normalizer trap forced a schema change before any code existed
- Situation: designing how G09 ("2.0625% per quarter (8.25% p.a.)") could resolve as a match without arithmetic in a prompt.
- What broke / what we assumed: the INSTRUCTIONS schema had `coupon_rate_pct` only; an extractor would have to choose which number to return, which is prompt-side decision-making.
- Lesson: if a model has to do arithmetic to fill a field, the schema is missing a fact. Capture the fact (rate basis) and let code compute.
- Fix / rework: added `coupon_rate_basis` to schema v1 (ADR-1) before freezing it.
- Post angle: "The first bug I fixed in my extraction pipeline was in the schema, and I fixed it before writing a line of code."

## 2026-09-11 — The MCP SDK I remembered no longer exists
- Situation: writing the booking_lookup MCP server for S1 against `FastMCP`.
- What broke / what we assumed: the installed `mcp` is 2.x; `FastMCP` was renamed `MCPServer`, the import path moved, and a new high-level `mcp.Client` accepts `StdioServerParameters` directly. Code from memory would have failed on import.
- Lesson: inspect the installed package before writing against it. Ten lines of `inspect.signature` saved an hour of guesswork; the server + client took under 30 minutes of the 2-hour timebox.
- Fix / rework: server on `mcp.server.mcpserver.MCPServer`, client on `mcp.Client` held on a background event loop so the sync pipeline can call it.
- Post angle: "The fastest way to write against a fast-moving SDK is to ask the SDK, not your memory."

## 2026-09-11 — "7.5% per annum" is a number, and the normalizer must know it
- Situation: S1 fixture test, gemini-style values written the way a model would copy them.
- What broke / what we assumed: `norm_decimal` rejected "7.5% per annum"; the merger then flagged a disagreement on every coupon.
- Lesson: the boundary between "value as written" and "canonical value" is where prompts leak decision logic. If the prompt has to say "strip the words per annum", the rule is in the wrong place.
- Fix / rework: the decimal normalizer strips period words (per annum, p.a., per quarter, of the Initial Level); a trailing clause like ", payable semi-annually" still fails, by design.
- Post angle: "Every rule I was tempted to put in the prompt became a unit test instead."

## 2026-09-11 — "Structured output" has a grammar budget, and 20 nested objects blew it
- Situation: first real Claude extraction call in S2.
- What broke / what we assumed: HTTP 400 twice. First "too many union-typed parameters (60, limit 16)", then, with unions removed, "compiled grammar is too large". The schema was semantically fine; its *shape* (20 per-field objects × 4 properties) was the problem. Gemini accepted every variant.
- Lesson: constrained decoding compiles your JSON schema into a grammar. Nesting and unions multiply grammar size; flat maps keyed by field name carry the same information at a fraction of the cost. Design the output shape for the compiler, not for the reader.
- Fix / rework: three flat maps (status / value / citation), zero unions, same contract for both families (ADR-16). Probed four shapes with a 10-token document before touching the pipeline: 400s are free.
- Post angle: "My extraction schema was rejected by a grammar compiler. The fix was a data-shape decision, not a prompt."

## 2026-09-11 — Gemini's output cap includes its thinking
- Situation: Gemini returned truncated JSON with finish reason MAX_TOKENS at an 8k ceiling.
- What broke / what we assumed: `thoughts_token_count` was 7,678 of the 8,000; the JSON itself needed ~1.5k. The cap counts reasoning. Thinking volume also swung 3k→12k between identical calls.
- Lesson: on Gemini 3.x, `max_output_tokens` is a budget for reasoning plus answer. Set it per family, bill thoughts as output (they are), and let the effort sweep show what the reasoning buys.
- Fix / rework: 32k ceiling for Gemini, 16k for Claude, both in config; trace records thoughts in `output_tokens`.
- Post angle: "The cheapest model call in my pipeline became the most expensive one, because thinking is output."

## 2026-09-11 — A model call with no timeout hung the eval for two hours
- Situation: first full 12-document eval, running in the background.
- What broke / what we assumed: after G05, the Gemini call never returned; the process sat at 0% CPU for two hours with no error. The preceding Claude call for the same document had taken 14 minutes (SDK retries on a flaky connection). Neither client had a request timeout.
- Lesson: in an eval harness, an API call that can hang is worse than one that fails, because "still running" looks like progress. Every model call gets a hard timeout and a traced outcome; the SDK's own retries are bounded and visible in latency.
- Fix / rework: `timeout_s: 240` in config, applied to both clients (google-genai in ms, anthropic in s with max_retries=2). The partial run is logged in eval_log.md as aborted, not hidden.
- Post angle: "My eval didn't fail. It just never finished. That is the failure mode to design against."

## 2026-09-11 — The demo's clean document went to triage, and that was the right answer
- Situation: first `make demo` while a 12-document eval was running on the same API keys.
- What broke / what we assumed: Gemini hit the new 240 s timeout on G11. Every field became MALFORMED, the document went to TRIAGE, and the triage agent wrote 19 polite desk queries about a read timeout.
- Lesson: the gate did exactly what it promised (no crash, no invented values, no auto-clear on missing evidence). The waste was asking a model to explain a technical failure 19 times. Code knows the cause; code should write the note.
- Fix / rework: ADR-18 short-circuit; never run demo and eval concurrently on one key (README note).
- Post angle: "When my clean control failed to auto-clear, the system was right and my demo plan was wrong."

## 2026-09-11 — The sweep that decided the default was two runs and a table, not an opinion
- Situation: choosing Gemini's thinking level for the shipped default (ADR-15 → ADR-19).
- What broke / what we assumed: I assumed extraction is "just copying" and low thinking would be free. Low was 9× faster and 37% cheaper, and it mis-mapped one field on the only stepping schedule in the set (8/9).
- Lesson: on n=12 one miss is the difference between 100% and 88.9%. The honest move is to ship the setting that caught everything, print the cheaper setting's numbers next to it, and say the sample is too small to know whether the miss is stable.
- Fix / rework: ADR-19; the brief carries the trade-off sentence; the env knob makes the sweep reproducible in one command.
- Post angle: "My cheapest config was 9× faster. I didn't ship it, and the reason is a table, not a feeling."

## 2026-09-12 — Every network call that lacks a hard timeout will eventually prove it
- Situation: pre-parsing the 12 golden PDFs with Mixedbread before the CS2 ablation.
- What broke / what we assumed: eleven parses took 2–13 seconds; G10's took 3.6 hours. The SDK's `poll_timeout_ms` bounds the polling loop, not a single stalled HTTP request. Same failure class as the Gemini hang the day before, on a different vendor.
- Lesson: the bound has to sit at the transport layer (per-request timeout + bounded retries), not at the application loop above it. Vendors differ in everything except this.
- Fix / rework: `Mixedbread(timeout=60, max_retries=2)`; the parse step is traced with its own latency so a stall is visible in the run, not just in wall-clock.
- Post angle: "Three vendors, one bug: the missing timeout. It is never the model that hangs; it is the socket."

## 2026-09-12 — The parse tax was a citation-anchoring tax, and one page break
- Situation: first pdf-source eval (CS2 ablation). Strict catch fell 9/9 → 6/9 and false flags rose 0 → 71/218, yet field-level catch stayed 9/9.
- What broke / what we assumed: both families read the parsed tables correctly and cited them the way a human would ("Trade Date | 2026-05-12"); the parsed markdown holds `<td>Trade Date</td><td>2026-05-12</td>`. The guard's verbatim matcher refused every table citation, so whole documents became MALFORMED. Gemini sometimes pasted the raw tags with a literal "\n"; the parser writes `&amp;` where the model writes `&`.
- Lesson: "verbatim" must be defined against a view of the artifact, not its bytes: tags and pipes are layout, entities are encoding, neither is evidence. Offsets still map back to the artifact on disk. Re-guarding the stored outputs recovered 86 of 87 failures with zero model calls; the eval, not a prompt, found the bug.
- Fix / rework: tag/pipe/entity-tolerant locator with an offset map (tests). The one residual is a sentence split by a page break around the running footer: a real parse tax, fixed in Phase 2 by dropping header/footer elements at parse time.
- Post angle: "My parse tax was 71 false flags. 70 of them were my own definition of 'verbatim'. The last one was a page footer."

## 2026-09-12 — Two wasted evals: I changed the schema and did not re-run the smoke test
- Situation: added 7 index fields (27/28 per product) for the reference lane and launched the full 15-document chain.
- What broke / what we assumed: I assumed the three-map output shape that compiled at 20 fields would compile at 27. Claude's grammar compiler said no on every document; the pipeline degraded honestly (MALFORMED everywhere, 1/17) and burned two hours of wall clock and a few dollars proving it.
- Lesson: any change to the output contract is a model-facing change and gets the ten-token probe before anything expensive. The fix (two maps + an explicit `absent` list) is arguably a better contract than the one it replaced.
- Fix / rework: ADR-24; the smoke test is now the first line of the release chain, not an optional step.
- Post angle: "The most expensive bug of the weekend was a checklist item I skipped because the last change 'was just fields'."

## 2026-09-12 — The desk's tolerance hid a real edit class within the hour
- Situation: CS8c cycle. The desk rejected the G02 autocall-date finding ("that's the business-day-adjusted date"); the drafted proposal suggested a 1–3 day tolerance; I applied a 3-day tolerance in its own commit to measure it.
- What broke / what we assumed: before the eval even finished, the live rehearsal shifted a booked autocall date by one day on a clean document and the gate said CLEAN. The deterministic fixture test went red on the planted G02 case for the same reason.
- Lesson: a tolerance is a decision to stop looking. The eval is the only thing that can price it, and here the price was a planted miss plus a live miss. The proposal's own predicted effect ("catch rate should not move") was wrong, and the system could show that in a diff instead of an argument.
- Fix / rework: HOLD (revert in its own commit), proposal stays on file with the diff attached. The desk's underlying point (booked dates are adjusted, term-sheet dates are not) becomes a golden candidate: a document pair where the adjustment is *stated*, so the comparator can check it instead of tolerating it.
- Post angle: "The desk asked for a tolerance. The eval showed what it would cost. We kept the finding."

## 2026-09-13 — Billing is a failure mode, and the eval has to name it
- Situation: Sunday-morning release run for v0.2.1 (the NOT_EVALUABLE disposition changed denominators, so the release needed a fresh run). 14/15 documents in, the Anthropic account ran out of credits.
- What broke / what we assumed: the last two Claude calls returned HTTP 400 "credit balance is too low". Tracer recorded API_ERROR with the message; the guard turned every field of those two documents into MALFORMED; the comparator flagged 53 clean fields and four planted findings lost their type. Nothing crashed, nothing went blank, and the ablation and triage steps queued behind it kept going and produced numbers that looked like a regression in parsing or in Claude.
- Lesson: a control-plane failure (billing, quota, key rotation) looks exactly like a model-quality failure in the headline metrics unless the eval report distinguishes "the model read it wrong" from "the model was never asked". The trace already carries the difference (outcome API_ERROR with the HTTP text); the report's job is to surface it next to the number so nobody debugs a parser for an invoice.
- Fix / rework: run parked under `runs/invalid-…-claude-credits`, logged as INVALID in eval_log.md, rerun after top-up. Follow-up for the report: a per-family "calls that never completed (API_ERROR/deadline)" line beside extraction accuracy, so a wholesale transport or billing event is read as such (the wholesale-failure short-circuit, ADR-18, already prevents the desk queries; the report line is the missing half).
- Post angle: "The most misleading eval number of the weekend was caused by an invoice, and the trace knew it before I did."

## 2026-09-13 — A stall should cost one document, not the run
- Situation: release morning. Three full 15-document runs lost in a row: credits exhausted, then the laptop slept twice mid-call. Each restart re-paid 40 minutes and about $2 for extractions that already existed, attested to the document hash.
- What broke / what we assumed: "one pass, no retries" had been read as "always start from zero". The rule exists so a model answer is never re-rolled inside a scored pass; it says nothing about re-buying answers that were already given and stored.
- Lesson: the recheck path built for the desk (ADR-29: reuse the stored extraction when the document hash is unchanged) is exactly the resume path the eval needed. Reuse is allowed only when the prior trace shows both families' calls completed; a TIMEOUT or a billing 400 is not a reading and is extracted again. The report header says it is a composite and names both sets.
- Fix / rework: `cg eval --resume <run>` (ADR-31), cost of the reused extraction carried into the per-document number; the deadline guard now distinguishes "process was suspended" from a provider stall so the trace is not misread on Monday.
- Post angle: "Three release runs died to an invoice and a sleeping laptop. The fix was not a retry; it was refusing to pay twice for an answer the system had already attested."

## 2026-09-13 — The same run showed two different costs depending on which folder it sat in
- Situation: second independent review, an hour after v0.2.1 was tagged. The reviewer GET the live desk view ($2.74) and opened the committed run report ($2.51) for the same run.
- What broke / what we assumed: the report attributed desk-query cost by comparing each trace line's run id to the *directory name*. In `runs/20260913-113753` the triage lines matched the folder and were silently folded into nothing (the per-document number is extraction-only); in `runs/showcase` and in the service's `state/current` they did not match and were counted as "later". Both pages were "generated, never typed", and both were wrong in different directions. The "nothing inflated" tool panel had the same shape of bug: on a resumed run it counted 16 extraction calls per family when one had reached the provider.
- Lesson: attribute by what a trace line *is* (a reading, a desk query, a methodology extraction, a reused artifact), never by where the run was copied to or which process wrote it. A run's identity is in its trace, not in its path. And the first review had fixed this class once already; it came back in a new place because the invariant lived in a comment, not in a test.
- Fix / rework: per-document `cost_breakdown` persisted; the loader sums readings from summaries and desk queries from every `triage:*` line; call counts split provider vs reused; a `cg rescore` (ADR-32) regenerated the frozen report from artifacts with identical numbers and the $0.23 of desk queries it had been hiding.
- Post angle: "Two honest pages, one run, two totals. The bug was a folder name; the lesson is that provenance belongs in the record, not in the path."

## 2026-09-14 — Three tools that reported success without doing the thing
- Situation: building the observability layer (provenance graph, ADK packaging, BigQuery sink) in one afternoon.
- What broke / what we assumed: three separate "success" messages were false. `bq mk --force --view` printed "successfully created" and left the existing view's definition untouched, so a corrected view kept answering the old way until I diffed the deployed SQL against the source. WeasyPrint rendered the graph's edge labels as invisible because it ignores `paint-order`, so a background-coloured halo stroke painted over the text it was meant to protect. And a guard clause of mine (`if "[project.optional-dependencies]" not in s`) skipped an edit entirely because the section already existed, so a "relock and compare" experiment compared nothing and reported a reassuring "unchanged".
- Lesson: a tool's exit code tells you the command ran, not that the state changed. Verify the artifact, not the message: read back the deployed view, render the SVG in a second renderer, diff the file you think you edited. This is the same discipline as the eval itself — the run says PASS, so check what it actually compared.
- Fix / rework: `CREATE OR REPLACE VIEW` instead of `bq mk --view`; an explicit background rect instead of `paint-order`; and the pyproject experiment redone properly, which then revealed the real finding that adding google-adk downgrades two of the demo image's transitive pins.
- Post angle: "Three green checkmarks this afternoon were lying. The habit that caught all three was reading back the artifact instead of the message."

## 2026-09-14 — The free path was not free, and a `str()` was why
- Situation: an independent test pass on the finished observability work, with an explicit brief to look for wasted compute and money. It POSTed a relaunch of an unchanged book — the path documented as costing nothing because every reading is reused under an unchanged document hash.
- What broke / what we assumed: it cost $0.0169 and 6.26 of 6.75 seconds. The recheck reuses a previously drafted desk query by matching a finding's identity, and that identity was built with `str()` on the compared values. For a stepping autocall schedule the in-memory value is `[Decimal('100'), Decimal('95'), Decimal('90')]` and the persisted value is `["100", "95", "90"]`, so one finding out of seventeen never matched itself across the save-and-reload and was re-drafted on every single recheck. The endpoint is unauthenticated and the spend guard only budgets full re-reads, so nothing capped it.
- Lesson: an identity that crosses a serialisation boundary has to be canonical on both sides, and `str()` of a container is not. The deeper lesson is that "this path makes no model calls" is a claim, and a claim with a price attached deserves a test that counts the calls rather than a comment that asserts it. The same afternoon's other findings were all of the same family: work repeated because nobody counted it (the run report rendered and discarded on every page load, the trace parsed once per document instead of once per page, fifteen unchanged files rewritten per render).
- Fix / rework: canonical JSON with `default=str` for the key, plus a test that round-trips every non-clean finding in the book and a test that asserts a recheck re-drafts nothing. Measured after: zero paid calls, $0.0000, 0.1 s for fifteen documents.
- Post angle: "The path I had documented as free cost two cents every time someone clicked it, and the reason was a `str()` on a list of Decimals."
