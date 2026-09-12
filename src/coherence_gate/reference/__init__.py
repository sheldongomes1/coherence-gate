"""Reference-document lane (v0.2 CS4): term-sheet claims about the underlying index vs the
index methodology. Models extract the rulebook (dual family); code decides."""
from .lane import ReferenceRules, check_reference, load_reference

__all__ = ["ReferenceRules", "check_reference", "load_reference"]
