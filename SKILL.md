---
name: eval-first-llm-build
description: >
  Discipline for building any LLM-powered feature or agent eval-first. Use this
  skill for ALL work in this repository, and whenever the task involves adding,
  changing, or prompting an LLM component, building an extraction/judging/triage
  pipeline, constructing golden sets, or reporting quality numbers — even if the
  user only says "improve the prompt" or "make it more accurate". If a change
  touches model behavior, this skill applies.
---

# Eval-First LLM Build Discipline

The prime directive: **quality is a number, not a vibe.** No model-facing change
ships without a number that moved, measured against a golden set that existed
before the change.

## Rule 1 — The eval exists before the product

Golden set, manifest of expected outcomes, and a runnable scoring harness come
FIRST. If asked to build pipeline code before the eval exists, build the eval
first anyway and say why. A stub pipeline scoring 0% on day one is the correct
starting state.

## Rule 2 — Binary over averages

Every check is PASS/FAIL against an expected outcome. Never score quality on a
1–5 scale and never average scores — a mean is where failures go to hide.
Aggregate only as counts and rates (caught / planted, flagged / clean).

## Rule 3 — Models judge, code decides

LLMs may extract, classify, and draft text. They may NEVER make the
match/no-match decision, apply tolerances, normalize values, or compute a
score. All of that is deterministic, unit-tested Python. If you find decision
logic drifting into a prompt, stop and move it into code.

## Rule 4 — Absence announces itself

No optional silence. Every expected field is either produced WITH provenance
(citation, source span) or explicitly declared absent — and a declared absence
is a first-class output, not a null. Any code path that can yield a silent
blank is a bug to fix immediately, whatever the task at hand was.

## Rule 5 — Two families, no arbitration

Where independent extraction/judging is the mechanic, use two different model
families. Disagreement between them is automatically a finding; never add an
LLM arbiter to break the tie. The disagreement IS the signal.

## Rule 6 — Version the judgment, not the model

Prompts, schema, tolerance tables, and golden sets are versioned artifacts
(v1, v2 …) checked into the repo. Model IDs are pinned and recorded in every
trace. When a model changes, rerun `make eval` and diff the numbers before
accepting it. Never edit a golden label to make a run pass; if a label is
wrong, change it in its own commit with a one-line justification in the
manifest history.

## Rule 7 — Report the honest ceiling, unprompted

Every quality number is reported with: n, how measured, and what it cannot
see. Small n gets the words "directional, not statistically significant" in
the report itself. False-flag rate gets equal prominence with catch rate.
Never round up, never hide a red number — a failing metric printed in red is
more valuable to this project than a passing one.

## Rule 8 — Iterate on one variable, log every iteration

When improving quality: change the prompt OR the schema OR the normalizer in
one step, rerun the eval, append one line to `eval_log.md`
(`date, what changed, catch_rate, false_flag_rate, notes`). The fix history is
a deliverable. If a change improves catch rate but raises false flags, that is
a trade-off to surface, not a win to report.

## Rule 9 — Cost and trace are features

Every model call is traced (model, version, tokens, latency) and the eval
report states cost per document at current prices. If a quality gain doubles
cost, say so next to the gain.

## Anti-patterns (stop and correct if observed)

- Retry-until-pass loops around model calls in the eval path
- "It looks right" as acceptance for anything model-generated
- Tolerances or normalization rules living inside a prompt
- A judge/extractor from the same family checking its own family's work
- Golden labels edited in the same commit as the code change they excuse
- Reporting an average score, or a rate without its n
