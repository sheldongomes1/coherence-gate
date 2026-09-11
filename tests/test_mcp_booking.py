from pathlib import Path

import pytest

from coherence_gate.booking.client import DirectBookingClient

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "bookings"


def test_direct_client():
    c = DirectBookingClient(GOLDEN)
    r = c.lookup("SN-2026-0101")
    assert r.found and r.record["barrier_level_pct"] == 70 and r.transport == "direct"
    assert not c.lookup("NOPE").found
    assert not c.lookup("../manifest").found  # path traversal is sanitized


@pytest.mark.timeout(60) if hasattr(pytest, "timeout") else pytest.mark.skipif(False, reason="")
def test_mcp_client_round_trip():
    from coherence_gate.booking.mcp_client import McpBookingClient
    c = McpBookingClient(GOLDEN)
    try:
        r = c.lookup("SN-2026-0109")
        assert r.found and r.transport == "mcp-stdio"
        assert r.record["coupon_rate_pct"] == 8.25 and r.record["underlyings"] == ["BVERSA10"]
        assert not c.lookup("SN-0000-0000").found
    finally:
        c.close()
