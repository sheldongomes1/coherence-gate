{# reference_v1 — extraction of an index METHODOLOGY (rulebook), not a trade. Same contract: cite verbatim or
   declare absent. The distinction that matters: a value the methodology FIXES vs a term it merely DEFINES. #}
You are extracting the rules and defaults stated in an index methodology document into a fixed schema. A downstream deterministic check will compare term-sheet claims about an index against these rules. You do not judge any term sheet.

Rules

1. Output exactly one JSON object with two maps, "value" and "citation", each keyed by every schema field listed below, plus an "absent" list naming every field the methodology does not fix. Every field must appear in both maps.
2. EXTRACTED (not in "absent"): the value AS WRITTEN in the methodology, with a citation copied VERBATIM from the document. DECLARED_ABSENT (listed in "absent"): value and citation are empty strings.
3. Distinguish carefully:
   - A RULE the methodology fixes unconditionally (e.g. "The Index Value shall be floored at zero", "Rebalance Date: Every Index Business Day", "Type I ... The Index Value is Excess Return") is EXTRACTED.
   - A DEFAULT stated as "unless explicitly stated otherwise in the index specific document, X is Y" is EXTRACTED with value Y (the schema field name says it is a default).
   - A term the methodology only DEFINES without fixing a value (e.g. "Volatility Target: the percentage target of volatility of an Index") is DECLARED_ABSENT. Never invent a number.
4. Do not extract formulas, examples, or backtest assumptions as values.

Schema (field | type | meaning)

{{ schema_table }}

Document

<document>
{{ document }}
</document>
