"""Coherence Gate demo service.

State lives under STATE_DIR (default ./state): an editable copy of the booking store and the
"current" run (seeded from runs/showcase). Every page is re-rendered on request so STALE is
recomputed against the editable store. A relaunch runs the real pipeline (both families,
comparator, relations, reference lane, triage) for the chosen trades on a background thread and
writes the results into the current run; the page polls /api/status until done.
One instance (Cloud Run max-instances=1) keeps the state coherent; it is a demo, not a platform.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from ..config import ROOT, load_config
from ..pipeline import booking_hash

STATE = Path(os.environ.get("STATE_DIR", ROOT / "state"))
SITE = Path(os.environ.get("SITE_DIR", ROOT / "site"))
STORE = STATE / "bookings"
RUN = STATE / "current"
GOLDEN = ROOT / "golden"

app = FastAPI(title="Coherence Gate demo")
jobs: dict[str, dict] = {}
lock = threading.Lock()
_ctx_cache: dict = {}   # the run context (extractors, parser, reference rules) is built once per process


def init_state(reset: bool = False) -> None:
    if reset and STATE.exists():
        shutil.rmtree(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    if not STORE.exists():
        shutil.copytree(GOLDEN / "bookings", STORE)
    if not RUN.exists():
        shutil.copytree(ROOT / "runs" / "showcase", RUN)
    render_pages()


def render_pages() -> None:
    from ..report.desk_view import render as render_desk
    from ..report.html import render as render_html
    render_html(RUN)
    render_desk(RUN, store_dir=STORE, golden_href="golden", live=True)


def _manifest() -> dict:
    return {d["id"]: d for d in json.loads((GOLDEN / "manifest.json").read_text())["documents"]}


def stale_docs() -> list[str]:
    from ..report.html import load_run
    from ..report.desk_view import _stale_reason
    return [d["doc_id"] for d in load_run(RUN)["docs"] if _stale_reason(RUN, d, STORE)]


def _run_docs(job_id: str, doc_ids: list[str], full: bool = False) -> None:
    """full=False: re-check against the current booking reusing the attested extractions (seconds).
    full=True: re-read the term sheet with both families (1–4 min per trade)."""
    from ..eval.harness import build_context
    from ..pipeline import recheck_document, run_document
    man = _manifest()
    job = jobs[job_id]
    try:
        if "ctx" not in _ctx_cache:  # reference rules (methodology parse + both extractions) load once, then are reused
            c = build_context(GOLDEN, STATE / "runs", stub=False, booking_transport="direct", with_triage=True,
                              source="pdf", parser_name="mixedbread", reference=True, bookings_dir=STORE)
            _ctx_cache["ctx"] = c
        ctx = _ctx_cache["ctx"]
        ctx.out_dir = RUN  # results replace the trade's folder inside the current run
        ctx.tracer.path = RUN / "trace.jsonl"
        for i, doc in enumerate(doc_ids, 1):
            job.update({"status": "running", "current": doc, "done": i - 1, "total": len(doc_ids), "mode": "full" if full else "recheck"})
            e = man[doc]
            with lock:
                if full:
                    run_document(GOLDEN / e["termsheet"], ctx, trade_id=None, pdf_path=GOLDEN / e["pdf"], product_type=e.get("product_type"))
                else:
                    try:
                        recheck_document(doc, ctx, RUN, product_type=e.get("product_type"))
                    except (FileNotFoundError, ValueError) as why:  # nothing reusable: full read, and say so
                        job["mode"] = f"full ({why})"
                        run_document(GOLDEN / e["termsheet"], ctx, trade_id=None, pdf_path=GOLDEN / e["pdf"], product_type=e.get("product_type"))
            job["done"] = i
        with lock:
            render_pages()
        job.update({"status": "done", "finished": time.time()})
    except Exception as exc:  # noqa: BLE001
        job.update({"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:300]}"})


NO_STORE = {"Cache-Control": "no-store, max-age=0"}


@app.on_event("startup")
def _startup() -> None:
    init_state()


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/desk_view.html", response_class=HTMLResponse)
def desk_view() -> HTMLResponse:
    with lock:
        render_pages()
        return HTMLResponse((RUN / "desk_view.html").read_text(), headers=NO_STORE)


@app.get("/run_report.html", response_class=HTMLResponse)
def run_report() -> HTMLResponse:
    with lock:
        return HTMLResponse((RUN / "run_report.html").read_text(), headers=NO_STORE)


@app.get("/api/state")
def api_state() -> JSONResponse:
    return JSONResponse({"stale": stale_docs(), "jobs": {k: v for k, v in jobs.items()}, "store": str(STORE)})


@app.post("/api/relaunch")
def api_relaunch(doc: str | None = None, scope: str = "stale", full: int = 0) -> JSONResponse:
    """doc=<G14>: one trade. scope=stale: every trade whose booking changed. scope=all: the whole book.
    full=1: re-read the term sheet with both model families instead of reusing the attested extraction."""
    if doc:
        docs = [doc]
    elif scope == "all":
        docs = list(_manifest())
    else:
        docs = stale_docs()
    if not docs:
        return JSONResponse({"job": None, "message": "nothing is stale; use scope=all to re-check the whole book"})
    running = [j for j in jobs.values() if j["status"] == "running"]
    if running:
        return JSONResponse({"job": None, "message": "a relaunch is already running"}, status_code=409)
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {"status": "queued", "docs": docs, "done": 0, "total": len(docs), "started": time.time(), "mode": "full" if full else "recheck"}
    threading.Thread(target=_run_docs, args=(job_id, docs, bool(full)), daemon=True).start()
    return JSONResponse({"job": job_id, "docs": docs, "mode": "full" if full else "recheck"})


@app.get("/api/status/{job_id}")
def api_status(job_id: str) -> JSONResponse:
    return JSONResponse(jobs.get(job_id, {"status": "unknown"}))


@app.get("/booking/{trade_id}", response_class=HTMLResponse)
def booking_form(trade_id: str) -> HTMLResponse:
    p = STORE / f"{trade_id}.json"
    if not p.exists():
        return HTMLResponse("unknown trade", status_code=404)
    rec = json.loads(p.read_text())
    rows = "".join(
        f'<tr><td class="k">{k}</td><td><input name="{k}" value="{json.dumps(v) if isinstance(v, (list, bool)) else v}" style="width:100%;font:13px ui-monospace,monospace"></td></tr>'
        for k, v in rec.items())
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Booking {trade_id}</title>
<style>body{{font:14px -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:900px;margin:30px auto;padding:0 16px;color:#1c1b19;background:#fbfaf7}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e4e1da}}td{{padding:6px 8px;border-bottom:1px solid #e4e1da}}td.k{{width:34%;font-family:ui-monospace,monospace;font-size:12.5px;background:#f4f2ec}}
button{{background:#12314f;color:#fff;border:0;padding:9px 16px;border-radius:6px;font-size:14px;cursor:pointer}}.sub{{color:#6b6862}}</style></head><body>
<div class="sub"><a href="/">← desk view</a></div><h2>Booking record {trade_id} (the bank's truth, editable for the demo)</h2>
<p class="sub">Change any field that affects the terms of the deal (e.g. participation_rate_pct 100 → 95, coupon_memory true → false, barrier_level_pct). Save, go back to the desk view: the row is STALE because its deal-terms hash moved. Press Relaunch: the gate re-reads the term sheet with both model families and re-checks it against this record. Lists and booleans are JSON.</p>
<form method="post"><table>{rows}</table><p><button type="submit">Save booking</button> &nbsp; <a href="/">cancel</a></p></form>
</body></html>"""
    return HTMLResponse(html)


