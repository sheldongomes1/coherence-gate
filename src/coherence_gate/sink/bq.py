"""BigQuery sink for `trace.jsonl`: the run's own record, queryable across runs.

Why this exists: the trace answers "what did this run do" perfectly well as a file, and the
provenance graph (ADR-33) draws one document from it. The questions it cannot answer from a file are
the ones that only appear across runs and over time — how a family's disagreement rate on one field
moves after a model pin changes, what share of calls never completed last month, what the gate cost
per document by product. Those are the drift signals, and they are SQL.

Why no client library: `google-cloud-bigquery` is another dependency whose transitive pins would move
the demo image's floor (the same measurement that kept ADK optional, ADR-34). The `bq` CLI ships with
the gcloud SDK that already deploys this service, so the sink writes newline-delimited JSON and a
schema and calls `bq load`. Nothing here imports a cloud library, so `cg trace export --dry-run`
works on a machine with no cloud access at all.

The table is partitioned by day and clustered by run and step, because every question above filters
on a run or a step first.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# BigQuery column types for a trace line. `detail` and `otel` stay JSON strings: they are
# free-shaped by design (a parse detail is not a triage detail) and BigQuery's JSON functions
# read them fine, whereas a fixed schema for them would break the first time a step adds a field.
SCHEMA = [
    {"name": "ts", "type": "TIMESTAMP", "mode": "REQUIRED"},
    {"name": "run_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "doc_id", "type": "STRING"},
    {"name": "step", "type": "STRING", "mode": "REQUIRED"},
    {"name": "family", "type": "STRING"},          # derived: extract:gemini -> gemini
    {"name": "model", "type": "STRING"},
    {"name": "model_version", "type": "STRING"},
    {"name": "prompt_tokens", "type": "INTEGER"},
    {"name": "output_tokens", "type": "INTEGER"},
    {"name": "latency_ms", "type": "INTEGER"},
    {"name": "cost_usd", "type": "NUMERIC"},
    {"name": "outcome", "type": "STRING", "mode": "REQUIRED"},
    {"name": "completed", "type": "BOOLEAN", "mode": "REQUIRED"},   # derived: the model answered at all
    {"name": "seq", "type": "INTEGER"},
    {"name": "detail", "type": "JSON"},
    {"name": "otel", "type": "JSON"},
]

# an extraction call that produced no reading: the distinction the eval report also prints (ADR-30 era)
NOT_COMPLETED = {"API_ERROR", "TIMEOUT", "REFUSAL", "DEADLINE"}

# rows that are not about a document: the run's config line and the one-off methodology extraction
NON_DOCUMENT = "('-', 'REF', '')"

VIEWS = {
    # what a run cost, split the way the report splits it. A resumed run (ADR-31) shows only what IT
    # paid: the reused readings were bought in the prior run and are CACHED here, at zero.
    "v_cost_by_run": """
        SELECT run_id,
               MIN(ts) AS started,
               COUNT(DISTINCT IF(doc_id NOT IN {nondoc}, doc_id, NULL)) AS documents,
               COUNTIF(STARTS_WITH(step, 'extract:') AND outcome = 'CACHED') AS readings_reused,
               ROUND(SUM(IF(STARTS_WITH(step, 'extract:'), cost_usd, 0)), 4) AS readings_usd,
               ROUND(SUM(IF(STARTS_WITH(step, 'triage:'), cost_usd, 0)), 4) AS desk_queries_usd,
               ROUND(SUM(cost_usd), 4) AS total_usd
        FROM `{table}` GROUP BY run_id ORDER BY started DESC""",
    # the line that tells a billing or transport event apart from a model getting worse
    "v_never_completed": """
        SELECT run_id, family, outcome, COUNT(*) AS calls, ARRAY_AGG(DISTINCT doc_id IGNORE NULLS) AS documents
        FROM `{table}`
        WHERE STARTS_WITH(step, 'extract:') AND NOT completed
        GROUP BY run_id, family, outcome ORDER BY run_id DESC""",
    # per-family latency and thinking volume: the effort sweep asked continuously instead of once.
    # CACHED calls are excluded — a reused reading has no latency and would drag every percentile to zero.
    "v_family_profile": """
        SELECT run_id, family,
               COUNTIF(outcome != 'CACHED') AS provider_calls,
               COUNTIF(outcome = 'CACHED') AS reused,
               APPROX_QUANTILES(IF(outcome != 'CACHED', latency_ms, NULL), 100)[OFFSET(50)] AS p50_ms,
               APPROX_QUANTILES(IF(outcome != 'CACHED', latency_ms, NULL), 100)[OFFSET(95)] AS p95_ms,
               SUM(output_tokens) AS output_tokens, ROUND(SUM(cost_usd), 4) AS cost_usd
        FROM `{table}` WHERE STARTS_WITH(step, 'extract:') AND completed
        GROUP BY run_id, family ORDER BY run_id DESC, family""",
}


@dataclass
class LoadPlan:
    """What would be sent, and the commands that would send it. Printable without cloud access."""
    rows: int
    run_ids: list[str]
    ndjson: Path
    schema: Path
    table: str
    commands: list[list[str]]


def _row(line: dict) -> dict:
    step = line.get("step", "")
    outcome = line.get("outcome", "")
    fam = step.split(":", 1)[1] if step.startswith("extract:") and ":" in step else None
    return {
        "ts": line.get("ts"),
        "run_id": line.get("run_id"),
        "doc_id": line.get("doc_id"),
        "step": step,
        "family": fam,
        "model": line.get("model"),
        "model_version": line.get("model_version"),
        "prompt_tokens": line.get("prompt_tokens") or 0,
        "output_tokens": line.get("output_tokens") or 0,
        "latency_ms": line.get("latency_ms") or 0,
        "cost_usd": line.get("cost_usd") or 0,
        "outcome": outcome,
        "completed": outcome not in NOT_COMPLETED,
        "seq": line.get("seq"),
        "detail": json.dumps(line.get("detail"), default=str) if line.get("detail") is not None else None,
        "otel": json.dumps(line.get("otel"), default=str) if line.get("otel") is not None else None,
    }


def prepare(run_dir: Path, project: str, dataset: str, table: str = "trace",
            out_dir: Path | None = None) -> LoadPlan:
    """Convert one run's trace into the rows and the exact `bq` commands that would load them."""
    run_dir = Path(run_dir)
    trace = run_dir / "trace.jsonl"
    if not trace.exists():
        raise FileNotFoundError(f"no trace.jsonl in {run_dir}")
    rows, run_ids = [], []
    for line in trace.read_text().splitlines():
        if not line.strip():
            continue
        r = _row(json.loads(line))
        if not r["ts"] or not r["run_id"]:
            continue          # a line without a timestamp or a run is not evidence of anything
        rows.append(r)
        if r["run_id"] not in run_ids:
            run_ids.append(r["run_id"])

    # staging goes to a temp directory by default: a frozen run is evidence, and an export must not
    # add files to it (the same rule the provenance graph follows, ADR-33)
    out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="cg-bq-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    ndjson = out_dir / "trace.bq.ndjson"
    ndjson.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))
    schema_path = out_dir / "trace.bq.schema.json"
    schema_path.write_text(json.dumps(SCHEMA, indent=2))

    fq = f"{project}:{dataset}.{table}"
    cmds = [
        ["bq", "--project_id", project, "mk", "--dataset", "--description",
         "Coherence Gate model-call traces (one row per step of one document in one run)", f"{project}:{dataset}"],
        ["bq", "--project_id", project, "mk", "--table",
         "--time_partitioning_field", "ts", "--time_partitioning_type", "DAY",
         "--clustering_fields", "run_id,step,doc_id", fq, str(schema_path)],
        ["bq", "--project_id", project, "load", "--source_format", "NEWLINE_DELIMITED_JSON",
         fq, str(ndjson), str(schema_path)],
    ]
    return LoadPlan(rows=len(rows), run_ids=run_ids, ndjson=ndjson, schema=schema_path,
                    table=f"{project}.{dataset}.{table}", commands=cmds)


