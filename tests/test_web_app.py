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
