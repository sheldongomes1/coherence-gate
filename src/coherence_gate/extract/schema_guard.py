"""Post-validation of a raw extraction: every field present, citation verbatim in source (char_range recomputed in code), status/value invariants. Violations -> MALFORMED_EXTRACTION findings, never a crash.

STATUS: scaffold. See docs/LLD.md §9.4.
"""
