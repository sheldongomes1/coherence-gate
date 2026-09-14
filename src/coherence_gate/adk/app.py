"""The gate as an ADK app: deterministic workflow agents over the existing pipeline functions.

Why this exists: ADK buys a deployment target (Agent Engine), session and event plumbing, and traces
that land in Cloud Trace without re-instrumentation. It does not buy orchestration, because the
pipeline is a fixed DAG and a `for` loop already sequences it correctly.

Why there is no LLM planner: the moment a model chooses which step runs next, the sentence this
product rests on ("models extract and explain; code decides") stops being true. Composition here is
`SequentialAgent` and `ParallelAgent` only — ADK's workflow agents, which run their children in a
fixed order decided by code, not by a model.

Why the agents are thin: each one calls the SAME function the direct path calls (`read_document`,
`extractor.extract`, `pipeline._complete`). Re-expressing the deterministic core inside agents would
create a second implementation of the decision, and two implementations eventually disagree. The
acceptance test (`tests/test_adk_wrapper.py`) asserts the two paths produce identical findings,
identical lanes and identical attestation hashes on the same document.

Install: `uv pip install google-adk` (kept out of the default dependency set and out of the demo
image; the eval and the live service never import this module).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator

from ..pipeline import DocumentResult, ReadResult, RunContext, _complete, read_document
from ..types import Extraction, Family


def _require_adk():
    try:
        from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent  # noqa: F401
        from google.adk.agents.invocation_context import InvocationContext  # noqa: F401
        from google.adk.events import Event, EventActions  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only where ADK is absent
        raise ImportError(
            "the ADK wrapper needs google-adk: `uv pip install google-adk`. The eval, the CLI and the "
            "demo service do not need it; this module is the Agent Engine path only."
        ) from exc
    return BaseAgent, ParallelAgent, SequentialAgent, Event, EventActions


@dataclass
class Work:
    """Everything one document's run carries between steps.

    ADK session state is for small, JSON-shaped facts (what a reader wants to see in the event log);
    the extraction objects and the run context live here, keyed to one invocation, because putting
    them in session state would mean serialising and re-parsing the very artifacts the pipeline is
    careful to hash.
    """
    ctx: RunContext
    doc_path: Path
    pdf_path: Path | None = None
    trade_id: str | None = None
    product_type: str | None = None
    read: ReadResult | None = None
    extractions: dict[Family, Extraction] = field(default_factory=dict)
    result: DocumentResult | None = None
    mark: int = 0


def build_app(work: Work):
    """The pipeline as an agent tree: read → (gemini ‖ claude) → decide and explain.

    Three stages, not eight, on purpose: the stages are the places where the work is genuinely
    different in kind (a vendor call, two independent model calls, a deterministic block). The
    deterministic block stays one function, so there is one implementation of the decision.
    """
    BaseAgent, ParallelAgent, SequentialAgent, Event, EventActions = _require_adk()

    class _Step(BaseAgent):
        model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}
        work: Any = None

        def _event(self, **state):
            return Event(author=self.name, actions=EventActions(state_delta=state))

    class Read(_Step):
        """Parse (or load) the document and detect the product: `pipeline.read_document`, unchanged."""

        async def _run_async_impl(self, ctx) -> AsyncGenerator[Any, None]:
            w: Work = self.work
            w.read = await asyncio.to_thread(read_document, w.doc_path, w.ctx, w.pdf_path, w.product_type)
            r = w.read
            yield self._event(doc_id=r.doc_id, source=w.ctx.source, sha256=r.sha[:12],
                              product_type=r.product_type, chars=len(r.text),
                              parsed_by=(r.parse_meta or {}).get("vendor"))

    class Extract(_Step):
        """One family's reading. Two of these run under a ParallelAgent, exactly as the direct path
        runs them in a thread pool: independent, never told about each other."""
        family: str = "gemini"

        async def _run_async_impl(self, ctx) -> AsyncGenerator[Any, None]:
            w: Work = self.work
            fam, r = Family(self.family), w.read
            ex = await asyncio.to_thread(w.ctx.extractors[fam].extract, r.text,
                                         doc_id=r.doc_id, tracer=w.ctx.tracer, schema=r.schema)
            w.extractions[fam] = ex
            # a field is EXTRACTED, DECLARED_ABSENT, or Malformed (no status at all); the event says which,
            # because "the model was never asked" must never read like "the model found nothing"
            status = [getattr(v, "status", None) for v in ex.fields.values()]
            yield self._event(**{f"extract_{self.family}": {
                "model": ex.model, "model_version": ex.model_version,
                "cited": sum(1 for st in status if str(st) == "Status.EXTRACTED" or st == "EXTRACTED"),
                "declared_absent": sum(1 for st in status if st is not None and not (str(st) == "Status.EXTRACTED" or st == "EXTRACTED")),
                "malformed": sum(1 for st in status if st is None)}})

    class Complete(_Step):
        """Normalize, merge, booking lookup over MCP, compare, relations, reference, lanes, triage,
        persist — the same single function the direct path calls. Nothing here is re-implemented."""

        async def _run_async_impl(self, ctx) -> AsyncGenerator[Any, None]:
            w: Work = self.work; r = w.read
            w.result = await asyncio.to_thread(
                _complete, r.doc_id, r.text, r.sha, r.product_type, r.schema,
                w.extractions, r.parse_meta, w.doc_path, w.ctx, w.trade_id, None, r.mark)
            r = w.result
            yield self._event(document_lane=str(r.document_lane), findings=len(r.findings),
                              cost_usd=r.cost_usd, trade_id=r.trade_id,
                              attested=(r.extras.get("attested_hashes") or {}).get("document_sha256", "")[:12])

    return SequentialAgent(
        name="coherence_gate",
        description="Term sheet vs booking coherence: two independent readings, deterministic decision.",
        sub_agents=[
            Read(name="read_document", work=work),
            ParallelAgent(name="read_both_families",
                          description="Two model families read the document independently; neither sees the other.",
                          sub_agents=[Extract(name="extract_gemini", family="gemini", work=work),
                                      Extract(name="extract_claude", family="claude", work=work)]),
            Complete(name="decide_and_explain", work=work),
        ])


async def run_document_adk(doc_path: Path, ctx: RunContext, trade_id: str | None = None,
                           pdf_path: Path | None = None, product_type: str | None = None,
                           collect_events: list | None = None) -> DocumentResult:
    """`pipeline.run_document` through the ADK runner. Same inputs, same artifacts, same hashes."""
    _require_adk()
    from google.adk.runners import InMemoryRunner
    from google.genai import types as gt

    work = Work(ctx=ctx, doc_path=Path(doc_path), pdf_path=pdf_path, trade_id=trade_id, product_type=product_type)
    runner = InMemoryRunner(agent=build_app(work), app_name="coherence_gate")
    session = await runner.session_service.create_session(app_name="coherence_gate", user_id="desk")
    async for event in runner.run_async(user_id="desk", session_id=session.id,
                                        new_message=gt.Content(role="user", parts=[gt.Part(text=str(doc_path))])):
        if collect_events is not None:
            collect_events.append(event)
    if work.result is None:  # a step that yields nothing must not look like a clean run (SKILL.md)
        raise RuntimeError("the ADK app produced no result: a step failed before `decide_and_explain`")
    return work.result


def run_document_adk_sync(*args, **kwargs) -> DocumentResult:
    return asyncio.run(run_document_adk(*args, **kwargs))
