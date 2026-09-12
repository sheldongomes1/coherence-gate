# memories.md — tutor learning log for this project (per-project)

Format: `{date} | phase/topic | built | interview score | weak areas`

2026-09-11 | design sign-off | docs (DESIGN/HLD/LLD/ADR-1..12), schema v1, scaffold | not yet interviewed | —
2026-09-11 | S0 eval-first | golden set (generated), types, trace, merger/comparator/lanes, harness, scoring, CLI; stub eval 0/9 | not yet interviewed | —
2026-09-11 | S1 deterministic core | normalize.py (27 tests), MCP server+client (2.x SDK), fixtures reproduce manifest 9/9 + trap + 2 clean | not yet interviewed | —
2026-09-11 | S2 extraction + S3 triage + S4 report (wip) | prompt v1, Gemini+Claude extractors, three-map schema (ADR-16), guard, triage agent (ADR-17), HTML report, cg demo; first run aborted on hang, timeouts added | not yet interviewed | —
2026-09-11 | S3 checkpoint | G01 triage note: BOOKING_LIKELY_WRONG, quotes "at a Knock-in Level of 65% of the Initial Level", names barrier_level_pct=70, asks for amendment or supporting doc; $0.0126, 6.3s | not yet interviewed | —
2026-09-11 | S4 + effort sweep | eval iterations 1-4 logged; 9/9 at medium (iter 3); Gemini low sweep 8/9 at -37% cost (iter 4, ADR-19 keeps medium); demo alone: G11+G09 auto-clear, G10 TS_ABSENT with desk query; BRIEF generated from run; showcase-demo frozen | not yet interviewed | candidate weak areas to drill: why 9 planted + 1 trap (not 10); why no LLM arbiter; grammar-size constraint on structured outputs; why thinking tokens count as output
2026-09-11 | v0.1.0 shipped | iteration 5 all green (9/9, 0/218, 228/228, $0.113/doc); showcase frozen; brief generated | not yet interviewed | drill list unchanged; add: "why did the cheapest config lose", "what does 1,489 s on one call tell you about the transport"
2026-09-12 | v0.2 CS1 PDF golden set | note.html.j2 (4 variants from approved template), WeasyPrint PDFs, canonical TXT, G12 = approved economics, Versa docs carry Underlying Index section; 55 tests pass | not yet interviewed | —
