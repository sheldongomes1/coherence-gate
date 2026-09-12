"""desk_view.html (V2-CHANGES CS5): the trader's 6am page for one run. Three trust states
plus STALE (CS7c). Consequence phrasing is a deterministic table (direction, never magnitude)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from ..config import ROOT
from .html import load_run

TEMPLATES = ROOT / "templates"
RED_TYPES = {"MISMATCH", "TS_ABSENT", "BOOKING_ABSENT", "RELATION_VIOLATION"}
AMBER_TYPES = {"EXTRACTOR_DISAGREEMENT", "MALFORMED_EXTRACTION"}

# finding type / field -> one line of desk consequence. `{ts}` documented, `{bk}` booked.
CONSEQUENCE = {
    ("MISMATCH", "barrier_level_pct"): "knock-in booked {bk} vs {ts} documented — knock-in risk computed off the wrong level",
    ("MISMATCH", "participation_rate_pct"): "participation booked {bk} vs {ts} documented — client payout {dir_under}",
    ("MISMATCH", "coupon_memory"): "memory booked {bk} vs {ts} documented — coupon liability {dir_memory}",
    ("MISMATCH", "notional"): "notional booked {bk} vs {ts} documented — hedge sized off the wrong notional",
    ("MISMATCH", "currency"): "currency booked {bk} vs {ts} documented — FX exposure unrecognised",
    ("MISMATCH", "day_count"): "day count booked {bk} vs {ts} documented — accrued coupon miscomputed every period",
    ("MISMATCH", "underlyings"): "underlying booked {bk} vs {ts} documented — hedge on the wrong index",
    ("MISMATCH", "autocall_observation_dates"): "autocall date booked {bk} vs {ts} documented — early-redemption cash flow on the wrong day",
    ("MISMATCH", "autocall_level_pct"): "autocall levels booked {bk} vs {ts} documented — step-down not booked, redemption probability wrong",
    ("MISMATCH", "coupon_rate_pct"): "coupon booked {bk} vs {ts} documented — coupon liability wrong every period",
    ("MISMATCH", "premium_amount"): "premium booked {bk} vs {ts} documented — cash settlement on the wrong amount",
    ("MISMATCH", "strike_level_pct"): "strike booked {bk} vs {ts} documented — payout computed off the wrong strike",
    ("TS_ABSENT", None): "term sheet is silent on {field}; booking carries {bk} — booked term has no documentary basis",
    ("BOOKING_ABSENT", None): "{field} documented as {ts} but not booked — term missing from the system of record",
    ("RELATION_VIOLATION", "rel:premium_arithmetic"): "premium arithmetic fails on the booking — premium booked off the wrong notional",
    ("MISMATCH", None): "{field} booked {bk} vs {ts} documented",
}


def _fmt(v) -> str:
    return "ABSENT" if v is None else str(v)


def consequence(f: dict) -> str:
    key = (f["type"], f["field"])
    tpl = CONSEQUENCE.get(key) or CONSEQUENCE.get((f["type"], None)) or "{field}: {type}"
    ts, bk = f.get("ts_value"), f.get("booking_value")

    def num(x):
        try:
            return float(str(x).replace(",", ""))
        except (TypeError, ValueError):
            return None

    dir_under = "under-hedged" if (num(bk) is not None and num(ts) is not None and num(bk) < num(ts)) else "over-hedged"
    dir_memory = "understated" if str(bk).lower() in ("false", "0") else "overstated"
    return tpl.format(ts=_fmt(ts), bk=_fmt(bk), field=f["field"], type=f["type"], dir_under=dir_under, dir_memory=dir_memory)


def trust_state(findings: list[dict]) -> tuple[str, str]:
    reds = [f for f in findings if f["type"] in RED_TYPES]
    ambers = [f for f in findings if f["type"] in AMBER_TYPES]
    if reds:
        crit = sorted(reds, key=lambda f: (f["severity"] != "critical", f["field"]))[0]
        extra = f" (+{len(reds) - 1} more)" if len(reds) > 1 else ""
        return "MISMATCH", consequence(crit) + extra
    if ambers:
        fields = ", ".join(sorted({f["field"] for f in ambers}))
        return "DISAGREEMENT", f"reading uncertain on {fields} — human review queued"
    n = len(findings)
    return "ATTESTED", f"booking attested against term sheet — {n} fields, both families agree"


def _fixture(doc_id: str, trade_id: str, fixtures: dict) -> dict:
    fx = fixtures.get(trade_id) or fixtures.get(doc_id) or {}
    return fx


def render(run_dir: Path, out: Path | None = None) -> Path:
    data = load_run(run_dir)
    cfg = yaml.safe_load((ROOT / "config" / "report.yaml").read_text()) if (ROOT / "config" / "report.yaml").exists() else {}
    book = (cfg.get("book") or {}).get("name", "Demo book")
    fx_path = ROOT / "golden" / "desk_fixtures.json"
    fixtures = json.loads(fx_path.read_text()) if fx_path.exists() else {}
    rows = []
    for d in data["docs"]:
        state, why = trust_state(d["findings"])
        stale = _stale_reason(run_dir, d)
        if stale:
            state, why = "STALE", stale
        fx = _fixture(d["doc_id"], d["trade_id"] or "", fixtures)
        rows.append({"doc_id": d["doc_id"], "trade_id": d["trade_id"] or d["doc_id"], "state": state, "why": why,
                     "product": d.get("product_type", "note"), "underlying": fx.get("underlying", "—"),
                     "notional": fx.get("notional", "—"), "maturity": fx.get("maturity", "—"),
                     "delta": fx.get("delta_pct_notional", "—"), "vega": fx.get("vega_usd_per_vol_pt", "—")})
    order = {"MISMATCH": 0, "STALE": 1, "DISAGREEMENT": 2, "ATTESTED": 3}
    rows.sort(key=lambda r: (order[r["state"]], r["trade_id"]))
    trace = data["trace"]
    steps = [l["step"] for l in trace]
    tools = [
        {"name": "parse", "kind": "vendor ML (Mixedbread) behind parse(pdf)", "calls": steps.count("parse"), "note": "cached artifacts count as calls to the tool, not to the vendor"},
        {"name": "extract:gemini", "kind": "LLM, family A", "calls": steps.count("extract:gemini"), "note": "cites verbatim or declares absent"},
        {"name": "extract:claude", "kind": "LLM, family B", "calls": steps.count("extract:claude"), "note": "independent of family A"},
        {"name": "booking_lookup", "kind": "MCP tool (books & records)", "calls": steps.count("booking_lookup"), "note": "the only path to booking truth"},
        {"name": "compare + relations", "kind": "deterministic code", "calls": steps.count("compare"), "note": "match/no-match, tolerances, arithmetic"},
        {"name": "reference check", "kind": "deterministic code over the Versa methodology", "calls": steps.count("reference_check"), "note": "not run in this release" if steps.count("reference_check") == 0 else ""},
        {"name": "triage", "kind": "LLM, drafts desk queries", "calls": sum(1 for s_ in steps if s_.startswith("triage:")), "note": "only for non-clean findings"},
    ]
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    html = env.get_template("desk_view.html.j2").render(
        book=book, run_id=data["run_id"], ts=datetime.now().strftime("%Y-%m-%d %H:%M"), rows=rows,
        n_attested=sum(r["state"] == "ATTESTED" for r in rows), n_attention=sum(r["state"] in ("MISMATCH", "DISAGREEMENT") for r in rows),
        n_stale=sum(r["state"] == "STALE" for r in rows), cost=sum(l["cost_usd"] for l in trace), tools=tools)
    out = out or Path(run_dir) / "desk_view.html"
    out.write_text(html)
    return out


def _stale_reason(run_dir: Path, d: dict) -> str | None:
    """CS7c: an attestation is bound to (parsed document sha, booking sha). If either current
    artifact differs from what the run attested, the row is STALE. Only ATTESTED rows can go stale."""
    att = d.get("attested_hashes") if isinstance(d, dict) else None
    if not att:
        return None
    moved = []
    for label, path, sha in (("document", att.get("document_path"), att.get("document_sha256")),
                             ("booking", att.get("booking_path"), att.get("booking_sha256"))):
        if path and sha and Path(path).exists():
            cur = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if cur != sha:
                moved.append(label)
    if not moved:
        return None
    what = " and ".join(moved)
    return f"attestation invalidated — {what} changed since last check; re-check queued"
