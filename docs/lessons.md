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
