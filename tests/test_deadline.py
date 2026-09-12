import time

import pytest

from coherence_gate.trace import DeadlineExceeded, run_with_deadline


def test_deadline_returns_value_and_raises_on_stall():
    assert run_with_deadline(lambda: 42, 1.0) == 42
    with pytest.raises(DeadlineExceeded):
        run_with_deadline(lambda: time.sleep(5), 0.2, what="stall")
    with pytest.raises(ValueError):
        run_with_deadline(lambda: (_ for _ in ()).throw(ValueError("x")), 1.0)
