# Tolerance: date-schedule elements within 3 days → informational, not MISMATCH

**Kind:** judgment_change  
**From feedback:** G02:autocall_observation_dates (MISMATCH, desk_rejected) in run 20260912-191532  
**Desk note:** Desk: the booked 15 Nov 2027 is the business-day-adjusted date for the 12 Nov observation; the term sheet shows unadjusted dates. Not a discrepancy.  
**Drafted:** 2026-09-12T23:50:53+00:00

**Artifact:** tolerance table, entry for observation/valuation date-list fields (`autocall_observation_dates`, `coupon_observation_dates`, `valuation_dates`).

**Change:** when TS and booking date lists are equal in length and in every element except ones where the booking date is **later than** the TS date by **1–3 calendar days**, emit severity `informational` with reason code `BDAY_ADJUSTMENT_CANDIDATE` instead of `minor MISMATCH`. Any element differing by >3 days, differing in the earlier direction, or any length mismatch keeps current `minor MISMATCH`.

**Consequence template** for the new code: "Booking date {b} may be the business-day-adjusted form of unadjusted TS date {t}. Confirm the holiday calendar and business-day convention in the term sheet before booking sign-off."

**Why not a full normalization rule:** 12 Nov 2027 is a Friday, so the roll to Mon 15 Nov cannot be derived from weekend logic alone — it requires the instrument's holiday calendar, which the comparator does not currently ingest. Silently normalizing would require guessing a calendar and would suppress genuine off-by-days booking errors. Downgrading preserves visibility while removing the false MISMATCH from the desk's minor-severity queue.

**Follow-up (not proposed here):** if the extractor is taught to read the Business Day Convention / calendar clause, this tolerance should be replaced by exact adjusted-date comparison.

**Predicted effect:** False-flag rate on minor-severity date-schedule findings should fall (this case and its class move to informational); catch rate on date fields should not move, since no comparison is suppressed and differences >3 days or in the earlier direction retain MISMATCH severity.

**Rationale:** The desk stated that booked 15 Nov 2027 is the business-day-adjusted form of the unadjusted 12 Nov term-sheet date and "not a discrepancy," but the roll is not derivable without a holiday calendar, so the defensible change is severity downgrade with a confirmation prompt rather than silent normalization.

---
PROPOSAL ONLY — apply via its own commit, rerun `make eval`, review the diff. Nothing in this file has been applied.
