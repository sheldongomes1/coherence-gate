"""Extractor B — Claude via the anthropic SDK 1.x (LLD §9.3). Structured outputs through
output_config.format; adaptive thinking (default on Opus 5) with effort from config."""
from __future__ import annotations

import anthropic

from ..config import ExtractionSettings, ModelPin
from ..schema_loader import Schema
from ..trace import Tracer
from ..types import Extraction, Family
from .base import SYSTEM, all_malformed, finalize, raw_extraction_json_schema, render_prompt


class ClaudeExtractor:
    family = Family.claude

    def __init__(self, pin: ModelPin, settings: ExtractionSettings | None = None) -> None:
        self.pin = pin
        self.settings = settings or ExtractionSettings()
        self.client = anthropic.Anthropic()  # AnthropicVertex(project_id, region) is the Vertex swap (HLD §8)

    def extract(self, document: str, *, doc_id: str, tracer: Tracer, schema: Schema) -> Extraction:
        prompt = render_prompt(schema, document, self.settings.prompt_version)
        with tracer.timed(doc_id=doc_id, step="extract:claude", pin=self.pin) as u:
            try:
                resp = self.client.messages.create(
                    model=self.pin.model,
                    max_tokens=self.settings.max_output_tokens_claude,
                    system=SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                    output_config={"effort": self.settings.claude_effort,
                                   "format": {"type": "json_schema", "schema": raw_extraction_json_schema(schema)}},
                )
            except Exception as exc:  # noqa: BLE001 — outcome, not crash
                u.outcome, u.detail = "API_ERROR", f"{type(exc).__name__}: {str(exc)[:300]}"
                return all_malformed(self.family, self.pin, schema, reason=u.detail)
            u.model_version = resp.model
            u.prompt_tokens = resp.usage.input_tokens
            u.output_tokens = resp.usage.output_tokens
            if resp.stop_reason == "refusal":
                u.outcome, u.detail = "REFUSAL", getattr(resp, "stop_details", None)
                return all_malformed(self.family, self.pin, schema, reason="model refusal", model_version=resp.model)
            text = next((b.text for b in resp.content if b.type == "text"), "")
            ext, violations = finalize(family=self.family, pin=self.pin, schema=schema, document=document,
                                       raw_text=text, model_version=resp.model)
            u.outcome = "OK" if not violations else "MALFORMED"
            u.detail = {"violations": violations, "stop_reason": resp.stop_reason}
        return ext
