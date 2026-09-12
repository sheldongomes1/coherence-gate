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
    cost_total: float
    cost_per_doc: float
    cost_min: float
    cost_max: float
    n_docs: int
    planted_detail: list[dict] = field(default_factory=list)
    false_flag_detail: list[dict] = field(default_factory=list)
    auto_clear_violations: list[dict] = field(default_factory=list)
    models: list[dict] = field(default_factory=list)
    stub: bool = False
    source: str = "txt"
    field_accuracy: dict[str, dict[str, bool]] = field(default_factory=dict)  # family -> "doc:field" -> correct

    def summary(self) -> dict[str, Any]:
        r = lambda x: {"hit": x.hit, "n": x.n}  # noqa: E731
        return {"run_id": self.run_id, "stub": self.stub, "n_docs": self.n_docs,
                "catch_strict": r(self.catch_strict), "catch_field_only": r(self.catch_field_only),
                "false_flag_fields": r(self.false_flag_fields), "false_flag_docs": r(self.false_flag_docs),
                "trap_resolved": r(self.trap_resolved), "auto_clear_correctness": r(self.auto_clear_correctness),
                "agreement": r(self.agreement),
                "extraction_accuracy": {k: r(v) for k, v in self.extraction_accuracy.items()},
                "cost_total_usd": self.cost_total, "cost_per_doc_usd": self.cost_per_doc,
                "source": self.source, "field_accuracy": self.field_accuracy,
                "planted_detail": self.planted_detail, "false_flag_detail": self.false_flag_detail}


def _truth_equal(truth_val: Any, nf) -> bool:
    if truth_val == "ABSENT":
        return bool(nf.absent) and not nf.malformed
    if nf.absent or nf.malformed:
        return False
    return normalize.values_equal(nf.value, _canon_truth(nf.key, truth_val))


def _canon_truth(key: str, v: Any) -> Any:
    """Truth files are canonical already; pass through the normalizer so Decimal/str forms agree."""
    from ..schema_loader import load_schema
    try:
        return normalize.normalize_value(load_schema().spec(key), v)
    except normalize.NormalizeError:
        return v


def score(manifest: dict, results: dict[str, "DocumentResult"], ctx: "RunContext", golden: Path) -> EvalResult:
    keys = ctx.schema.comparison_keys
    docs = [d for d in manifest["documents"] if d["id"] in results]
    planted = [(d["id"], p["field"], p["type"]) for d in docs for p in d["planted"]]
    traps = [(d["id"], t["field"]) for d in docs for t in d.get("traps", [])]
    clean_docs = [d["id"] for d in docs if d.get("clean_control")]
    excluded = {(doc, f) for doc, f, _ in planted} | set(traps)

    by_doc = {doc_id: {f.field: f for f in r.findings} for doc_id, r in results.items()}

    # catch (strict + field-only), auto-clear correctness
    planted_detail, strict_hits, lenient_hits, violations = [], 0, 0, []
    for doc, fld, typ in planted:
        f = by_doc[doc].get(fld)
        reported = f.type if f else None
        strict = reported == typ
        lenient = f is not None and f.type is not FindingType.CLEAN
        strict_hits += strict
        lenient_hits += lenient
        if f is not None and f.lane is Lane.AUTO_CLEAR:
            violations.append({"doc": doc, "field": fld, "expected": typ, "reported": reported})
        planted_detail.append({"doc": doc, "field": fld, "expected": typ, "reported": reported,
                               "strict": strict, "field_only": lenient, "detail": f.detail if f else "no finding"})

    # false flags on clean fields
    ff_detail, n_clean = [], 0
    for doc in results:
        for k in keys:
            if (doc, k) in excluded:
                continue
            n_clean += 1
            f = by_doc[doc].get(k)
            if f is None or f.type is not FindingType.CLEAN:
                ff_detail.append({"doc": doc, "field": k, "type": f.type if f else "MISSING", "detail": f.detail if f else ""})
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
            for k in keys:
                ok = _truth_equal(truth.get(k, "ABSENT"), r.normalized[fam][k])
                acc[fam] += ok
                field_acc[fam][f"{d['id']}:{k}"] = bool(ok)
    n_fields = len(results) * len(keys)

    costs = [r.cost_usd for r in results.values()]
    total = round(sum(costs), 4)
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
        cost_total=total, cost_per_doc=round(total / max(len(costs), 1), 4),
        cost_min=round(min(costs, default=0), 4), cost_max=round(max(costs, default=0), 4),
        n_docs=len(results), planted_detail=planted_detail, false_flag_detail=ff_detail,
        auto_clear_violations=violations, models=models, source=ctx.source, field_accuracy=field_acc,
        stub=all(l.get("detail") and "stub" in str(l.get("detail")) for l in ctx.tracer.lines if l["step"].startswith("extract:")),
    )


