# Proposal decisions (human, eval-gated)

| date | proposal | applied in | measured by | decision | why |
|---|---|---|---|---|---|
| 2026-09-12 | judgment_change/20260912-191532_G02_autocall_observation_dates_desk_rejected.md (3-day tolerance on autocall observation dates) | commit "CS8c cycle step 3: APPLY proposal" | runs/20260912-200709 vs baseline 20260912-180705 → `eval_diff_cycle.md`; fixture test; live rehearsal | **HELD** (reverted) | Strict catch 17/17 → 16/17; **auto_clear_correctness 17/17 → 16/17: the planted G02 shift was auto-cleared with zero human touch.** The live rehearsal also missed a +1 day booking edit on a clean document. The desk's underlying point (booked dates are business-day-adjusted, term-sheet dates are not) is real; the right fix is a golden candidate where the adjustment is stated so the comparator can *check* it, not a tolerance that stops looking. |

Rules: a proposal is applied only in its own commit; the eval decides; a HOLD is reverted in its own commit with this row; the proposal file stays on record unchanged.
