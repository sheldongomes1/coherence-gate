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
                  only=a.only)
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
    ctx = build_context(Path(a.golden), Path(a.out), stub=a.stub, booking_transport=a.booking, with_triage=a.triage)
    try:
        r = run_document(Path(a.termsheet), ctx, trade_id=a.trade_id)
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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cg", description="Coherence Gate")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--golden", default="golden")
        sp.add_argument("--out", default="runs")
        sp.add_argument("--stub", action="store_true", help="no model calls (S0 checkpoint)")
        sp.add_argument("--booking", choices=["mcp", "direct"], default="direct")
        sp.add_argument("--triage", action="store_true", help="run the triage agent on TRIAGE findings")

    e = sub.add_parser("eval"); common(e); e.add_argument("--only", nargs="*"); e.set_defaults(fn=cmd_eval)
    r = sub.add_parser("run"); common(r); r.add_argument("termsheet"); r.add_argument("--trade-id"); r.set_defaults(fn=cmd_run)
    t = sub.add_parser("trace"); t.add_argument("--latest", nargs="?", const="runs"); t.add_argument("--run"); t.set_defaults(fn=cmd_trace)
    for name in ("demo", "report"):
        d = sub.add_parser(name); d.set_defaults(fn=lambda a, n=name: sys.exit(f"`cg {n}` is built in S4"))
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