def render_markdown(ev: EvalResult) -> str:
    n_planted = ev.catch_strict.n
    lines = [f"# eval_report.md — run {ev.run_id}" + (" (STUB PIPELINE — no model calls)" if ev.stub else "")
             + f" — source: {ev.source}", ""]
    lines += ["## Results", "", "| metric | result | n |", "|---|---|---|"]
    for r in (ev.catch_strict, ev.catch_field_only, ev.false_flag_fields, ev.false_flag_docs, ev.trap_resolved,
              ev.auto_clear_correctness, ev.agreement, *ev.extraction_accuracy.values()):
        lines.append(f"| {r.label} | {r.render()} | {r.n} |")
    lines.append(f"| cost per document (USD) | ${ev.cost_per_doc:.4f} (min ${ev.cost_min:.4f}, max ${ev.cost_max:.4f}, total ${ev.cost_total:.4f}) | {ev.n_docs} |")
    lines.append("")
    if ev.auto_clear_correctness.hit != ev.auto_clear_correctness.n:
        lines += [f"{RED} **auto_clear_correctness is not 100%: the tiered-autonomy claim does not hold on this run.** "
                  f"Violations: {ev.auto_clear_violations}", ""]
    lines += ["## Models", "", "| family | model | pinned | $/1M in | $/1M out |", "|---|---|---|---|---|"]
    lines += [f"| {m['family']} | {m['model']} | {m['pinned']} | {m['price_in']} | {m['price_out']} |" for m in ev.models]
    lines += ["", "## Planted findings (mutants)", "", "| doc | field | expected | reported | strict | field-only | detail |", "|---|---|---|---|---|---|---|"]
    for p in ev.planted_detail:
        lines.append(f"| {p['doc']} | {p['field']} | {p['expected']} | {p['reported']} | {GREEN if p['strict'] else RED} | {GREEN if p['field_only'] else RED} | {p['detail']} |")
    lines += ["", f"## False flags on clean fields ({len(ev.false_flag_detail)})", ""]
    if ev.false_flag_detail:
        lines += ["| doc | field | type | detail |", "|---|---|---|---|"]
        lines += [f"| {f['doc']} | {f['field']} | {f['type']} | {str(f['detail'])[:120]} |" for f in ev.false_flag_detail[:60]]
        if len(ev.false_flag_detail) > 60:
            lines.append(f"| … | {len(ev.false_flag_detail) - 60} more | | |")
    else:
        lines.append("none")
    lines += ["", "## Honest ceiling", "",
              f"- n = {ev.n_docs} synthetic documents, {n_planted} planted findings plus {ev.trap_resolved.n} normalizer trap, "
              f"{ev.false_flag_docs.n} clean controls. **Directional, not statistically significant.**",
              "- Documents are synthetic and generated from parameters across 4 layout families; real desk paper has more layouts, OCR noise and multi-page annexes.",
              "- One prompt per extractor family; no prompt ensemble. One run per number: no retries, no reruns, no best-of.",
              "- The eval can only see error classes it plants. Unplanted classes (e.g. wrong observation-date count, swapped issuer/guarantor) are invisible to it.",
              "- Field-level false-flag denominator counts every non-planted comparison key on every document, including fields that are absent in both term sheet and booking.",
              f"- Cost is computed from traced tokens × pinned prices in config/models.yaml ({'no model calls in this run' if ev.stub else 'current list prices'}).",
              ""]
    return "\n".join(lines)
