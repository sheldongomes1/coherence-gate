{# triage_v1 — one call per TRIAGE finding. The finding type and lane are already decided by code;
   the model classifies (advisory) and drafts the desk query. It never sees the full document (ADR-17). #}
A deterministic coherence check between a structured-note term sheet and its booking record has produced the finding below. The match/no-match decision is final and is not yours to revisit. Your job is to write the query a documentation analyst would send to the desk so it can be resolved in one reply.

Finding
- Document: {{ doc_id }}
- Field: {{ field }} ({{ field_description }})
- Finding type: {{ finding_type }} — {{ finding_type_meaning }}
- Severity: {{ severity }}
- Term sheet value (as extracted): {{ ts_value }}
- Booking value (field "{{ field }}" in the booking record): {{ booking_value }}
- Comparator detail: {{ detail }}

Term sheet evidence (verbatim spans the extractors cited)
{% for c in citations %}- "{{ c }}"
{% endfor %}{% if not citations %}- (none: the term sheet does not state this field){% endif %}

Write:
1. classification — one of BOOKING_LIKELY_WRONG, DOCUMENT_LIKELY_WRONG, GENUINE_AMBIGUITY, EXTRACTION_QUALITY. Use EXTRACTION_QUALITY when the finding type is EXTRACTOR_DISAGREEMENT or MALFORMED_EXTRACTION and the evidence suggests the extractors, not the documents, are the problem.
2. desk_query — 2 to 4 sentences addressed to the desk. Quote the clause verbatim, name the booking field and its value, state what needs confirming. No pleasantries.
3. cited_clause — the single verbatim span you relied on (or "" if the term sheet is silent).
4. booking_field / booking_value — as given above.
5. rationale — one sentence on why you chose the classification.
