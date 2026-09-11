"""MCP-over-stdio booking client (LLD §8). Spawns the server once per run on a background
event loop and holds the session; the sync pipeline calls `lookup` like any other client.
The transport actually used is recorded in every BookingLookup and trace line."""
from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path
from typing import Any

import mcp
from mcp.client.stdio import StdioServerParameters

from ..types import BookingLookup


class McpBookingClient:
    transport = "mcp-stdio"

    def __init__(self, store_dir: Path, timeout_s: float = 30.0) -> None:
        self.store_dir = Path(store_dir)
        self.timeout_s = timeout_s
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="mcp-booking", daemon=True)
        self._thread.start()
        self._client: mcp.Client | None = None
        self._run(self._connect())

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=self.timeout_s)

    async def _connect(self) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "coherence_gate.booking.mcp_server", "--store", str(self.store_dir)],
        )
        self._client = mcp.Client(params, raise_exceptions=True)
        await self._client.__aenter__()

    async def _call(self, trade_id: str) -> dict[str, Any]:
        assert self._client is not None
        res = await self._client.call_tool("booking_lookup", {"trade_id": trade_id})
        if res.structured_content:
            payload = res.structured_content
            return payload.get("result", payload) if isinstance(payload, dict) else payload
        text = "".join(getattr(c, "text", "") for c in res.content)
        return json.loads(text)

    def lookup(self, trade_id: str) -> BookingLookup:
        res = self._run(self._call(trade_id))
        return BookingLookup(trade_id=trade_id, found=bool(res.get("found")), record=res.get("record"),
                             transport="mcp-stdio")

    def close(self) -> None:
        if self._client is not None:
            try:
                self._run(self._client.__aexit__(None, None, None))
            except Exception:  # noqa: BLE001 — shutdown must not mask the run result
                pass
            self._client = None
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
