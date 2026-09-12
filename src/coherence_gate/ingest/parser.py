"""parse(pdf) -> markdown + meta, behind one interface (V2-CHANGES CS2).

The parsed markdown is the CANONICAL source text: every extraction citation anchors into it,
and the run report says so per document. The PDF is upstream evidence. Parsed artifacts are
versioned under golden/parsed/<doc_id>.md with a .meta.json (vendor, job id, mode, latency,
pdf sha256) and are reused while the PDF hash is unchanged, so an eval does not re-parse.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class ParseResult:
    markdown: str
    meta: dict[str, Any] = field(default_factory=dict)


class Parser(Protocol):
    name: str

    def parse(self, pdf: Path) -> ParseResult: ...


class MixedbreadParser:
    """Mixedbread Parsing API: upload -> create job (markdown, high_quality, page chunks) -> poll."""

    name = "mixedbread"

    def __init__(self, mode: str = "high_quality", poll_timeout_s: float = 300.0) -> None:
        from mixedbread import Mixedbread  # the only vendor import in the codebase

        # Hard HTTP timeout + bounded retries: the SDK's poll_timeout did not stop one poll from
        # sitting 3.6 h on a stalled connection (lessons.md 2026-09-12). timeout is per request.
        self.client = Mixedbread(api_key=os.environ["MXBAI_API_KEY"], timeout=60.0, max_retries=2)
        self.mode, self.poll_timeout_s = mode, poll_timeout_s
        import mixedbread as _m
        self.sdk_version = getattr(_m, "__version__", "?")

    def parse(self, pdf: Path) -> ParseResult:
        from ..trace import run_with_deadline
        t0 = time.perf_counter()

        def _upload():
            with open(pdf, "rb") as fh:
                return self.client.files.create(file=fh)
        f = run_with_deadline(_upload, 120.0, what="mixedbread.files.create")
        job = run_with_deadline(lambda: self.client.parsing.jobs.create(file_id=f.id, return_format="markdown", mode=self.mode,
                                                                        chunking_strategy="page"), 120.0, what="mixedbread.jobs.create")
        job = run_with_deadline(lambda: self.client.parsing.jobs.poll(job.id, poll_timeout_ms=self.poll_timeout_s * 1000),
                                self.poll_timeout_s + 60, what="mixedbread.jobs.poll")
        latency = int((time.perf_counter() - t0) * 1000)
        if job.status != "completed" or job.result is None:
            raise RuntimeError(f"mixedbread job {job.id} status={job.status} error={job.error}")
        chunks = job.result.chunks or []
        md = "\n\n".join((c.content or "") for c in chunks)
        return ParseResult(markdown=md, meta={
            "vendor": self.name, "job_id": job.id, "file_id": f.id, "mode": self.mode, "return_format": "markdown",
            "chunking": "page", "pages": len(chunks), "latency_ms": latency,
            "cost_usd": None,  # not reported by the API; stated as such in the report
            "sdk_version": self.sdk_version, "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })


class LocalParser:
    """pdftotext -layout. The fallback when no vendor key or the vendor misbehaves."""

    name = "local-fallback"

    def parse(self, pdf: Path) -> ParseResult:
        t0 = time.perf_counter()
        out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        return ParseResult(markdown=out, meta={"vendor": self.name, "tool": "pdftotext -layout", "job_id": None,
                                               "latency_ms": int((time.perf_counter() - t0) * 1000), "cost_usd": 0.0,
                                               "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%S")})


def get_parser(name: str) -> Parser:
    if name == "mixedbread":
        return MixedbreadParser()
    if name == "local":
        return LocalParser()
    raise ValueError(f"unknown parser {name!r}")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_document(doc_id: str, pdf: Path, parser: Parser, cache_dir: Path) -> tuple[ParseResult, bool]:
    """Returns (result, cached). Reuses golden/parsed/<doc_id>.md when the PDF hash and the
    vendor match the stored meta; otherwise parses and stores the versioned artifact."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    md_path, meta_path = cache_dir / f"{doc_id}.md", cache_dir / f"{doc_id}.meta.json"
    digest = sha256(pdf)
    if md_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("pdf_sha256") == digest and meta.get("vendor") == parser.name:
            return ParseResult(markdown=md_path.read_text(), meta=meta), True
    res = parser.parse(pdf)
    res.meta.update({"doc_id": doc_id, "pdf": str(pdf), "pdf_sha256": digest,
                     "markdown_sha256": hashlib.sha256(res.markdown.encode()).hexdigest()})
    md_path.write_text(res.markdown)
    meta_path.write_text(json.dumps(res.meta, indent=2) + "\n")
    return res, False
