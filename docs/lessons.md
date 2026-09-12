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
- Lesson: on n=12 one miss is the difference between 100% and 89%. The honest move is to ship the setting that caught everything, print the cheaper setting's numbers next to it, and say the sample is too small to know whether the miss is stable.
- Fix / rework: ADR-19; the brief carries the trade-off sentence; the env knob makes the sweep reproducible in one command.
- Post angle: "My cheapest config was 9× faster. I didn't ship it, and the reason is a table, not a feeling."

## 2026-09-12 — Every network call that lacks a hard timeout will eventually prove it
- Situation: pre-parsing the 12 golden PDFs with Mixedbread before the CS2 ablation.
- What broke / what we assumed: eleven parses took 2–13 seconds; G10's took 3.6 hours. The SDK's `poll_timeout_ms` bounds the polling loop, not a single stalled HTTP request. Same failure class as the Gemini hang the day before, on a different vendor.
- Lesson: the bound has to sit at the transport layer (per-request timeout + bounded retries), not at the application loop above it. Vendors differ in everything except this.
- Fix / rework: `Mixedbread(timeout=60, max_retries=2)`; the parse step is traced with its own latency so a stall is visible in the run, not just in wall-clock.
- Post angle: "Three vendors, one bug: the missing timeout. It is never the model that hangs; it is the socket."
