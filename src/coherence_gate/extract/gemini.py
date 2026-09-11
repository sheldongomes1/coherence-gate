"""Extractor A — Gemini via google-genai (LLD §9.2). JSON-schema-constrained output."""
from __future__ import annotations

import os

from google import genai
from google.genai import types as gt

from ..config import ExtractionSettings, ModelPin
from ..schema_loader import Schema
from ..trace import Tracer
from ..types import Extraction, Family
from .base import SYSTEM, all_malformed, finalize, raw_extraction_json_schema, render_prompt


class GeminiExtractor:
    family = Family.gemini

    def __init__(self, pin: ModelPin, settings: ExtractionSettings | None = None) -> None:
        self.pin = pin
        self.settings = settings or ExtractionSettings()
        # Same code path serves Vertex: GOOGLE_GENAI_USE_VERTEXAI=true + project/location env (HLD §8).
        self.client = genai.Client() if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") else \
            genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    def extract(self, document: str, *, doc_id: str, tracer: Tracer, schema: Schema) -> Extraction:
        prompt = render_prompt(schema, document, self.settings.prompt_version)
        cfg = gt.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_json_schema=raw_extraction_json_schema(schema),
            temperature=self.settings.temperature,
            max_output_tokens=self.settings.max_output_tokens_gemini,
            thinking_config=gt.ThinkingConfig(thinking_level=self.settings.gemini_thinking_level)
            if self.settings.gemini_thinking_level else None,
        )
        with tracer.timed(doc_id=doc_id, step="extract:gemini", pin=self.pin) as u:
            try:
                resp = self.client.models.generate_content(model=self.pin.model, contents=prompt, config=cfg)
            except Exception as exc:  # noqa: BLE001 — outcome, not crash
                u.outcome, u.detail = "API_ERROR", f"{type(exc).__name__}: {str(exc)[:300]}"
                return all_malformed(self.family, self.pin, schema, reason=u.detail)
            um = resp.usage_metadata
            u.model_version = getattr(resp, "model_version", None) or self.pin.model
            u.prompt_tokens = (um.prompt_token_count or 0) if um else 0
            # thoughts are billed as output tokens
            u.output_tokens = ((um.candidates_token_count or 0) + (um.thoughts_token_count or 0)) if um else 0
            text = resp.text or ""
            ext, violations = finalize(family=self.family, pin=self.pin, schema=schema, document=document,
                                       raw_text=text, model_version=u.model_version)
            u.outcome = "OK" if not violations else "MALFORMED"
            u.detail = {"violations": violations, "finish": str(getattr(resp.candidates[0], "finish_reason", "")) if resp.candidates else None}
        return ext
