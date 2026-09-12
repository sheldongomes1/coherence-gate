"""Append-only trace: one JSON line per pipeline step (LLD §10).

Every model call goes through `Tracer.timed(...)`, which is the only place latency and cost
are computed. Lines are flushed immediately so a crash mid-run still leaves a readable trace.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import ModelPin


@dataclass
class StepUsage:
    """Filled in by the caller inside a `timed` block."""

    model_version: str | None = None
    prompt_tokens: int = 0
    output_tokens: int = 0
    outcome: str = "OK"
    detail: Any = None


@dataclass
class Tracer:
    run_id: str
    path: Path
    lines: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def step(self, *, doc_id: str, step: str, outcome: str, model: str | None = None,
             model_version: str | None = None, prompt_tokens: int = 0, output_tokens: int = 0,
             latency_ms: int = 0, cost_usd: float = 0.0, detail: Any = None) -> dict:
        line = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "run_id": self.run_id, "doc_id": doc_id, "step": step,
            "model": model, "model_version": model_version,
            "prompt_tokens": prompt_tokens, "output_tokens": output_tokens,
            "latency_ms": latency_ms, "cost_usd": cost_usd,
            "outcome": outcome, "detail": detail,
        }
        self.lines.append(line)
        with self.path.open("a") as fh:
            fh.write(json.dumps(line, default=str) + "\n")
        return line

    @contextmanager
    def timed(self, *, doc_id: str, step: str, pin: ModelPin | None = None) -> Iterator[StepUsage]:
        usage = StepUsage()
        t0 = time.perf_counter()
        try:
            yield usage
        except Exception as exc:  # noqa: BLE001 — an exception is an outcome, not a crash (LLD §9.3)
            usage.outcome = "API_ERROR"
            usage.detail = f"{type(exc).__name__}: {exc}"[:500]
            raise
        finally:
            latency = int((time.perf_counter() - t0) * 1000)
            cost = pin.cost_usd(usage.prompt_tokens, usage.output_tokens) if pin else 0.0
            self.step(doc_id=doc_id, step=step, outcome=usage.outcome,
                      model=pin.model if pin else None, model_version=usage.model_version,
                      prompt_tokens=usage.prompt_tokens, output_tokens=usage.output_tokens,
                      latency_ms=latency, cost_usd=cost, detail=usage.detail)

    def total_cost(self, doc_id: str | None = None) -> float:
        return round(sum(l["cost_usd"] for l in self.lines if doc_id is None or l["doc_id"] == doc_id), 6)


def read_trace(path: Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


# ----------------------------------------------------------------------------- wall-clock deadline
class DeadlineExceeded(TimeoutError):
    """A model/parser call exceeded its wall-clock budget. Raised in the caller's thread; the
    stalled call is abandoned on a daemon thread (SDK-level timeouts proved unreliable twice:
    a Gemini call ran 4 h 21 min, a Mixedbread poll 3.6 h; eval_log 2026-09-12)."""


def run_with_deadline(fn, seconds: float, *, what: str = "call"):
    """Run fn() on a daemon thread and wait at most `seconds`. On timeout raise DeadlineExceeded."""
    import concurrent.futures as cf
    import threading

    result: dict = {}
    done = threading.Event()

    def target():
        try:
            result["value"] = fn()
        except BaseException as exc:  # noqa: BLE001
            result["error"] = exc
        finally:
            done.set()

    t = threading.Thread(target=target, name=f"deadline:{what}", daemon=True)
    t.start()
    if not done.wait(seconds):
        raise DeadlineExceeded(f"{what} exceeded {seconds:.0f}s wall clock; call abandoned")
    if "error" in result:
        raise result["error"]
    return result["value"]
