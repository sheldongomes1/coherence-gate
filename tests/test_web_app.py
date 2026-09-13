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
