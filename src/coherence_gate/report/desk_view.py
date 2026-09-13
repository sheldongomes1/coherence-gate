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
RED_TYPES = {"MISMATCH", "TS_ABSENT", "BOOKING_ABSENT", "RELATION_VIOLATION", "REFERENCE_INCONSISTENT"}
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
    ("REFERENCE_INCONSISTENT", "ref:index_return_treatment"): "term sheet calls the index {ts} but its methodology says {bk} — payoff described on the wrong index economics",
    ("REFERENCE_INCONSISTENT", "ref:index_rebalance_frequency"): "term sheet says the index rebalances {ts} but the rulebook says {bk} — the hedge described is not the index that trades",
    ("REFERENCE_INCONSISTENT", None): "term sheet describes the index contrary to its methodology ({field}: documented {ts}, rulebook {bk})",
    ("MISMATCH", "index_vol_target_pct"): "index vol target booked {bk} vs {ts} documented — static data describes a different index",
    ("MISMATCH", None): "{field} booked {bk} vs {ts} documented",
}


# Which finding leads a row / the modal: economic terms first, then dates, then index claims.
LEAD_RANK = {k: i for i, k in enumerate([
    "participation_rate_pct", "notional", "currency", "premium_amount", "rel:premium_arithmetic", "barrier_level_pct",
    "coupon_rate_pct", "coupon_memory", "underlyings", "strike_level_pct", "autocall_level_pct", "autocall_observation_dates",
    "day_count", "maturity_date", "expiration_date", "valuation_date"])}


def _fmt(v) -> str:
    """Desk-readable value: lists joined, big numbers with separators, ABSENT for None."""
    if v is None:
        return "ABSENT"
    if isinstance(v, (list, tuple)):
        return ", ".join(_fmt(x) for x in v)
    if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(v)
            if isinstance(parsed, (list, tuple)):
                return ", ".join(_fmt(x) for x in parsed)
        except (ValueError, SyntaxError):
            pass
    try:
        from decimal import Decimal
        d = Decimal(str(v))
        if abs(d) >= 1000 and d == d.to_integral():
            return f"{int(d):,}"
    except Exception:  # noqa: BLE001
        pass
    return str(v)


def _clean_cite(text: str) -> str:
    from ..extract.schema_guard import display_span
    return display_span(text or "")


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
        crit = sorted(reds, key=lambda f: (f["severity"] != "critical", LEAD_RANK.get(f["field"], 50), f["field"]))[0]
        extra = f" (+{len(reds) - 1} more)" if len(reds) > 1 else ""
        return "MISMATCH", consequence(crit) + extra
    if ambers:
        fields = ", ".join(sorted({f["field"] for f in ambers}))
        return "DISAGREEMENT", f"reading uncertain on {fields} — human review queued"
    n = len(findings)
    return "ATTESTED", f"booking attested against term sheet — {n} fields, both families agree"


def _musd(v) -> str:
    """USD 96.3mm style, sign kept; '—' when unknown."""
    if v is None:
        return "—"
    a = abs(float(v)); sign = "-" if float(v) < 0 else ""
    return f"{sign}USD {a/1e6:,.1f}mm" if a >= 1e6 else f"{sign}USD {a:,.0f}"


def _fixture(doc_id: str, trade_id: str, fixtures: dict) -> dict:
    fx = fixtures.get(trade_id) or fixtures.get(doc_id) or {}
    return fx


