"""Assemble the full packet (prep chapter + every project document) into one PDF.
Usage: uv run python scripts/build_packet.py [out.pdf]   (default private/Coherence-Gate-Packet.pdf)
The prep chapter lives in private/ (git-ignored); everything else is the repository verbatim."""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import markdown
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "private" / "Coherence-Gate-Packet.pdf"

SECTIONS = [
    ("Part I — Interview preparation", [("private/INTERVIEW-PREP.md", "Interview preparation")]),
    ("Part II — The product", [("BRIEF.md", "Brief (generated from the release run)"), ("README.md", "README"), ("GOAL.md", "Goal and success criteria")]),
    ("Part III — Design and architecture", [("docs/DESIGN.md", "Design: phases and cut lines"), ("docs/HLD.md", "High-level design"),
                                            ("docs/LLD.md", "Low-level design"), ("docs/V2-CHANGES.md", "v0.2 change sets")]),
    ("Part IV — Decisions", [("docs/DECISIONS.md", "Architecture decision records (ADR-1..32)"), ("proposals/DECISIONS.md", "Proposal decisions (feedback loop)")]),
    ("Part V — Evidence", [("runs/showcase/eval_report.md", "Eval report, release run 20260913-113753"), ("eval_log.md", "Eval log (iteration history)"),
                           ("eval_diff.md", "Eval diff: effort sweep"), ("eval_diff_cycle.md", "Eval diff: the held tolerance proposal")]),
    ("Part VI — Governance", [("MODEL-RISK.md", "Model-risk summary (generated)"), ("SKILL.md", "Eval-first discipline (the rules the build followed)")]),
    ("Part VII — Lessons and memory", [("docs/lessons.md", "Lessons (build diary)"), ("docs/memories.md", "Tutor memory")]),
]

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; @bottom-center { content: "Coherence Gate — packet v0.2.1 · page " counter(page); font: 9px Helvetica, Arial, sans-serif; color: #777; } }
body { font: 10.5px/1.45 Helvetica, Arial, sans-serif; color: #1a1a1a; }
h1 { font-size: 20px; margin: 0 0 6px; page-break-before: always; }
h1.part { font-size: 26px; margin-top: 40mm; color: #2a4d7a; }
h2 { font-size: 14px; margin: 16px 0 6px; border-bottom: 1px solid #ccc; }
h3 { font-size: 12px; margin: 12px 0 4px; }
p { margin: 5px 0; }
table { border-collapse: collapse; margin: 6px 0; font-size: 9.5px; width: 100%; }
th, td { border: 1px solid #ccc; padding: 3px 5px; vertical-align: top; text-align: left; }
th { background: #f0f0f0; }
code { font: 9px ui-monospace, Menlo, monospace; background: #f5f5f5; padding: 0 2px; }
pre { font: 8.5px/1.3 ui-monospace, Menlo, monospace; background: #f7f7f7; border: 1px solid #ddd; padding: 6px; white-space: pre-wrap; word-break: break-word; }
blockquote { border-left: 3px solid #ccc; margin: 6px 0; padding: 2px 10px; color: #444; }
.cover { page-break-after: always; margin-top: 60mm; }
.cover h1 { page-break-before: auto; font-size: 34px; color: #2a4d7a; }
.cover p { font-size: 13px; }
.toc li { margin: 2px 0; }
.src { color: #777; font-size: 9px; margin: 0 0 8px; }
a { color: #2a4d7a; text-decoration: none; }
"""

def md_to_html(text: str) -> str:
    text = text.replace("🟢", "PASS").replace("🔴", "FAIL").replace("🟡", "WARN")
    text = re.sub(r"^# ", "## ", text, count=1, flags=re.M)     # the document's own H1 becomes H2 under the packet's H1
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])

parts = [f'<div class="cover"><h1>Coherence Gate</h1><p><b>The full packet, v0.2.1</b> — {date.today().isoformat()}</p>'
         '<p>Interview preparation, brief, design, architecture, every decision record, the evidence, the model-risk summary, the lessons.</p>'
         '<p>Repository: github.com/sheldongomes1/coherence-gate · Live demo: coherence-gate-demo-521865321554.us-central1.run.app</p></div>']
toc = ["<h1>Contents</h1><ol class='toc'>"]
n = 0
for part, files in SECTIONS:
    toc.append(f"<li><b>{part}</b><ol>")
    for rel, title in files:
        n += 1
        toc.append(f"<li>{title} <span class='src'>({rel})</span></li>")
    toc.append("</ol></li>")
toc.append("</ol>")
parts.append("".join(toc))
for part, files in SECTIONS:
    parts.append(f'<h1 class="part">{part}</h1>')
    for rel, title in files:
        p = ROOT / rel
        if not p.exists():
            parts.append(f"<h1>{title}</h1><p class='src'>{rel} — missing</p>"); continue
        parts.append(f"<h1>{title}</h1><p class='src'>{rel}</p>" + md_to_html(p.read_text()))
html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(parts)}</body></html>"
OUT.parent.mkdir(parents=True, exist_ok=True)
HTML(string=html, base_url=str(ROOT)).write_pdf(str(OUT))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB, {n} documents)")
