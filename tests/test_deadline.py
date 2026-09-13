import time

import pytest

from coherence_gate.trace import DeadlineExceeded, run_with_deadline


def test_deadline_returns_value_and_raises_on_stall():
    assert run_with_deadline(lambda: 42, 1.0) == 42
    with pytest.raises(DeadlineExceeded):
        run_with_deadline(lambda: time.sleep(5), 0.2, what="stall")
    with pytest.raises(ValueError):
        run_with_deadline(lambda: (_ for _ in ()).throw(ValueError("x")), 1.0)


def test_deadline_names_a_suspended_process(monkeypatch):
    """If the wait returns far past its own deadline the process was not running; the message must say so."""
    import threading
    real_wait = threading.Event.wait
    clock = iter([0.0, 10.0])  # monotonic: start, then "woke up" 10 s later on a 0.2 s deadline
    monkeypatch.setattr(time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(threading.Event, "wait", lambda self, timeout=None: False)
    with pytest.raises(DeadlineExceeded, match="suspended"):
        run_with_deadline(lambda: None, 0.2, what="x")
    monkeypatch.setattr(threading.Event, "wait", real_wait)