def render(run_dir: Path, out: Path | None = None, store_dir: Path | None = None, golden_href: str | None = None) -> Path:
    """`golden_href`: where the golden files sit relative to the page (default: computed from the run dir;
    the assembled static site passes 'golden')."""
    data = load_run(run_dir)
    if store_dir is None:  # a run made against a rehearsal store records it in the config line
        for l in data["trace"]:
            if l["step"] == "config" and isinstance(l.get("detail"), dict) and l["detail"].get("bookings_dir"):
                store_dir = Path(l["detail"]["bookings_dir"]); break
    cfg = yaml.safe_load((ROOT / "config" / "report.yaml").read_text()) if (ROOT / "config" / "report.yaml").exists() else {}
    book = (cfg.get("book") or {}).get("name", "Demo book")
    fx_path = ROOT / "golden" / "desk_fixtures.json"
    fixtures = json.loads(fx_path.read_text()) if fx_path.exists() else {}
    fb_path = ROOT / "feedback" / "feedback.jsonl"
    verdicts: dict[str, str] = {}
    if fb_path.exists():
        for l in fb_path.read_text().splitlines():
            if l.strip():
                r = json.loads(l); verdicts[r["finding_id"]] = r["verdict"]
    rows = []
    for d in data["docs"]:
        state, why = trust_state(d["findings"])
        marks = sorted({verdicts[f"{d['doc_id']}:{f['field']}"] for f in d["findings"] if f"{d['doc_id']}:{f['field']}" in verdicts})
        if marks:
            why += " · desk verdict recorded: " + ", ".join(m.replace("desk_", "") for m in marks)
        stale = _stale_reason(run_dir, d, store_dir)
        if stale:
            state, why = "STALE", stale
        fx = _fixture(d["doc_id"], d["trade_id"] or "", fixtures)
        dusd = fx.get("delta_usd")
        at_stake = abs(dusd) if (dusd is not None and state != "ATTESTED") else None
        n_crit = sum(1 for f in d["findings"] if f["type"] != "CLEAN" and f["severity"] == "critical")
        rows.append({"doc_id": d["doc_id"], "trade_id": d["trade_id"] or d["doc_id"], "state": state, "why": why,
                     "at_stake": at_stake, "at_stake_fmt": _musd(at_stake) if at_stake is not None else "—", "n_critical": n_crit,
                     "product": d.get("product_type", "note"), "underlying": fx.get("underlying", "—"),
                     "notional": fx.get("notional", "—"), "notional_usd": fx.get("notional_usd", 0), "maturity": fx.get("maturity", "—"),
                     "delta": fx.get("delta_pct_notional", "—"), "delta_usd": dusd, "delta_usd_fmt": _musd(dusd),
                     "vega": fx.get("vega_usd_per_vol_pt", "—")})
    # red → stale → amber → green; within a state, the biggest exposure at stake first
    order = {"MISMATCH": 0, "STALE": 1, "DISAGREEMENT": 2, "ATTESTED": 3}
    rows.sort(key=lambda r: (order[r["state"]], -(r["at_stake"] or 0), r["trade_id"]))
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
    def gross(sel):
        return sum(abs(r["delta_usd"] or 0) for r in rows if sel(r))
    exposure = {"total": gross(lambda r: True), "attention": gross(lambda r: r["state"] in ("MISMATCH", "DISAGREEMENT")),
                "stale": gross(lambda r: r["state"] == "STALE"), "attested": gross(lambda r: r["state"] == "ATTESTED"),
                "notional_total": sum(r["notional_usd"] or 0 for r in rows)}
    # Evidence for the modal: per document, non-clean findings first, then clean ones (collapsed on the page).
    # Grounding links: the source PDF, the parsed text the gate actually read, the booking as read by
    # this run, and the booking store's current record (relative to the run directory).
    import os
    golden = ROOT / "golden"
    def rel(p: Path) -> str:
        if golden_href is not None:
            return golden_href + "/" + os.path.relpath(p, golden.resolve())
        return os.path.relpath(p, Path(run_dir).resolve())
    evidence = {}
    for d in data["docs"]:
        doc = d["doc_id"]; tid = d["trade_id"] or ""
        links = {}
        if (golden / "pdf" / f"{doc}.pdf").exists():
            links["term sheet (PDF)"] = rel((golden / "pdf" / f"{doc}.pdf").resolve())
        parsed = (d.get("attested_hashes") or {}).get("document_path")
        if parsed and Path(parsed).exists():
            links["parsed text the gate read"] = rel(Path(parsed).resolve())
        elif (golden / "termsheets" / f"{doc}.txt").exists():
            links["text the gate read"] = rel((golden / "termsheets" / f"{doc}.txt").resolve())
        if (Path(run_dir) / doc / "booking.json").exists():
            links["booking as read by this run"] = f"{doc}/booking.json"
        if tid and (golden / "bookings" / f"{tid}.json").exists():
            links["booking store (current record)"] = rel((golden / "bookings" / f"{tid}.json").resolve())
        fs = [{"field": f["field"], "type": f["type"], "severity": f["severity"], "lane": f["lane"],
               "ts": _fmt(f.get("ts_value")), "bk": _fmt(f.get("booking_value")), "detail": f.get("detail", ""),
               "citations": [_clean_cite(c["text_span"]) for c in f.get("citations", [])],
               "consequence": consequence(f) if f["type"] in RED_TYPES else "",
               "triage": (f.get("triage") or {}).get("desk_query"), "classification": (f.get("triage") or {}).get("classification")}
              for f in d["findings"]]
        order = {t: i for i, t in enumerate(["MISMATCH", "TS_ABSENT", "BOOKING_ABSENT", "RELATION_VIOLATION", "REFERENCE_INCONSISTENT",
                                              "EXTRACTOR_DISAGREEMENT", "MALFORMED_EXTRACTION", "CLEAN"])}
        fs.sort(key=lambda f: (f["type"] == "CLEAN", f["severity"] != "critical", LEAD_RANK.get(f["field"], 50), order.get(f["type"], 9), f["field"]))
        evidence[d["doc_id"]] = {"trade_id": d["trade_id"], "lane": d["document_lane"], "product": d.get("product_type", "note"),
                                 "source": d.get("source"), "parse": (d.get("parse") or {}).get("job_id"), "findings": fs,
                                 "links": links, "attested": d.get("attested_hashes") or {}}
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.filters["musd"] = _musd
    html = env.get_template("desk_view.html.j2").render(
        book=book, run_id=data["run_id"], ts=datetime.now().strftime("%Y-%m-%d %H:%M"), rows=rows,
        n_attested=sum(r["state"] == "ATTESTED" for r in rows), n_attention=sum(r["state"] in ("MISMATCH", "DISAGREEMENT") for r in rows),
        n_stale=sum(r["state"] == "STALE" for r in rows), cost=sum(l["cost_usd"] for l in trace), tools=tools,
        exposure=exposure, evidence_json=json.dumps(evidence, default=str).replace("</", "<\\/"))
    out = out or Path(run_dir) / "desk_view.html"
    out.write_text(html)
    return out


def _stale_reason(run_dir: Path, d: dict, store_dir: Path | None = None) -> str | None:
    """CS7c: an attestation is bound to (source text sha, canonical booking sha). At page time
    both are recomputed from the current files; if either moved, the row is STALE with the reason.
    No watchers, no daemons: a hash comparison when the page is generated."""
    att = d.get("attested_hashes") if isinstance(d, dict) else None
    if not att:
        return None
    from ..booking import store
    from ..pipeline import booking_hash
    moved = []
    doc_path = att.get("document_path")
    if doc_path and att.get("document_sha256") and Path(doc_path).exists():
        if hashlib.sha256(Path(doc_path).read_text().encode()).hexdigest() != att["document_sha256"]:
            moved.append("document")
    tid = att.get("booking_trade_id")
    if tid and att.get("booking_sha256"):
        res = store.lookup(store_dir or (ROOT / "golden" / "bookings"), tid)
        keys = att.get("booking_terms_keys")  # older runs attested to the whole record
        if not res["found"] or booking_hash(res["record"], keys) != att["booking_sha256"]:
            moved.append("deal terms in the booking")
    if not moved:
        return None
    return f"attestation invalidated — {' and '.join(moved)} changed since last check; re-check queued"
