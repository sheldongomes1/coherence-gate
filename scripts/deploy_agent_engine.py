#!/usr/bin/env python
"""Deploy the ADK app (ADR-34) to Vertex AI Agent Engine, or check that it could be.

    uv run python scripts/deploy_agent_engine.py                 # preflight only, no cloud writes
    uv run python scripts/deploy_agent_engine.py --deploy        # creates a billable resource

Preflight is the useful part most days: it checks the things that actually fail (auth, project, APIs,
a staging bucket, the agent tree building, the requirement set) and prints the exact call it would
make. Deployment is behind an explicit flag because an Agent Engine instance is a long-lived,
billable resource, and because `make deploy-service` on Cloud Run is what serves the demo.

What Agent Engine buys over the Cloud Run service: the runtime hosts the agent loop and the session
store, and the OTel-shaped spans the tracer already emits land in Cloud Trace without a second
instrumentation. What it does not change: the decision. The same `pipeline._complete` runs there,
and `tests/test_adk_wrapper.py` is what says so.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Pins the deployed image needs. Kept in one place and derived from the project's own lock rather
# than retyped, so the agent runs the versions the eval measured.
REQUIREMENT_NAMES = ["google-adk", "google-genai", "anthropic", "pydantic", "jinja2", "mcp",
                     "pyyaml", "beautifulsoup4", "pypdf", "mixedbread", "python-dotenv"]


def _sh(cmd: list[str]) -> tuple[bool, str]:
    if not shutil.which(cmd[0]):
        return False, f"{cmd[0]} is not on PATH"
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def locked_versions() -> dict[str, str]:
    """Read the pins out of uv.lock so the deployed agent matches the evaluated one."""
    lock = (ROOT / "uv.lock").read_text()
    out: dict[str, str] = {}
    name = None
    for line in lock.splitlines():
        line = line.strip()
        if line.startswith("name = "):
            name = line.split('"')[1]
        elif line.startswith("version = ") and name:
            out[name] = line.split('"')[1]
            name = None
    return out


def requirements() -> list[str]:
    """Pin from uv.lock where the project locks it, and from the installed distribution where it
    deliberately does not (google-adk, ADR-34). An unpinned requirement in a deployed agent is a
    reproducibility hole, which is the whole argument the eval makes about model pins."""
    from importlib.metadata import PackageNotFoundError, version
    locked = locked_versions()
    req = []
    for n in REQUIREMENT_NAMES:
        v = locked.get(n)
        if not v:
            try:
                v = version(n)
            except PackageNotFoundError:
                v = None
        req.append(f"{n}=={v}" if v else n)
    return req


def preflight(project: str, region: str, bucket: str) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    ok, out = _sh(["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"])
    checks.append(("authenticated", ok and bool(out), out.splitlines()[0] if out else "no active account"))

    ok, out = _sh(["gcloud", "config", "get-value", "project"])
    checks.append(("project", ok and out.strip() == project, f"{out.strip() or '?'} (want {project})"))

    ok, out = _sh(["gcloud", "services", "list", "--enabled", f"--project={project}",
                   "--filter=config.name:aiplatform.googleapis.com", "--format=value(config.name)"])
    checks.append(("aiplatform API enabled", ok and "aiplatform" in out, out or "not enabled: gcloud services enable aiplatform.googleapis.com"))

    ok, out = _sh(["gcloud", "storage", "buckets", "describe", bucket, f"--project={project}", "--format=value(name)"])
    checks.append(("staging bucket", ok, out.splitlines()[-1][:120] if out else f"missing: gcloud storage buckets create {bucket} --location={region}"))

    try:
        from coherence_gate.adk import Work, build_app                    # noqa: F401
        from coherence_gate.eval.harness import build_context
        import tempfile
        ctx = build_context(ROOT / "golden", Path(tempfile.mkdtemp()), stub=True, source="txt")
        app = build_app(Work(ctx=ctx, doc_path=ROOT / "golden" / "termsheets" / "G11.txt"))
        shape = " → ".join(a.name for a in app.sub_agents)
        checks.append(("agent tree builds", True, shape))
    except ImportError as exc:
        checks.append(("agent tree builds", False, f"{exc} (uv pip install google-adk)"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("agent tree builds", False, f"{type(exc).__name__}: {exc}"))

    try:
        import vertexai  # noqa: F401
        checks.append(("vertexai SDK", True, "importable"))
    except ImportError:
        checks.append(("vertexai SDK", False, "uv pip install 'google-cloud-aiplatform[agent_engines]'"))

    return checks


def deploy(project: str, region: str, bucket: str, display_name: str):
    """Create the Agent Engine instance. Billable, long-lived, and deliberately behind a flag."""
    import vertexai
    from vertexai import agent_engines

    from coherence_gate.adk import Work, build_app
    from coherence_gate.eval.harness import build_context
    import tempfile

    vertexai.init(project=project, location=region, staging_bucket=bucket)
    ctx = build_context(ROOT / "golden", Path(tempfile.mkdtemp()), stub=True, source="txt")
    app = build_app(Work(ctx=ctx, doc_path=ROOT / "golden" / "termsheets" / "G11.txt"))
    remote = agent_engines.create(
        agent_engine=app,
        display_name=display_name,
        description=("Coherence Gate: term sheet vs booking coherence. Two model families read "
                     "independently; deterministic code decides; no LLM chooses the control flow."),
        requirements=requirements(),
        extra_packages=[str(ROOT / "src" / "coherence_gate"), str(ROOT / "schema"),
                        str(ROOT / "prompts"), str(ROOT / "config")],
    )
    return remote


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default="signal-intel-prod")
    ap.add_argument("--region", default="us-central1")
    ap.add_argument("--bucket", default="gs://signal-intel-prod-agent-engine")
    ap.add_argument("--name", default="coherence-gate")
    ap.add_argument("--deploy", action="store_true", help="actually create the Agent Engine instance (billable)")
    a = ap.parse_args()

    checks = preflight(a.project, a.region, a.bucket)
    width = max(len(n) for n, _, _ in checks)
    for name, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    blocked = [n for n, ok, _ in checks if not ok]

    print("\nrequirements the agent would be built with:")
    for r in requirements():
        print(f"  {r}")

    if not a.deploy:
        print(f"\npreflight only, nothing created. To deploy:\n"
              f"  uv pip install 'google-cloud-aiplatform[agent_engines]' google-adk\n"
              f"  uv run python {Path(__file__).relative_to(ROOT)} --deploy --project {a.project} "
              f"--region {a.region} --bucket {a.bucket}")
        return 1 if blocked else 0

    if blocked:
        print(f"\nrefusing to deploy: {', '.join(blocked)} did not pass")
        return 1
    remote = deploy(a.project, a.region, a.bucket, a.name)
    print(json.dumps({"resource_name": getattr(remote, "resource_name", str(remote)),
                      "display_name": a.name, "region": a.region}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
