"""Demo service: the static fallback serves web assets from the run/site directories only."""
import os
from pathlib import Path

from fastapi.testclient import TestClient


def _client(tmp_path: Path):
    os.environ["STATE_DIR"] = str(tmp_path / "state")
    site = tmp_path / "site"; site.mkdir()
    (site / "Dockerfile").write_text("FROM x")
    (site / "page.html").write_text("<p>hi</p>")
    (site / ".secret").write_text("no")
    os.environ["SITE_DIR"] = str(site)
    import importlib
    from coherence_gate.web import app as web
    importlib.reload(web)
    return TestClient(web.app)


def test_fallback_serves_assets_only_and_stays_contained(tmp_path):
    c = _client(tmp_path)
    assert c.get("/Dockerfile").status_code == 404
    assert c.get("/.secret").status_code == 404
    assert c.get("/page.html").status_code == 200
    assert c.get("/../pyproject.toml").status_code in (404, 302, 307)
    assert c.get("/site/Dockerfile").status_code == 404          # the bundle path follows the same asset rules
    assert c.get("/site/page.html").status_code == 200
    assert c.get("/site/", follow_redirects=False).status_code == 302


def test_feedback_endpoint_records_a_verdict_and_rejects_bad_input(tmp_path):
    import json
    c = _client(tmp_path)
    from coherence_gate.web import app as web
    web.init_state()                                   # showcase run + bookings + the shipped feedback file
    doc = next(d.name for d in sorted(web.RUN.iterdir()) if (d / "findings.json").exists())
    f = next(x for x in json.loads((web.RUN / doc / "findings.json").read_text()) if x["type"] != "CLEAN")
    r = c.post("/api/feedback", json={"doc": doc, "field": f["field"], "verdict": "desk_rejected", "note": "known"})
    assert r.status_code == 200 and r.json()["recorded"]["finding_id"] == f"{doc}:{f['field']}"
    rows = [json.loads(l) for l in web.FEEDBACK.read_text().splitlines() if l.strip()]
    assert rows[-1]["verdict"] == "desk_rejected" and rows[-1]["via"] == "desk_view" and rows[-1]["finding_type"] == f["type"]
    assert c.post("/api/feedback", json={"doc": doc, "field": f["field"], "verdict": "maybe"}).status_code == 400
    assert c.post("/api/feedback", json={"doc": "NOPE", "field": "x", "verdict": "desk_accepted"}).status_code == 404
    assert 'id="fbcount"' in c.get("/").text


def test_loading_the_desk_view_does_not_rebuild_the_run_report(tmp_path):
    """GET / used to render run_report.html and throw it away: ~50 ms and a 2.8 MB page built for nobody."""
    import os, time
    c = _client(tmp_path)
    from coherence_gate.web import app as web
    web.init_state()
    report = web.RUN / "run_report.html"
    before = report.stat().st_mtime
    time.sleep(0.02)
    assert c.get("/").status_code == 200
    assert report.stat().st_mtime == before, "the desk view rebuilt the run report"
    # a job that changes artifacts still refreshes both pages
    web.render_pages("both")
    assert report.stat().st_mtime > before


def test_public_endpoints_refuse_bad_input_instead_of_crashing(tmp_path):
    """Every one of these returned a 500 with a traceback, a job that died in the worker, or a silently
    coerced value. A public demo endpoint answers 400."""
    import json
    c = _client(tmp_path)
    from coherence_gate.web import app as web
    web.init_state()
    assert c.post("/api/feedback", content="not json").status_code == 400
    assert c.post("/api/feedback", json=[1, 2]).status_code == 400
    assert c.post("/api/relaunch?doc=G99").status_code == 400
    assert c.post("/api/relaunch?doc=../../etc/passwd").status_code == 400
    assert web.jobs == {}, "a refused relaunch must not leave a job behind"

    trade = json.loads(next(iter(sorted((web.STORE).glob("*.json")))).read_text())
    tid = trade["trade_id"]
    numeric = next((k for k, v in trade.items() if isinstance(v, (int, float)) and not isinstance(v, bool)), None)
    if numeric:
        r = c.post(f"/booking/{tid}", data={numeric: "not-a-number"}, follow_redirects=False)
        assert r.status_code == 400 and "is not a" in r.text
        after = json.loads((web.STORE / f"{tid}.json").read_text())
        assert after[numeric] == trade[numeric], "an invalid value was written into a numeric field"


def test_the_eval_answer_key_is_not_part_of_the_demo_surface(tmp_path):
    c = _client(tmp_path)
    from coherence_gate.web import app as web
    web.init_state()
    assert c.get("/golden/truth/G01.json").status_code == 404      # the eval's ground truth
    assert c.get("/golden/manifest.json").status_code == 404
    assert c.get("/golden/pdf/G14.pdf").status_code == 200         # what the grounding links point at


def test_a_full_reread_is_swapped_in_atomically(tmp_path):
    """A full re-read takes minutes and cannot hold the page lock, so a page could pair a new
    findings.json with an old summary.json. The document is staged and swapped instead."""
    import json
    c = _client(tmp_path)
    from coherence_gate.web import app as web
    from coherence_gate.eval.harness import build_context
    web.init_state()
    doc = sorted(d.name for d in web.RUN.iterdir() if d.is_dir() and (d / "summary.json").exists())[0]
    entry = web._manifest()[doc]
    before = json.loads((web.RUN / doc / "summary.json").read_text())

    ctx = build_context(web.GOLDEN, web.STATE / "runs", stub=True, source="txt")
    ctx.out_dir = web.RUN
    ctx.tracer.path = web.RUN / "trace.jsonl"
    web._full_read(doc, entry, ctx)

    after = json.loads((web.RUN / doc / "summary.json").read_text())
    assert after["doc_id"] == before["doc_id"]
    assert (web.RUN / doc / "findings.json").exists()
    assert ctx.out_dir == web.RUN, "the staging directory leaked into the context"
    assert not list(web.STATE.glob("staging-*")), "staging directories were left behind"
    assert not list(web.RUN.glob(".*.replaced")), "a replaced document directory was left behind"
