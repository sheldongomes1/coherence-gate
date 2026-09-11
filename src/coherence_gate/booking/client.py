"""Booking clients (LLD §8). Both expose the same `lookup`; the pipeline only sees the
interface, and the transport actually used is written into every BookingLookup.

MCP-over-stdio client is added in S1 (ADR-6, 2h timebox); `DirectBookingClient` is the
fallback with an identical signature.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..types import BookingLookup
from . import store


class BookingClient(Protocol):
    transport: str

    def lookup(self, trade_id: str) -> BookingLookup: ...

    def close(self) -> None: ...


class DirectBookingClient:
    transport = "direct"

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = Path(store_dir)

    def lookup(self, trade_id: str) -> BookingLookup:
        res = store.lookup(self.store_dir, trade_id)
        return BookingLookup(trade_id=trade_id, found=res["found"], record=res.get("record"),
                             transport="direct")

    def close(self) -> None:
        return None
