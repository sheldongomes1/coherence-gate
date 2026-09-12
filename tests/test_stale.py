"""CS7c: an attested row goes STALE when the booking (or document) changes; re-check restores it. Stub pipeline, no network."""
import json
import shutil
from pathlib import Path

from coherence_gate.eval.harness import build_context
from coherence_gate.pipeline import run_document
from coherence_gate.report.desk_view import _stale_reason
from coherence_gate.report.html import load_run

ROOT = Path(__file__).resolve().parents[1]


def test_stale_on_booking_amendment(tmp_path):
    store = tmp_path / "bookings"; shutil.copytree(ROOT / "golden" / "bookings", store)
    ctx = build_context(ROOT / "golden", tmp_path / "runs", stub=True)
    from coherence_gate.booking.client import DirectBookingClient
    ctx.booking = DirectBookingClient(store)
    r = run_document(ROOT / "golden" / "termsheets" / "G11.txt", ctx, trade_id="SN-2026-0111")
    att = json.loads((r.out_dir / "summary.json").read_text())["attested_hashes"]
    assert att["booking_sha256"] and att["document_sha256"]
    d = load_run(ctx.out_dir)["docs"][0]
    assert _stale_reason(ctx.out_dir, d, store) is None
    b = store / "SN-2026-0111.json"; rec = json.loads(b.read_text()); rec["barrier_level_pct"] = 65; b.write_text(json.dumps(rec))
    assert "booking" in _stale_reason(ctx.out_dir, d, store)
    # re-check: a new run binds to the amended booking -> not stale
    r2 = run_document(ROOT / "golden" / "termsheets" / "G11.txt", ctx, trade_id="SN-2026-0111")
    d2 = load_run(ctx.out_dir)["docs"][0]
    assert _stale_reason(ctx.out_dir, d2, store) is None
