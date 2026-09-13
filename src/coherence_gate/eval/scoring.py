"""Binary scoring against manifest.json (LLD §14, ADR-10). Counts and rates only; never an
average. Every rate is rendered with its n. Red numbers are printed red."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .. import normalize
from ..types import Family, FindingType, Lane

if TYPE_CHECKING:
    from ..pipeline import DocumentResult, RunContext

RED = "🔴"
GREEN = "🟢"


@dataclass
class Rate:
    hit: int
    n: int
    label: str
    must_be_full: bool = False   # red unless hit == n
    lower_is_better: bool = False

    @property
    def pct(self) -> float:
        return 0.0 if self.n == 0 else 100.0 * self.hit / self.n

    def render(self) -> str:
        s = f"{self.hit}/{self.n} ({self.pct:.1f}%)"
        if self.must_be_full:
            return f"{GREEN if self.hit == self.n else RED} {s}"
        if self.lower_is_better:
            return f"{GREEN if self.hit == 0 else RED} {s}"
        return f"{GREEN if self.hit == self.n else RED} {s}"


@dataclass
class EvalResult:
    run_id: str
    run_dir: Path
    catch_strict: Rate
    catch_field_only: Rate
    false_flag_fields: Rate
    false_flag_docs: Rate
    trap_resolved: Rate
    auto_clear_correctness: Rate
    agreement: Rate
    extraction_accuracy: dict[str, Rate]
    cost_total: float          # model cost attributed to documents (extraction + triage where run)
    cost_per_doc: float
    cost_min: float
    cost_max: float
    n_docs: int
    reference_cost: float = 0.0     # one-off methodology extraction (cached afterwards)
    cost_traced_total: float = 0.0  # every traced line of this run id
    planted_detail: list[dict] = field(default_factory=list)
    false_flag_detail: list[dict] = field(default_factory=list)
    auto_clear_violations: list[dict] = field(default_factory=list)
    models: list[dict] = field(default_factory=list)
    stub: bool = False
    source: str = "txt"
    field_accuracy: dict[str, dict[str, bool]] = field(default_factory=dict)  # family -> "doc:field" -> correct
    by_product: dict[str, dict] = field(default_factory=dict)  # product_type -> {docs, catch, planted, false_flags, clean_fields}
    reference_lane: dict | None = None  # CS4 results when the lane ran
    not_evaluable: dict[str, int] = field(default_factory=dict)  # reason -> count of checks that were NOT performed (never auto-cleared, never flagged)
    n_truth_absent: int = 0   # truth values that are ABSENT (agreement/accuracy count agreeing on absence)
    # family -> {"calls": n, "by_outcome": {outcome: n}, "docs": [...]} for extraction calls that never returned a
    # reading (API_ERROR / TIMEOUT / DEADLINE / REFUSAL). A billing or transport event lowers the accuracy number
    # exactly like a misread would; this is the line that says which one it was.
    never_completed: dict[str, dict] = field(default_factory=dict)
    resumed: dict | None = None   # {"prior_run", "reused": [...], "re_extracted": [...]} when `cg eval --resume` was used

    def summary(self) -> dict[str, Any]:
        r = lambda x: {"hit": x.hit, "n": x.n}  # noqa: E731
        return {"run_id": self.run_id, "stub": self.stub, "n_docs": self.n_docs,
                "catch_strict": r(self.catch_strict), "catch_field_only": r(self.catch_field_only),
                "false_flag_fields": r(self.false_flag_fields), "false_flag_docs": r(self.false_flag_docs),
                "trap_resolved": r(self.trap_resolved), "auto_clear_correctness": r(self.auto_clear_correctness),
                "agreement": r(self.agreement),
                "extraction_accuracy": {k: r(v) for k, v in self.extraction_accuracy.items()},
                "never_completed": self.never_completed, "resumed": self.resumed,
                "cost_total_usd": self.cost_total, "cost_per_doc_usd": self.cost_per_doc,
                "source": self.source, "field_accuracy": self.field_accuracy, "by_product": self.by_product,
                "reference_lane": self.reference_lane, "not_evaluable": self.not_evaluable, "n_truth_absent": self.n_truth_absent,
                "reference_cost_usd": self.reference_cost, "cost_traced_total_usd": self.cost_traced_total,
                "planted_detail": self.planted_detail, "false_flag_detail": self.false_flag_detail}


def _truth_equal(truth_val: Any, nf, schema=None) -> bool:
    if truth_val == "ABSENT":
        return bool(nf.absent) and not nf.malformed
    if nf.absent or nf.malformed:
        return False
    return normalize.values_equal(nf.value, _canon_truth(nf.key, truth_val, schema))


def _canon_truth(key: str, v: Any, schema=None) -> Any:
    """Truth files are canonical already; pass through the normalizer so Decimal/str forms agree."""
    from ..schema_loader import load_schema
    schema = schema or load_schema()
    try:
        return normalize.normalize_value(schema.spec(key), v)
    except normalize.NormalizeError:
        return v


def score(manifest: dict, results: dict[str, "DocumentResult"], ctx: "RunContext", golden: Path) -> EvalResult:
    docs = [d for d in manifest["documents"] if d["id"] in results]
    schema_of = {d["id"]: ctx.schemas[d.get("product_type", "note")] for d in docs}
    keys_of = {d["id"]: schema_of[d["id"]].comparison_keys for d in docs}          # extraction keys
    check_keys_of = {d["id"]: keys_of[d["id"]] + schema_of[d["id"]].relation_keys for d in docs}  # incl. rel:*
    planted = [(d["id"], p["field"], p["type"]) for d in docs for p in d["planted"]]
    traps = [(d["id"], t["field"]) for d in docs for t in d.get("traps", [])]
    clean_docs = [d["id"] for d in docs if d.get("clean_control")]
    excluded = {(doc, f) for doc, f, _ in planted} | set(traps)

    by_doc = {doc_id: {f.field: f for f in r.findings} for doc_id, r in results.items()}

    ptype = {d["id"]: d.get("product_type", "note") for d in docs}
    by_product: dict[str, dict] = {}
    for t_ in set(ptype.values()):
        by_product[t_] = {"docs": sum(1 for v in ptype.values() if v == t_), "planted": 0, "catch": 0, "clean_fields": 0, "false_flags": 0}

    # catch (strict + field-only), auto-clear correctness
    planted_detail, strict_hits, lenient_hits, violations = [], 0, 0, []
    for doc, fld, typ in planted:
        f = by_doc[doc].get(fld)
        reported = f.type if f else None
        strict = reported == typ
        lenient = f is not None and f.type is not FindingType.CLEAN
        strict_hits += strict
        lenient_hits += lenient
        by_product[ptype[doc]]["planted"] += 1
        by_product[ptype[doc]]["catch"] += int(strict)
        if f is not None and f.lane is Lane.AUTO_CLEAR:
            violations.append({"doc": doc, "field": fld, "expected": typ, "reported": reported})
        planted_detail.append({"doc": doc, "field": fld, "expected": typ, "reported": reported,
                               "strict": strict, "field_only": lenient, "detail": f.detail if f else "no finding"})

    # false flags on clean fields
    ff_detail, n_clean = [], 0
    not_evaluable: dict[str, int] = {}
    for doc in results:
        ref_keys = [f.field for f in results[doc].findings if f.field.startswith("ref:")]
        for k in check_keys_of[doc] + ref_keys:
            if (doc, k) in excluded:
                continue
            f = by_doc[doc].get(k)
            if f is not None and f.type is FindingType.NOT_EVALUABLE:
                key = f.detail.split(":")[0].split(" — ")[0][:60]
                not_evaluable[key] = not_evaluable.get(key, 0) + 1
                continue   # a check that was not performed is neither a clean field nor a flag
            n_clean += 1
            by_product[ptype[doc]]["clean_fields"] += 1
            if f is None or f.type is not FindingType.CLEAN:
                ff_detail.append({"doc": doc, "field": k, "type": f.type if f else "MISSING", "detail": f.detail if f else ""})
                by_product[ptype[doc]]["false_flags"] += 1
    ff_docs = [d for d in clean_docs if results[d].document_lane is not Lane.AUTO_CLEAR]

    trap_hits = sum(1 for doc, fld in traps if (f := by_doc[doc].get(fld)) and f.type is FindingType.CLEAN)

    # agreement + extraction accuracy
    agree = sum(1 for r in results.values() for m in r.merged.values() if m["agree"])
    acc: dict[str, int] = {str(Family.gemini): 0, str(Family.claude): 0}
    field_acc: dict[str, dict[str, bool]] = {fam: {} for fam in acc}
    for d in docs:
        truth = json.loads((golden / d["truth"]).read_text())
        r = results[d["id"]]
        for fam in acc:
            for k in keys_of[d["id"]]:
                ok = _truth_equal(truth.get(k, "ABSENT"), r.normalized[fam][k], schema_of[d["id"]])
                acc[fam] += ok
                field_acc[fam][f"{d['id']}:{k}"] = bool(ok)
    n_fields = sum(len(keys_of[d]) for d in results)
    n_truth_absent = sum(1 for d in docs for k in keys_of[d["id"]] if json.loads((golden / d["truth"]).read_text()).get(k, "ABSENT") == "ABSENT")

    # reference lane (CS4): planted REFERENCE_INCONSISTENT caught; deferred/default fields never flagged
    ref_planted = [(d_, f_, t_) for d_, f_, t_ in planted if t_ == "REFERENCE_INCONSISTENT"]
    ref_caught = sum(1 for d_, f_, t_ in ref_planted if (x := by_doc[d_].get(f_)) and x.type == t_)
    ref_findings = [f for r in results.values() for f in r.findings if f.field.startswith("ref:")]
    ref_ran = any(l["step"] == "reference_check" for l in ctx.tracer.lines)
    reference_lane = None
    if ref_ran or ref_planted:
        deferred_flags = sum(1 for f in ref_findings if f.type == FindingType.REFERENCE_INCONSISTENT and "deferred" in f.detail)
        reference_lane = {"ran": ref_ran, "catch": f"{ref_caught}/{len(ref_planted)}",
                          "checks": sum(1 for f in ref_findings if f.type != FindingType.NOT_EVALUABLE),
                          "flags": sum(1 for f in ref_findings if f.type == FindingType.REFERENCE_INCONSISTENT),
                          "deferred_false_flags": deferred_flags,
                          "not_evaluable": sum(1 for f in ref_findings if f.type == FindingType.NOT_EVALUABLE)}

    # calls that never produced a reading: the model was not asked (or did not answer), it did not read wrongly
    never: dict[str, dict] = {}
    for l in ctx.tracer.lines:
        if l["run_id"] != ctx.run_id or not l["step"].startswith("extract:") or l["doc_id"] not in results:
            continue
        if l["outcome"] in ("OK", "MALFORMED", "CACHED"):
            continue
        fam = l["step"].split(":", 1)[1]
        e = never.setdefault(fam, {"calls": 0, "by_outcome": {}, "docs": []})
        e["calls"] += 1
        e["by_outcome"][l["outcome"]] = e["by_outcome"].get(l["outcome"], 0) + 1
        if l["doc_id"] not in e["docs"]:
            e["docs"].append(l["doc_id"])

    costs = [r.cost_usd for r in results.values()]
    total = round(sum(costs), 4)
    ref_cost = round(sum(l["cost_usd"] for l in ctx.tracer.lines if l["doc_id"] == "REF"), 4)
    traced_total = round(sum(l["cost_usd"] for l in ctx.tracer.lines if l["run_id"] == ctx.run_id), 4)
    models = [{"family": p.family, "model": p.model, "pinned": p.pinned,
               "price_in": p.price_in, "price_out": p.price_out} for p in ctx.config.pins]
    return EvalResult(
        run_id=ctx.run_id, run_dir=ctx.out_dir,
        catch_strict=Rate(strict_hits, len(planted), "catch_rate (doc+field+type)"),
        catch_field_only=Rate(lenient_hits, len(planted), "catch_rate_field_only (diagnostic)"),
        false_flag_fields=Rate(len(ff_detail), n_clean, "false_flag_rate (clean fields flagged)", lower_is_better=True),
        false_flag_docs=Rate(len(ff_docs), len(clean_docs), "clean documents NOT auto-cleared", lower_is_better=True),
        trap_resolved=Rate(trap_hits, len(traps), "G09 normalizer trap resolved as CLEAN", must_be_full=True),
        auto_clear_correctness=Rate(len(planted) - len(violations), len(planted), "auto_clear_correctness (planted never auto-cleared)", must_be_full=True),
        agreement=Rate(agree, n_fields, "cross-family agreement (fields)"),
        extraction_accuracy={fam: Rate(v, n_fields, f"extraction_accuracy ({fam}) vs truth") for fam, v in acc.items()},
        cost_total=total, cost_per_doc=round(total / max(len(costs), 1), 4), reference_cost=ref_cost, cost_traced_total=traced_total,
        cost_min=round(min(costs, default=0), 4), cost_max=round(max(costs, default=0), 4),
        n_docs=len(results), planted_detail=planted_detail, false_flag_detail=ff_detail,
        auto_clear_violations=violations, models=models, source=ctx.source, field_accuracy=field_acc, by_product=by_product,
        reference_lane=reference_lane, not_evaluable=not_evaluable, n_truth_absent=n_truth_absent, never_completed=never,
        stub=all(l.get("detail") and "stub" in str(l.get("detail")) for l in ctx.tracer.lines if l["step"].startswith("extract:")),
    )


def _sweep_section() -> list[str]:
    """Effort sweep from frozen run summaries listed in config/report.yaml (CS6)."""
    import yaml
    from ..config import ROOT
    cfg_path = ROOT / "config" / "report.yaml"
    if not cfg_path.exists():
        return []
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    sw = cfg.get("sweep") or {}
    rows = []
    for r in sw.get("runs", []):
        p = ROOT / r["summary"]
        if not p.exists():
            continue
        sm = json.loads(p.read_text())
        rows.append((r["label"], sm, r.get("note", "")))
    if not rows:
        return []
    out = [f"## 6. {sw.get('title', 'Effort sweep')}", "", "Measured on the v0.1 golden set (12 documents, 9 planted findings), not on the current set; the mechanism is identical.", "",
           "| setting | run | strict catch | false flags | agreement | auto-clear ok | cost/doc | note |", "|---|---|---|---|---|---|---|---|"]
    for label, sm, note in rows:
        r = lambda k: f"{sm[k]['hit']}/{sm[k]['n']}"  # noqa: E731
        out.append(f"| {label} | {sm['run_id']} | {r('catch_strict')} | {r('false_flag_fields')} | {r('agreement')} | {r('auto_clear_correctness')} | ${sm['cost_per_doc_usd']:.3f} | {note} |")
    out.append("")
    return out


def render_markdown(ev: EvalResult) -> str:
    """eval_report v2 (CS6): headline strict catch with the field-level diagnostic beneath, false-flag
    rate at equal prominence, auto-clear correctness in red if not 100%, agreement, per-product
    breakdown, parse-tax section (appended by the ablation command), reference lane, effort sweep,
    cost per document and per book, honest ceiling v2."""
    n_planted = ev.catch_strict.n
    n_book = ev.n_docs
    lines = [f"# eval_report.md — run {ev.run_id}" + (" (STUB PIPELINE — no model calls)" if ev.stub else "")
             + f" — source: {ev.source}", "",
             "Every number below is a count over a stated n, from this one run, with no retries. Red means the claim it "
             "supports does not hold on this run.", ""]
    if ev.resumed:
        rs = ev.resumed
        lines += [f"**Resumed from `{rs['prior_run']}`.** {len(rs['reused'])} document(s) reused the extractions stored there "
                  f"(both families' calls completed; extractions attested to the document hash; deterministic steps re-run here): "
                  f"{', '.join(rs['reused']) or '—'}. {len(rs['re_extracted'])} document(s) extracted again because a call never "
                  f"completed in the prior run: {', '.join(rs['re_extracted']) or '—'}. Per-document cost includes the reused "
                  f"extraction's cost; the trace of the prior run holds those calls.", ""]
    # 1. headline
    lines += ["## 1. Headline: did the gate catch what was planted, and did it flag what was clean?", "",
              "| metric | result | n |", "|---|---|---|",
              f"| **catch_rate (right field AND right finding type)** | {ev.catch_strict.render()} | {ev.catch_strict.n} |",
              f"| catch_rate_field_only (diagnostic: any non-clean finding on the planted field) | {ev.catch_field_only.render()} | {ev.catch_field_only.n} |",
              f"| **false_flag_rate (clean fields that were flagged)** | {ev.false_flag_fields.render()} | {ev.false_flag_fields.n} |",
              f"| clean control documents NOT auto-cleared | {ev.false_flag_docs.render()} | {ev.false_flag_docs.n} |",
              f"| **auto_clear_correctness (nothing planted was auto-cleared; must be 100%)** | {ev.auto_clear_correctness.render()} | {ev.auto_clear_correctness.n} |",
              f"| cross-family agreement (fields where both families read the same value, or both declared it absent; {ev.n_truth_absent} of {ev.agreement.n} truth values are absent) | {ev.agreement.render()} | {ev.agreement.n} |",
              f"| G09 normalizer trap resolved as CLEAN (per-quarter vs per-annum) | {ev.trap_resolved.render()} | {ev.trap_resolved.n} |", ""]
    if ev.auto_clear_correctness.hit != ev.auto_clear_correctness.n:
        lines += [f"{RED} **auto_clear_correctness is not 100%: the tiered-autonomy claim does not hold on this run.** "
                  f"Violations: {ev.auto_clear_violations}", ""]
    if ev.not_evaluable:
        n_ne = sum(ev.not_evaluable.values())
        lines += [f"**Checks not performed ({n_ne}), excluded from every rate above** — a check the gate could not perform is neither a clean field nor a flag; it is listed, never auto-cleared:", ""]
        lines += [f"- {k}: {v}" for k, v in sorted(ev.not_evaluable.items(), key=lambda kv: -kv[1])] + [""]
    # 2. extraction accuracy
    lines += ["## 2. Extraction accuracy per family (vs the golden truth files; agreeing on absence counts, see n absent above)", "",
              "| family | correct fields | n | calls that never completed (billing / transport / deadline / refusal) |", "|---|---|---|---|"]
    for fam, r in ev.extraction_accuracy.items():
        nc = ev.never_completed.get(fam)
        why = "0" if not nc else (f"{nc['calls']} on {', '.join(nc['docs'])}: " + ", ".join(f"{k} ×{v}" for k, v in nc["by_outcome"].items()))
        lines.append(f"| {fam} | {r.render()} | {r.n} | {why} |")
    lines.append("")
    if ev.never_completed:
        lines += ["A call that never completed makes every field of that document MALFORMED for that family, which lowers the accuracy "
                  "number exactly like a misread would. The last column says which it was, so a billing, quota or transport event is "
                  "read as such and not debugged as a model or parser regression (the trace line carries the provider's message).", ""]
    # 3. per product type
    if ev.by_product:
        lines += ["## 3. Per product type", "", "| product | documents | planted | strict catch | clean fields | false flags |", "|---|---|---|---|---|---|"]
        for pt, b in sorted(ev.by_product.items()):
            lines.append(f"| {pt} | {b['docs']} | {b['planted']} | {b['catch']}/{b['planted']} | {b['clean_fields']} | {b['false_flags']}/{b['clean_fields']} |")
        lines.append("")
    # 4. parse tax placeholder (the ablation command appends the real section)
    lines += ["## 4. Parse tax", "",
              ("Source for this run: parsed PDF. Run `cg ablation --txt-run <txt run> --pdf-run <this run>` to append the "
               "text-vs-parsed comparison here." if ev.source == "pdf" else
               "Source for this run: canonical text (no parsing). This run is the ablation baseline; the parse-tax table lives in the paired pdf run."), ""]
    # 5. reference lane
    lines += ["## 5. Reference lane (term sheet claims vs the Bloomberg Versa methodology)", ""]
    if ev.reference_lane:
        rl = ev.reference_lane
        lines += ["| metric | result |", "|---|---|",
                  f"| lane ran (methodology parsed + extracted by both families, merged by code) | {'yes' if rl['ran'] else 'NO — planted reference cases scored as misses'} |",
                  f"| planted reference incoherences caught (right field, type REFERENCE_INCONSISTENT) | {rl['catch']} |",
                  f"| reference checks performed (documents with an Underlying Index section × mapped rules) | {rl['checks']} |",
                  f"| reference flags raised | {rl['flags']} |",
                  f"| flags on parameters the methodology defers or merely defaults (must be 0) | {GREEN if rl['deferred_false_flags'] == 0 else RED} {rl['deferred_false_flags']} |",
                  f"| checks not evaluable (families disagreed on the rule or the claim) | {rl['not_evaluable']} |", "",
                  "A parameter the methodology defers to the index-specific document (e.g. Volatility Target) is reported as "
                  "`deferred`, never as a flag; the term sheet's value is checked against the booking's static data instead.", ""]
    else:
        lines += ["Not run in this release: the reference lane is Change Set 4 (docs/V2-CHANGES.md) and is reported here when built.", ""]
    # 6. sweep
    lines += _sweep_section()
    # 7. cost
    lines += ["## 7. Cost", "", "| scope | USD |", "|---|---|",
              f"| per document (both extractions + triage where run, traced tokens × pinned prices) | ${ev.cost_per_doc:.4f} (min ${ev.cost_min:.4f}, max ${ev.cost_max:.4f}) |",
              f"| per book of {n_book} documents (documents only) | ${ev.cost_total:.4f} |",
              f"| methodology (reference) extraction, once per methodology version, cached afterwards | ${ev.reference_cost:.4f} |",
              f"| everything traced under this run id | ${ev.cost_traced_total:.4f} |",
              "| parsing | not reported by the vendor API; parse latency is in the trace |", ""]
    # 8. models
    lines += ["## 8. Models (pinned)", "", "| family | model | pinned | $/1M in | $/1M out |", "|---|---|---|---|---|"]
    lines += [f"| {m['family']} | {m['model']} | {m['pinned']} | {m['price_in']} | {m['price_out']} |" for m in ev.models]
    # 9. detail
    lines += ["", "## 9. Planted findings (mutants)", "", "| doc | field | expected | reported | strict | field-only | detail |", "|---|---|---|---|---|---|---|"]
    for p in ev.planted_detail:
        lines.append(f"| {p['doc']} | {p['field']} | {p['expected']} | {p['reported']} | {GREEN if p['strict'] else RED} | {GREEN if p['field_only'] else RED} | {str(p['detail'])[:140]} |")
    lines += ["", f"## 10. False flags on clean fields ({len(ev.false_flag_detail)})", ""]
    if ev.false_flag_detail:
        lines += ["| doc | field | type | detail |", "|---|---|---|---|"]
        lines += [f"| {f['doc']} | {f['field']} | {f['type']} | {str(f['detail'])[:120]} |" for f in ev.false_flag_detail[:60]]
        if len(ev.false_flag_detail) > 60:
            lines.append(f"| … | {len(ev.false_flag_detail) - 60} more | | |")
    else:
        lines.append("none")
    # 11. ceiling
    lines += ["", "## 11. Honest ceiling", "",
              f"- n = {ev.n_docs} synthetic documents, {n_planted} planted findings plus {ev.trap_resolved.n} normalizer trap, "
              f"{ev.false_flag_docs.n} clean controls. **Directional, not statistically significant.**",
              "- Documents are synthetic, generated from one parameter table through four layout families in one house style; phrasing is machine-uniform. Real desk paper has more layouts, scans, multi-page annexes and hand edits.",
              "- One prompt per extractor family; no prompt ensemble. One run per number: no retries, no reruns, no best-of.",
              "- The eval can only see error classes it plants. Unplanted classes (wrong observation-date count, swapped issuer/guarantor, a coupon barrier read as a knock-in) are invisible to it unless they happen to hit a planted field.",
              "- The triage agent sees only the finding, its citations and the booking field; it cannot exculpate a finding using an unflagged clause elsewhere in the document.",
              "- Parsing is single-sourced (one vendor, one mode) behind one interface; the local fallback exists but its parse tax is not measured here.",
              "- Field-level false-flag denominator counts every non-planted comparison key on every document, including fields absent in both term sheet and booking.",
              f"- Cost is computed from traced tokens × pinned list prices ({'no model calls in this run' if ev.stub else 'current list prices'}); parsing cost is not reported by the vendor.",
              ""]
    return "\n".join(lines)