def _run(cmd: list[str], allow_exists: bool = False) -> tuple[bool, str]:
    if not shutil.which("bq"):
        return False, "the bq CLI is not on PATH (it ships with the gcloud SDK)"
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if p.returncode == 0:
        return True, out
    if allow_exists and "already exists" in out.lower():
        return True, "already exists"
    return False, out


def export_run(run_dir: Path, project: str, dataset: str, table: str = "trace",
               replace: bool = False, out_dir: Path | None = None) -> dict:
    """Load one run's trace into BigQuery. Idempotent: a run already present is skipped unless
    `replace`, because loading the same run twice would double every cost figure derived from it."""
    plan = prepare(run_dir, project, dataset, table, out_dir)
    fq = f"{project}:{dataset}.{table}"
    result: dict = {"table": plan.table, "rows": plan.rows, "run_ids": plan.run_ids, "steps": []}

    ok, msg = _run(plan.commands[0], allow_exists=True); result["steps"].append(("dataset", ok, msg))
    if not ok:
        return {**result, "loaded": False}
    ok, msg = _run(plan.commands[1], allow_exists=True); result["steps"].append(("table", ok, msg))
    if not ok:
        return {**result, "loaded": False}

    quoted = ", ".join(f"'{r}'" for r in plan.run_ids)
    present = 0
    ok, msg = _run(["bq", "--project_id", project, "--format", "json", "query", "--nouse_legacy_sql",
                    f"SELECT COUNT(*) AS n FROM `{project}.{dataset}.{table}` WHERE run_id IN ({quoted})"])
    if ok and msg:
        try:
            present = int(json.loads(msg)[0]["n"])
        except (ValueError, KeyError, IndexError):
            present = 0
    result["already_present"] = present
    if present and not replace:
        return {**result, "loaded": False, "skipped": "run already loaded; pass replace=True to reload"}
    if present and replace:
        ok, msg = _run(["bq", "--project_id", project, "query", "--nouse_legacy_sql",
                        f"DELETE FROM `{project}.{dataset}.{table}` WHERE run_id IN ({quoted})"])
        result["steps"].append(("delete_existing", ok, msg))

    ok, msg = _run(plan.commands[2]); result["steps"].append(("load", ok, msg))
    result["loaded"] = ok
    if ok:
        for name, sql in VIEWS.items():
            # CREATE OR REPLACE, not `bq mk --force --view`: mk reports success and leaves an existing
            # view's definition untouched, so a changed view would silently keep answering the old way
            body = sql.format(table=f"{project}.{dataset}.{table}", nondoc=NON_DOCUMENT)
            v_ok, v_msg = _run(["bq", "--project_id", project, "query", "--nouse_legacy_sql",
                                f"CREATE OR REPLACE VIEW `{project}.{dataset}.{name}` AS {body}"])
            result["steps"].append((f"view:{name}", v_ok, v_msg.splitlines()[-1] if v_msg else "replaced"))
    return result
