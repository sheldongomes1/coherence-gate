"""Assemble the self-contained static site in site/ (desk view as index). Markdown pages are
rendered to HTML with the report's CSS so a browser shows them; source .md files stay alongside."""
import shutil
from pathlib import Path

import markdown

from coherence_gate.report.desk_view import render as render_desk

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CSS = """<style>body{margin:0;padding:24px 20px 60px;background:#fbfaf7;color:#1c1b19;font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:1100px;margin-inline:auto}
table{border-collapse:collapse;background:#fff;border:1px solid #e4e1da;font-size:13px;margin:10px 0}th,td{padding:6px 9px;border-bottom:1px solid #e4e1da;text-align:left;vertical-align:top}th{background:#f3f1ec}
code,pre{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px}pre{background:#f6f4ef;padding:10px;overflow-x:auto}h1{font-size:22px}h2{font-size:17px;border-bottom:1px solid #e4e1da;padding-bottom:4px;margin-top:28px}
nav{font-size:13px;color:#6b6862;margin-bottom:14px}nav a{margin-right:12px}</style>"""
NAV = ('<nav><a href="index.html">desk view</a><a href="run_report.html">run report</a><a href="eval_report.html">eval report</a>'
       '<a href="BRIEF.html">brief</a><a href="eval_log.html">eval log</a><a href="eval_diff.html">model-swap diff</a>'
       '<a href="eval_diff_cycle.html">feedback-cycle diff</a><a href="MODEL-RISK.html">model risk</a><a href="README.html">readme</a></nav>')


def md_to_html(src: Path, dst: Path, title: str) -> None:
    body = markdown.markdown(src.read_text(), extensions=["tables", "fenced_code"])
    dst.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>{CSS}</head><body>{NAV}{body}</body></html>")


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(ROOT / "runs" / "showcase", SITE)
    for sub in ("pdf", "parsed", "bookings", "termsheets"):
        shutil.copytree(ROOT / "golden" / sub, SITE / "golden" / sub)
    render_desk(ROOT / "runs" / "showcase", out=SITE / "desk_view.html", golden_href="golden")
    (SITE / "index.html").write_text((SITE / "desk_view.html").read_text())
    pages = {"eval_report.md": ROOT / "runs" / "showcase" / "eval_report.md", "BRIEF.md": ROOT / "BRIEF.md", "README.md": ROOT / "README.md",
             "eval_log.md": ROOT / "eval_log.md", "eval_diff.md": ROOT / "eval_diff.md", "eval_diff_cycle.md": ROOT / "eval_diff_cycle.md",
             "MODEL-RISK.md": ROOT / "MODEL-RISK.md"}
    for name, src in pages.items():
        if src.exists():
            shutil.copy(src, SITE / name)
            md_to_html(src, SITE / name.replace(".md", ".html"), name.replace(".md", ""))
    # nav on the two generated pages too
    for page in ("desk_view.html", "index.html", "run_report.html"):
        p = SITE / page; h = p.read_text()
        p.write_text(h.replace("<body>", "<body>" + NAV.replace("<nav>", '<nav style="font:13px system-ui;color:#6b6862;margin-bottom:12px">'), 1))
    (SITE / "Dockerfile").write_text(
        "FROM nginx:1.27-alpine\n"
        "COPY . /usr/share/nginx/html\n"
        "RUN rm -f /usr/share/nginx/html/Dockerfile && sed -i 's/listen       80;/listen       8080;/' /etc/nginx/conf.d/default.conf\n"
        "EXPOSE 8080\n")  # Cloud Run injects PORT=8080
    print(f"site/ ready ({sum(f.stat().st_size for f in SITE.rglob('*') if f.is_file()) / 1e6:.1f} MB): index.html = desk view")


if __name__ == "__main__":
    main()
