# Desk feedback (CS8b)

One JSON line per disposition, appended by `cg feedback <doc>:<field> --verdict desk_accepted|desk_rejected --note "..."`.
Feedback never changes model or pipeline behaviour; `cg propose` turns it into human-reviewed proposals.