@app.post("/booking/{trade_id}")
async def booking_save(trade_id: str, request: Request) -> RedirectResponse:
    p = STORE / f"{trade_id}.json"
    rec = json.loads(p.read_text())
    form = await request.form()
    for k in rec:
        if k in form:
            raw = str(form[k]).strip()
            old = rec[k]
            try:
                if isinstance(old, bool):
                    rec[k] = json.loads(raw.lower())
                elif isinstance(old, list):
                    rec[k] = json.loads(raw)
                elif isinstance(old, (int, float)):
                    rec[k] = float(raw) if "." in raw else int(raw)
                else:
                    rec[k] = raw
            except (ValueError, json.JSONDecodeError):
                rec[k] = raw
    p.write_text(json.dumps(rec, indent=2))
    return RedirectResponse("/", status_code=303)


@app.post("/api/reset")
def api_reset() -> RedirectResponse:
    with lock:
        init_state(reset=True)
    return RedirectResponse("/", status_code=303)


# static: everything in the current run (per-doc booking.json etc.), the golden files the links point to, and the site's docs
app.mount("/golden", StaticFiles(directory=str(GOLDEN)), name="golden")
if SITE.exists():
    app.mount("/site", StaticFiles(directory=str(SITE), html=True), name="site")


@app.get("/{path:path}")
def fallback(path: str):
    for base in (RUN, SITE):
        p = base / path
        if p.is_file():
            return FileResponse(str(p))
    return HTMLResponse("not found", status_code=404)
