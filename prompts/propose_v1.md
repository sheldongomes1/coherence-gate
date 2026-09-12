{# propose_v1 — CS8c. Turns desk feedback into REVIEWABLE proposals. Containment: the model sees only the
   finding, its citations, the booking value and the desk note. It never applies anything. #}
You are drafting a proposal for the maintainers of a document-coherence gate. The desk has reviewed one automated finding and recorded a verdict. Your proposal will be read by a human and, if accepted, applied in its own commit and re-measured by the evaluation suite. Nothing you write is applied automatically. The model that produced the finding never learns from this; only versioned artifacts (golden set, tolerance table, prompts, consequence templates) can change, and only after the eval confirms the effect.

Feedback entry
- Finding: {{ finding_id }} (document {{ doc_id }}, field {{ field }}, type {{ finding_type }}, severity {{ severity }})
- Term sheet value: {{ ts_value }}
- Booking value: {{ booking_value }}
- Comparator detail: {{ detail }}
- Desk verdict: {{ verdict }}
- Desk note: {{ note }}
- Citations: {% for c in citations %}"{{ c }}" {% endfor %}

Choose ONE proposal kind:
- golden_candidate: the desk's verdict reveals a case class the golden set does not contain (typically a false flag the eval could not see). Propose the document snippet / booking pair to add and the label it would carry, and name the metric it would exercise.
- judgment_change: the verdict implies a change to a versioned judgment artifact (a normalization rule, a tolerance, a prompt instruction, a consequence template). State the exact change and a predicted effect on catch rate and false-flag rate.
- error_register: the verdict is a repeat complaint with no defensible change yet. Record the pattern and what evidence would justify a change.

Write: kind, title (≤ 80 chars), body (markdown, ≤ 250 words, concrete), predicted_effect (one sentence naming the metrics that should and should not move), rationale (one sentence citing the desk note).
