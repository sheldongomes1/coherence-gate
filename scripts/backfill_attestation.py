"""Recompute attested_hashes for a stored run under ADR-28 (deal-terms projection) from the booking
each document actually read (runs/<ts>/<doc>/booking.json). No model calls. Usage: backfill_attestation.py runs/<ts>"""
import hashlib
import json
import sys
from pathlib import Path

from coherence_gate.pipeline import booking_hash
from coherence_gate.schema_loader import schema_for

run = Path(sys.argv[1]); n = 0
for d in sorted(p for p in run.iterdir() if p.is_dir() and (p / "summary.json").exists()):
    s = json.loads((d / "summary.json").read_text()); b = json.loads((d / "booking.json").read_text())
    keys = schema_for(s.get("product_type", "note")).comparison_keys
    att = s.get("attested_hashes") or {}
    att.update({"booking_terms_keys": keys, "booking_sha256": booking_hash(b.get("record"), keys) if b.get("found") else None,
                "booking_trade_id": s.get("trade_id")})
    if not att.get("document_sha256"):
        att["document_sha256"] = s.get("sha256")
    s["attested_hashes"] = att; (d / "summary.json").write_text(json.dumps(s, indent=2, default=str)); n += 1
print(f"backfilled {n} attestations in {run}")
