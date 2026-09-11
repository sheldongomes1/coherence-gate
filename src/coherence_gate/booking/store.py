"""The books-and-records store: one JSON file per trade id. Only the MCP server and the
direct fallback client import this module (HLD §4)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def lookup(store_dir: Path, trade_id: str) -> dict[str, Any]:
    safe = "".join(c for c in trade_id.strip() if c.isalnum() or c in "-_")
    path = Path(store_dir) / f"{safe}.json"
    if not path.is_file():
        return {"found": False, "trade_id": trade_id}
    return {"found": True, "trade_id": trade_id, "record": json.loads(path.read_text())}
