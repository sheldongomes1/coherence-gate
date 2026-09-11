"""stdio MCP server exposing the books-and-records store as one tool (LLD §8, ADR-6).

    python -m coherence_gate.booking.mcp_server --store golden/bookings

The pipeline reaches booking truth only through `booking_lookup`. In a bank this process is
replaced by the real books-and-records MCP endpoint; the client and the pipeline do not change.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import store

STORE_DIR = Path(os.environ.get("CG_BOOKING_STORE", "golden/bookings"))

server = MCPServer(
    name="booking-store",
    instructions="Books-and-records lookup for structured notes. booking_lookup(trade_id) returns the booked record.",
    version="1",
)


@server.tool(description="Return the booking record for a trade id, or found=false.")
def booking_lookup(trade_id: str) -> dict[str, Any]:
    return store.lookup(STORE_DIR, trade_id)


def main() -> None:
    global STORE_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(STORE_DIR))
    STORE_DIR = Path(ap.parse_args().store)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
