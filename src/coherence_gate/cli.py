"""cg — Coherence Gate command line (LLD §12)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def _latest(run_root: Path) -> Path:
    runs = sorted(p for p in Path(run_root).iterdir() if p.is_dir() and p.name[0].isdigit())
    if not runs:
        sys.exit(f"no runs under {run_root}")
    return runs[-1]


def cmd_eval(a: argparse.Namespace) -> int:
    from .eval.harness import run_eval
    ev = run_eval(Path(a.golden), Path(a.out), stub=a.stub, booking_transport=a.booking, with_triage=a.triage,
                  only=a.only, source=a.source, parser_name=a.parser)
    console.print(f"[bold]run {ev.run_id}[/] → {ev.run_dir}/eval_report.md")
    t = Table("metric", "result")
    for r in (ev.catch_strict, ev.catch_field_only, ev.false_flag_fields, ev.false_flag_docs, ev.trap_resolved,
              ev.auto_clear_correctness, ev.agreement, *ev.extraction_accuracy.values()):
        t.add_row(r.label, r.render())
    t.add_row("cost per document", f"${ev.cost_per_doc:.4f}")
    console.print(t)
    return 0


def cmd_run(a: argparse.Namespace) -> int:
    from .eval.harness import build_context
    from .pipeline import run_document
    ctx = build_context(Path(a.golden), Path(a.out), stub=a.stub, booking_transport=a.booking, with_triage=a.triage,
                        source=a.source, parser_name=a.parser)
    try:
        doc = Path(a.termsheet)
        pdf = doc if doc.suffix.lower() == ".pdf" else None
        txt = doc if doc.suffix.lower() == ".txt" else Path(a.golden) / "termsheets" / f"{doc.stem}.txt"
        r = run_document(txt, ctx, trade_id=a.trade_id, pdf_path=pdf)
    finally:
        ctx.booking.close()
    console.print(f"[bold]{r.doc_id}[/] lane={r.document_lane} trade_id={r.trade_id} cost=${r.cost_usd:.4f} → {r.out_dir}")
    t = Table("field", "type", "sev", "lane", "detail")
    for f in r.findings:
        t.add_row(f.field, f.type, f.severity, f.lane, f.detail[:90])
    console.print(t)
    return 0


def cmd_trace(a: argparse.Namespace) -> int:
    from .trace import read_trace
    run = _latest(Path(a.latest)) if a.latest else Path(a.run)
    lines = read_trace(run / "trace.jsonl")
    t = Table("doc", "step", "model", "version", "in", "out", "ms", "cost $", "outcome", title=f"trace {run.name}")
    for l in lines:
        t.add_row(l["doc_id"], l["step"], l["model"] or "", l["model_version"] or "", str(l["prompt_tokens"]),
                  str(l["output_tokens"]), str(l["latency_ms"]), f"{l['cost_usd']:.4f}", str(l["outcome"]))
    console.print(t)
    console.print(f"total cost ${sum(l['cost_usd'] for l in lines):.4f} over {len(lines)} steps")
    return 0


def cmd_parse(a: argparse.Namespace) -> int:
    """Pre-parse every golden PDF into golden/parsed (versioned artifacts)."""
    import json
    from .ingest import get_parser, parse_document
    golden = Path(a.golden); parser = get_parser(a.parser)
    manifest = json.loads((golden / "manifest.json").read_text())
    for e in manifest["documents"]:
        if not e.get("pdf"):
            continue
        res, cached = parse_document(e["id"], golden / e["pdf"], parser, golden / "parsed")
        console.print(f"{e['id']}: {'cached' if cached else 'parsed'} via {res.meta.get('vendor')} job={res.meta.get('job_id')} {res.meta.get('latency_ms')} ms, {len(res.markdown)} chars")
    return 0


def cmd_ablation(a: argparse.Namespace) -> int:
    from .eval.ablation import render_parse_tax
    out = render_parse_tax(Path(a.txt_run), Path(a.pdf_run))
    console.print(f"wrote {out} (and appended to {Path(a.pdf_run) / 'eval_report.md'})")
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    from .report.desk_view import render as render_desk
    from .report.html import render
    run = _latest(Path(a.latest)) if a.latest else Path(a.run)
    out = render(run); desk = render_desk(run)
    console.print(f"wrote {out}\nwrote {desk}")
    return 0


DEMO = [
    ("G11", "Clean document. Both families agree on every field, the comparator passes, the document AUTO-CLEARS. Zero human touch, and zero model calls after extraction."),
    ("G10", "The term sheet never states the knock-in level; the booking has 70%. Both extractors DECLARE ABSENT, code raises TS_ABSENT (critical) and the triage agent drafts the desk query. The absence announced itself."),
    ("G09", "The coupon is printed as 2.0625% per quarter (8.25% p.a.). Whatever each family extracts, normalize.py brings it to 8.25 per annum; the merger agrees; the comparator matches the booking. Code decided, not a prompt."),
]


def cmd_demo(a: argparse.Namespace) -> int:
    from .eval.harness import build_context
    from .pipeline import run_document
    from .report.html import render
    a.triage = True
    ctx = build_context(Path(a.golden), Path(a.out), stub=a.stub, booking_transport=a.booking, with_triage=True)
    console.rule("[bold]Coherence Gate — demo")
    try:
        for doc_id, story in DEMO:
            console.print(f"\n[bold]{doc_id}[/] — {story}")
            r = run_document(Path(a.golden) / "termsheets" / f"{doc_id}.txt", ctx)
            t = Table("field", "type", "lane", "term sheet", "booking", title=f"{doc_id}: document lane = {r.document_lane}  cost ${r.cost_usd:.4f}")
            for f in r.findings:
                if f.type != "CLEAN" or doc_id == "G11":
                    t.add_row(f.field, f.type, f.lane, str(f.ts_value if f.ts_value is not None else "ABSENT"), str(f.booking_value if f.booking_value is not None else "ABSENT"))
            console.print(t)
            for f in r.findings:
                if f.triage:
                    console.print(f"[bold]desk query ({f.field}, {f.triage.classification}):[/] {f.triage.desk_query}")
    finally:
        ctx.booking.close()
    from .report.desk_view import render as render_desk
    out = render(ctx.out_dir); desk = render_desk(ctx.out_dir)
    console.rule()
    console.print(f"desk view: {desk}\nreport:    {out}\ntrace:     {ctx.tracer.path}   (make trace)\neval:      run `make eval` for eval_report.md; history in eval_log.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cg", description="Coherence Gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--golden", default="golden")
        sp.add_argument("--out", default="runs")
        sp.add_argument("--stub", action="store_true", help="no model calls (S0 checkpoint)")
        sp.add_argument("--booking", choices=["mcp", "direct"], default="direct")
        sp.add_argument("--triage", action="store_true", help="run the triage agent on TRIAGE findings")
        sp.add_argument("--source", choices=["pdf", "txt"], default="pdf", help="pdf: parse stage + citations into parsed text; txt: canonical text (ablation/fallback)")
        sp.add_argument("--parser", choices=["mixedbread", "local"], default="mixedbread")

    e = sub.add_parser("eval"); common(e); e.add_argument("--only", nargs="*"); e.set_defaults(fn=cmd_eval)
    r = sub.add_parser("run"); common(r); r.add_argument("termsheet"); r.add_argument("--trade-id"); r.set_defaults(fn=cmd_run)
    t = sub.add_parser("trace"); t.add_argument("--latest", nargs="?", const="runs"); t.add_argument("--run"); t.set_defaults(fn=cmd_trace)
    pa = sub.add_parser("parse"); pa.add_argument("--golden", default="golden"); pa.add_argument("--parser", choices=["mixedbread", "local"], default="mixedbread"); pa.set_defaults(fn=cmd_parse)
    ab = sub.add_parser("ablation"); ab.add_argument("--txt-run", required=True); ab.add_argument("--pdf-run", required=True); ab.set_defaults(fn=cmd_ablation)
    rp = sub.add_parser("report"); rp.add_argument("--latest", nargs="?", const="runs"); rp.add_argument("--run"); rp.set_defaults(fn=cmd_report)
    dm = sub.add_parser("demo"); common(dm); dm.set_defaults(fn=cmd_demo)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
