"""Per-deal provenance graph: what went in, what each step did, what came out.

Every node and edge here is read back from what the run already persisted (`trace.jsonl` plus the
per-document artifacts). Nothing new is instrumented and nothing is recomputed, so drawing the graph
cannot change a result: it is the same relationship to the run that `cg rescore` has to the report.

The picture answers the model-risk question directly — "where did this finding come from" — by
making the lineage clickable: a node that produced an artifact links to that artifact, so the
reader goes from the box to the exact JSON the step emitted.

Layout is deliberate rather than computed: the pipeline is a fixed DAG (LLD §1), so columns are
stages and rows are the parallel work inside a stage. No graph library, no layout engine, no
runtime dependency — the same reason the rest of the reporting is plain Jinja and plain SVG.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# palette: the desk view's, so the graph does not look like a foreign object on the page
C = {
    "bg": "#fbfaf7", "fg": "#1c1b19", "muted": "#6b6862", "line": "#d8d4cb",
    "ok": "#1f7a4d", "okbg": "#e6f4ec",
    "bad": "#b3261e", "badbg": "#fbe9e7",
    "warn": "#8a5a00", "warnbg": "#fff3d6",
    "reuse": "#3a5a7a", "reusebg": "#e8eef5",
    "code": "#3f3b34", "codebg": "#f1efe9",
    "in": "#4b4f57", "inbg": "#eceef1",
}
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif"

W, H, GX, GY, M = 176, 92, 84, 16, 16          # node width/height, gaps, margin
# the horizontal gap is wide on purpose: every edge label sits in it, never on a box

# outcomes that mean "the step did its work" vs "the answer was reused" vs "it never completed"
DONE = {"OK", "FOUND", "CLEAN", "AUTO_CLEAR", "NO_CLAIMS", "note", "otc_option"}
REUSED = {"CACHED", "REUSED_EXTRACTION"}
FAILED = {"API_ERROR", "TIMEOUT", "MALFORMED", "REFUSAL", "NOT_FOUND", "UNAVAILABLE",
          "SKIPPED_WHOLESALE_FAILURE", "MISSING"}


@dataclass
class Node:
    id: str
    col: int
    row: int
    kind: str                      # input | vendor | model | code | tool | output
    title: str
    sub: str = ""
    metrics: str = ""
    outcome: str = ""
    href: str | None = None        # the artifact this step produced, relative to the page
    tip: str = ""


@dataclass
class Edge:
    src: str
    dst: str
    label: str = ""


@dataclass
class Graph:
    doc_id: str
    trade_id: str | None
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    caption: str = ""

    def by_id(self, nid: str) -> Node | None:
        return next((n for n in self.nodes if n.id == nid), None)


def _load(p: Path) -> Any:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _money(v: float | None) -> str:
    return "" if not v else (f"${v:.4f}" if v < 0.01 else f"${v:.3f}")


def _ms(v: int | None) -> str:
    if not v:
        return ""
    return f"{v} ms" if v < 1000 else f"{v / 1000:.1f} s"


def _tone(outcome: str) -> tuple[str, str]:
    """border, fill for an outcome. A reused answer is blue, not green: it was not bought again."""
    if outcome in REUSED:
        return C["reuse"], C["reusebg"]
    if outcome in FAILED:
        return C["bad"], C["badbg"]
    if outcome in DONE or not outcome:
        return C["ok"], C["okbg"]
    if outcome in ("TRIAGE", "INFO"):
        return C["warn"], C["warnbg"]
    return C["ok"], C["okbg"]


def build(run_dir: Path, doc_id: str, golden_href: str | None = None) -> Graph:
    """Read one document's stored artifacts and trace lines into a graph. Missing artifacts become
    nodes that say so (a blank box would be exactly the silent failure this product exists to stop)."""
    run_dir = Path(run_dir)
    d = run_dir / doc_id
    summary = _load(d / "summary.json") or {}
    trace = []
    tpath = run_dir / "trace.jsonl"
    if tpath.exists():
        for line in tpath.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("doc_id") == doc_id:
                trace.append(row)
    step = {}
    for row in trace:                                   # last line per step wins (a relaunch rewrites it)
        step[row["step"]] = row

    g = Graph(doc_id=doc_id, trade_id=summary.get("trade_id"))
    att = summary.get("attested_hashes") or {}
    source = summary.get("source", "txt")
    parse_meta = summary.get("parse") or {}
    breakdown = summary.get("cost_breakdown") or {}

    # ---- column 0: what went in -------------------------------------------------------------
    import os
    golden = (Path(__file__).resolve().parents[3] / "golden")
    gh = golden_href if golden_href is not None else os.path.relpath(golden, run_dir.resolve())

    def gref(*parts: str) -> str | None:
        p = golden.joinpath(*parts)
        return f"{gh}/{'/'.join(parts)}" if p.exists() else None

    sha = str(att.get("document_sha256") or summary.get("sha256") or "")
    doc_href = gref("pdf", f"{doc_id}.pdf") if source == "pdf" else gref("termsheets", f"{doc_id}.txt")
    g.nodes.append(Node(
        id="doc", col=0, row=0, kind="input",
        title="Term sheet" + (" (PDF)" if source == "pdf" else " (text)"),
        sub=f"{doc_id} · {summary.get('product_type', 'note')}",
        metrics="sha " + (sha[:12] or "?"),
        tip="The document as received. Every citation anchors into the text read from this file.",
        href=doc_href))

    booking = _load(d / "booking.json") or {}
    n_terms = len(booking.get("record") or {})
    found = bool(booking.get("found"))
    g.nodes.append(Node(
        id="book_in", col=0, row=1, kind="input", title="Booking record",
        sub=str(summary.get("trade_id") or booking.get("trade_id") or "—"),
        metrics=f"{n_terms} fields" if found else "not found",
        outcome="" if found else "NOT_FOUND",
        tip="The bank's truth for this trade, reached only through the MCP tool.",
        href=f"{doc_id}/booking.json"))

    ref_step = step.get("reference_check")
    if ref_step:
        g.nodes.append(Node(
            id="meth", col=0, row=2, kind="input", title="Index methodology",
            sub="Bloomberg Versa rulebook", metrics="extracted once, cached",
            tip="The governing rulebook, read once by both families and cached across runs."))

    # ---- column 1: parse, column 2: the two readings and the booking fetch --------------------
    row1 = 0
    if source == "pdf" or "parse" in step:
        p = step.get("parse", {})
        g.nodes.append(Node(
            id="parse", col=1, row=0, kind="vendor", title="parse(pdf)",
            sub=f"{parse_meta.get('vendor', 'mixedbread')} · {parse_meta.get('mode', '')}".strip(" ·"),
            metrics=" · ".join(x for x in (f"{parse_meta.get('pages', '?')} pages",
                                           _ms(parse_meta.get("latency_ms") or p.get("latency_ms"))) if x),
            outcome=p.get("outcome", ""),
            tip="Vendor parsing behind a one-module interface; the parsed markdown is what the gate reads and cites.",
            href=gref("parsed", f"{doc_id}.md")))

    for fam in ("gemini", "claude"):
        s = step.get(f"extract:{fam}", {})
        ex = _load(d / f"extraction_{fam}.json") or {}
        fields = ex.get("fields") or {}
        n_ext = sum(1 for v in fields.values() if v.get("status") == "EXTRACTED")
        n_abs = sum(1 for v in fields.values() if v.get("status") != "EXTRACTED")
        out = s.get("outcome", "MISSING" if not ex else "")
        bits = [f"{n_ext} cited", f"{n_abs} absent"] if fields else []
        if out in REUSED:
            prior = (step.get("load", {}).get("detail") or {})
            prior = prior.get("prior_run") if isinstance(prior, dict) else None
            bits = ["reused" + (f" from {Path(str(prior)).name}" if prior else ""), *bits]
        else:
            bits += [x for x in (_ms(s.get("latency_ms")), _money(s.get("cost_usd"))) if x]
        g.nodes.append(Node(
            id=f"ex_{fam}", col=2, row=row1, kind="model",
            title=f"extract · {fam}", sub=str(ex.get("model") or s.get("model") or "—"),
            metrics=" · ".join(bits), outcome=out,
            tip=("Reads the document into the versioned schema: every field is cited to a verbatim span "
                 "or explicitly declared absent. Never decides anything."),
            href=f"{doc_id}/extraction_{fam}.json" if ex else None))
        row1 += 1

    bl = step.get("booking_lookup", {})
    g.nodes.append(Node(
        id="lookup", col=2, row=row1, kind="tool", title="booking_lookup()",
        sub=str(booking.get("transport") or bl.get("detail", {}).get("transport", "mcp-stdio")),
        metrics=" · ".join(x for x in (bl.get("outcome", ""), _ms(bl.get("latency_ms"))) if x),
        outcome=bl.get("outcome", "" if found else "NOT_FOUND"),
        tip="MCP tool: the only path to books and records, in the eval and in the live service alike.",
        href=f"{doc_id}/booking.json"))

    # ---- column 2: agreement ----------------------------------------------------------------
    merged = _load(d / "merged.json") or {}
    n_agree = sum(1 for v in merged.values() if v.get("agree"))
    mg = step.get("merge", {})
    g.nodes.append(Node(
        id="merge", col=3, row=0, kind="code", title="normalize + merge",
        sub="deterministic, unit-tested",
        metrics=f"{n_agree}/{len(merged)} fields agree" if merged else (mg.get("outcome", "") or "—"),
        outcome="MALFORMED" if (merged and n_agree < len(merged)) else mg.get("outcome", ""),
        tip=("Canonical forms in code (per-quarter vs per-annum, date formats, enums), then the two "
             "families are compared to each other. Disagreement is a finding, never arbitrated."),
        href=f"{doc_id}/merged.json" if merged else None))

    # ---- column 3: the decision -------------------------------------------------------------
    findings = _load(d / "findings.json") or []
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.get("type", "?")] = counts.get(f.get("type", "?"), 0) + 1
    cmp_step = step.get("compare", {})
    g.nodes.append(Node(
        id="compare", col=4, row=0, kind="code", title="compare",
        sub="tolerance table, in code",
        metrics=f"{len(merged) or len(findings)} checks · {counts.get('MISMATCH', 0)} mismatch",
        outcome=cmp_step.get("outcome", ""),
        tip="The match / no-match call. No model is consulted here: this is the line the product rests on.",
        href=f"{doc_id}/findings.json" if findings else None))
    row3 = 1
    if any(str(f.get("field", "")).startswith("rel:") for f in findings):
        n_rel = sum(1 for f in findings if str(f.get("field", "")).startswith("rel:"))
        g.nodes.append(Node(
            id="rel", col=4, row=row3, kind="code", title="relations",
            sub="arithmetic across fields", metrics=f"{n_rel} checked",
            tip="Schema-declared relations, e.g. premium = notional × premium %.",))
        row3 += 1
    if ref_step:
        rd = ref_step.get("detail") or {}
        g.nodes.append(Node(
            id="ref", col=4, row=row3, kind="code", title="reference check",
            sub="claims vs the rulebook",
            metrics=" · ".join(f"{k.lower().replace('_', ' ')} {v}" for k, v in list(rd.items())[:2]) if isinstance(rd, dict) else "",
            outcome=ref_step.get("outcome", ""),
            tip="Term-sheet claims about the index checked against the methodology's own rules.",))
        row3 += 1

    # ---- column 4: lanes, explanation, output ------------------------------------------------
    n_auto = summary.get("n_auto_clear", sum(1 for f in findings if f.get("lane") == "AUTO_CLEAR"))
    n_tri = sum(1 for f in findings if f.get("lane") == "TRIAGE")
    n_info = sum(1 for f in findings if f.get("lane") == "INFO")
    lane_bits = [f"{n_auto} auto-cleared", f"{n_tri} to triage"] + ([f"{n_info} info"] if n_info else [])
    g.nodes.append(Node(
        id="lanes", col=5, row=0, kind="code", title="lanes",
        sub="autonomy earned per field", metrics=" · ".join(lane_bits),
        outcome=summary.get("document_lane", ""),
        tip="Agree and pass → auto-clear with zero human touch. Anything else is a typed finding.",
        href=f"{doc_id}/auto_clear.json"))

    tri_lines = [v for k, v in step.items() if k.startswith("triage:")]
    triage_rows = _load(d / "triage.json") or []
    n_drafted = sum(1 for t in triage_rows if t.get("triage"))
    if tri_lines or n_drafted:
        tri_cost = sum(l.get("cost_usd") or 0 for l in tri_lines) or breakdown.get("triage") or 0
        failed_tri = [l for l in tri_lines if l.get("outcome") in FAILED]
        g.nodes.append(Node(
            id="triage", col=5, row=1, kind="model", title="triage · desk query",
            sub=str(next((l.get("model") for l in tri_lines if l.get("model")), "claude-opus-5")),
            metrics=" · ".join(x for x in (f"{n_drafted or len(tri_lines)} drafted", _money(tri_cost)) if x),
            outcome="MALFORMED" if failed_tri else "OK",
            tip=("The only place a model writes prose: it explains a finding code already made and drafts "
                 "the query, given the finding and its citations, never the whole document."),
            href=f"{doc_id}/triage.json" if triage_rows else None))

    out_row = 2 if (tri_lines or n_drafted) else 1
    att_metrics = "not attested"
    if att.get("document_sha256"):
        keys = att.get("booking_terms_keys")
        n_keys = len(keys) if isinstance(keys, list) else (keys or "?")
        att_metrics = f"doc {str(att['document_sha256'])[:8]} · terms {str(att.get('booking_sha256') or '')[:8]} ({n_keys} fields)"
    top = [f"{k.lower().replace('_', ' ')} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:3]]
    g.nodes.append(Node(
        id="out", col=5, row=out_row, kind="output", title="findings + attestation",
        sub=" · ".join(top) if top else "no findings",
        metrics=att_metrics,
        outcome="MISMATCH" if counts.get("MISMATCH") else ("AUTO_CLEAR" if summary.get("document_lane") == "AUTO_CLEAR" else ""),
        tip=("The result is bound to the document hash and to the hash of the booking fields that affect the "
             "terms of the deal, so a fixing never disturbs it and an amendment expires it."),
        href=f"{doc_id}/summary.json"))

    # ---- edges: what actually flows ------------------------------------------------------------
    n_fields = len(merged) or 28
    if g.by_id("parse"):
        g.edges += [Edge("doc", "parse", f"{parse_meta.get('pages', '')} pages".strip()),
                    Edge("parse", "ex_gemini", "parsed markdown"), Edge("parse", "ex_claude", "parsed markdown")]
    else:
        g.edges += [Edge("doc", "ex_gemini", "text"), Edge("doc", "ex_claude", "text")]
    g.edges += [Edge("ex_gemini", "merge", f"{n_fields} fields"), Edge("ex_claude", "merge", f"{n_fields} fields")]
    g.edges.append(Edge("book_in", "lookup", "trade id"))
    g.edges.append(Edge("merge", "compare", "agreed values"))
    g.edges.append(Edge("lookup", "compare", f"{n_terms} booked terms" if n_terms else "no record"))
    if g.by_id("rel"):
        g.edges.append(Edge("merge", "rel", ""))
    if g.by_id("ref"):
        g.edges.append(Edge("meth", "ref", "rules"))
        g.edges.append(Edge("merge", "ref", "claims"))
    g.edges.append(Edge("compare", "lanes", f"{len(findings)} findings"))
    if g.by_id("rel"):
        g.edges.append(Edge("rel", "lanes", ""))
    if g.by_id("ref"):
        g.edges.append(Edge("ref", "lanes", ""))
    if g.by_id("triage"):
        g.edges.append(Edge("lanes", "triage", f"{n_tri} not clean"))
        g.edges.append(Edge("triage", "out", "drafted queries"))
    g.edges.append(Edge("lanes", "out", f"{n_auto} cleared"))

    used = sorted({n.col for n in g.nodes})
    remap = {c: i for i, c in enumerate(used)}
    for n in g.nodes:
        n.col = remap[n.col]

    spend = breakdown.get("extraction", summary.get("cost_usd"))
    g.caption = (f"{doc_id} · {summary.get('trade_id') or ''} · source {source} · "
                 f"{_money(spend) or '$0'} for the readings"
                 + (f" + {_money(breakdown.get('triage'))} for the desk queries" if breakdown.get("triage") else "")
                 + " · every box links to the artifact it produced")
    return g


# --------------------------------------------------------------------------------------------
# rendering


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _wrap(s: str, n: int) -> list[str]:
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines[:2]


def render_svg(g: Graph) -> str:
    """Fixed-column layout, hand-routed edges. Labels always sit in the gap to the right of their
    source node, never on top of a box; an edge that skips a column is dashed, because it is carrying
    something past a stage rather than into it (the booking record is the one that does this)."""
    cols = max((n.col for n in g.nodes), default=0) + 1
    rows = max((n.row for n in g.nodes), default=0) + 1
    width = M * 2 + cols * W + (cols - 1) * GX
    height = M * 2 + rows * H + (rows - 1) * GY + 46          # + caption and legend

    def pos(n: Node) -> tuple[float, float]:
        return M + n.col * (W + GX), M + n.row * (H + GY)

    # styles live inside the svg, scoped to .pgraph: an inline <svg> in an HTML page shares the
    # document's stylesheet, so unscoped rules here would leak onto the desk view itself.
    style = (f".pgraph text{{font-family:{SANS}}}"
             f".pgraph .t{{font-size:12.5px;font-weight:700;fill:{C['fg']}}}"
             f".pgraph .s{{font-size:10.5px;fill:{C['muted']}}}"
             f".pgraph .m{{font-size:10px;font-family:{MONO}}}"
             f".pgraph .e{{font-size:9.5px;fill:{C['muted']}}}"
             f".pgraph .b{{font-size:9px;font-weight:700}}"
             f".pgraph .k{{font-size:9.5px;fill:{C['muted']}}}"
             f".pgraph a{{cursor:pointer}}.pgraph a:hover rect{{stroke-width:2.2}}")
    parts = [
        f'<svg class="pgraph" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px" role="img" '
        f'aria-label="provenance graph for {_esc(g.doc_id)}">',
        f"<style>{style}</style>",
        f'<rect width="{width}" height="{height}" fill="{C["bg"]}" rx="6"/>',
        '<defs><marker id="pa" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
        f'orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="{C["line"]}"/></marker></defs>',
    ]

    # stagger labels that share a gap so two edges leaving the same node do not print over each other
    share: dict[tuple[str, int], list[Edge]] = {}
    for e in g.edges:
        s_, t_ = g.by_id(e.src), g.by_id(e.dst)
        if s_ and t_ and e.label and t_.col != s_.col:
            share.setdefault((e.src, s_.col), []).append(e)

    for e in g.edges:
        s_, t_ = g.by_id(e.src), g.by_id(e.dst)
        if not s_ or not t_:
            continue
        sx, sy = pos(s_); tx, ty = pos(t_)
        if t_.col == s_.col:
            # same stage, next row (lanes -> triage -> output): a short vertical connector, no label;
            # a label here would have to live in the 16 px row gap, where nothing is readable
            cx = sx + W / 2
            parts.append(f'<path d="M{cx} {sy + H} L{cx} {ty - 2}" fill="none" stroke="{C["line"]}" '
                         f'stroke-width="1.4" marker-end="url(#pa)"/>')
            continue
        x1, y1 = sx + W, sy + H / 2
        x2, y2 = tx, ty + H / 2
        skips = t_.col - s_.col > 1
        ctrl = x1 + (x2 - x1) * 0.45
        parts.append(f'<path d="M{x1} {y1} C{ctrl} {y1}, {ctrl} {y2}, {x2 - 2} {y2}" fill="none" '
                     f'stroke="{C["line"]}" stroke-width="1.4" marker-end="url(#pa)"'
                     + (' stroke-dasharray="4 3"' if skips else "") + "/>")
        if e.label:
            group = share.get((e.src, s_.col), [])
            i = group.index(e) if e in group else 0
            off = (i - (len(group) - 1) / 2) * 12
            lx, ly = x1 + GX / 2, y1 + off - 5
            label = e.label[:16]
            plate = len(label) * 5.1 + 6       # a plate, not a paint-order halo: WeasyPrint and older
            parts.append(f'<rect x="{lx - plate / 2:.0f}" y="{ly - 9:.0f}" width="{plate:.0f}" height="12" '
                         f'fill="{C["bg"]}" rx="2"/>')   # renderers ignore paint-order and would hide the text
            parts.append(f'<text class="e" x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle">{_esc(label)}</text>')

    for n in g.nodes:
        x, y = pos(n)
        stroke, fill = _tone(n.outcome)
        if n.kind == "input":
            stroke, fill = C["in"], C["inbg"]
        if n.kind == "code" and not n.outcome:
            stroke, fill = C["code"], C["codebg"]
        body = [f'<g><title>{_esc(n.tip or n.title)}</title>',
                f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>',
                f'<text class="t" x="{x + 11}" y="{y + 21}">{_esc(n.title[:26])}</text>']
        ty = y + 38
        for line in _wrap(n.sub, 28):
            body.append(f'<text class="s" x="{x + 11}" y="{ty}">{_esc(line)}</text>')
            ty += 13
        for line in _wrap(n.metrics, 24):
            body.append(f'<text class="m" x="{x + 11}" y="{ty}" fill="{stroke}">{_esc(line)}</text>')
            ty += 12
        if n.outcome in REUSED or n.outcome in FAILED:
            body.append(f'<text class="b" x="{x + W - 10}" y="{y + 20}" text-anchor="end" fill="{stroke}">{_esc(n.outcome)}</text>')
        body.append("</g>")
        box = "".join(body)
        parts.append(f'<a xlink:href="{_esc(n.href)}" href="{_esc(n.href)}" target="_blank">{box}</a>' if n.href else box)

    legend_y = height - 26
    parts.append(f'<text class="k" x="{M}" y="{legend_y}">{_esc(g.caption)}</text>')
    kx = M
    for label, colour in (("completed", C["ok"]), ("reused under an unchanged hash", C["reuse"]),
                          ("never completed", C["bad"]), ("code, no model", C["code"])):
        parts.append(f'<rect x="{kx}" y="{legend_y + 8}" width="9" height="9" rx="2" fill="{colour}"/>')
        parts.append(f'<text class="k" x="{kx + 13}" y="{legend_y + 16}">{_esc(label)}</text>')
        kx += 20 + len(label) * 5.4
    parts.append("</svg>")
    return "".join(parts)


def write(run_dir: Path, doc_id: str, golden_href: str | None = None) -> Path | None:
    """Write `<run>/<doc>/provenance.svg`. A failure here must never cost the page: the graph is a
    view of the run, not part of it, so the error is drawn instead of raised."""
    out = Path(run_dir) / doc_id / "provenance.svg"
    try:
        svg = render_svg(build(run_dir, doc_id, golden_href))
    except Exception as exc:  # noqa: BLE001
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 60" width="100%" role="img">'
               f'<rect width="560" height="60" fill="{C["badbg"]}" rx="6"/>'
               f'<text x="14" y="26" font-size="12" fill="{C["bad"]}">provenance graph unavailable for {_esc(doc_id)}</text>'
               f'<text x="14" y="44" font-size="10" fill="{C["bad"]}">{_esc(f"{type(exc).__name__}: {exc}"[:110])}</text></svg>')
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg)
        return out
    except OSError:
        return None


def write_all(run_dir: Path, golden_href: str | None = None) -> dict[str, str]:
    """Draw every document in the run. Returns doc_id -> svg markup, for inlining in a page."""
    run_dir = Path(run_dir)
    svgs: dict[str, str] = {}
    for d in sorted(p for p in run_dir.iterdir() if p.is_dir() and (p / "summary.json").exists()):
        p = write(run_dir, d.name, golden_href)
        if p:
            svgs[d.name] = p.read_text()
    return svgs
