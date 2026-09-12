"""Pinned models, prices and paths (LLD §2). Model ids are recorded on every trace line."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
MODELS_YAML = ROOT / "config" / "models.yaml"


@dataclass(frozen=True)
class ModelPin:
    family: str
    model: str
    price_in: float   # USD per 1M input tokens
    price_out: float  # USD per 1M output tokens
    pinned: bool = True  # False when overridden by env to an id not in the alternatives list

    def cost_usd(self, prompt_tokens: int, output_tokens: int) -> float:
        return round((prompt_tokens * self.price_in + output_tokens * self.price_out) / 1_000_000, 6)


@dataclass(frozen=True)
class ExtractionSettings:
    prompt_version: str = "extract_v1"
    claude_effort: str = "medium"
    gemini_thinking_level: str | None = "medium"
    max_output_tokens_gemini: int = 32000
    max_output_tokens_claude: int = 16000
    timeout_s: float = 240.0
    temperature: float = 0.0


@dataclass(frozen=True)
class Config:
    gemini: ModelPin
    claude: ModelPin
    triage: ModelPin
    extraction: ExtractionSettings = ExtractionSettings()
    root: Path = ROOT

    @property
    def pins(self) -> list[ModelPin]:
        return [self.gemini, self.claude, self.triage]


def _pin(block: dict, env_key: str) -> ModelPin:
    model = os.environ.get(env_key) or block["model"]
    known = {block["model"], *block.get("alternatives", [])}
    return ModelPin(
        family=block["family"],
        model=model,
        price_in=float(block["price_per_1m_input_usd"]),
        price_out=float(block["price_per_1m_output_usd"]),
        pinned=model in known,
    )


def _extraction_settings(block: dict) -> ExtractionSettings:
    kw = {k: v for k, v in block.items() if k in ExtractionSettings.__dataclass_fields__}
    # Sweep knobs (ADR-15) without editing the pinned file; both are written to the trace.
    if os.environ.get("CG_GEMINI_THINKING"):
        kw["gemini_thinking_level"] = None if os.environ["CG_GEMINI_THINKING"] == "none" else os.environ["CG_GEMINI_THINKING"]
    if os.environ.get("CG_CLAUDE_EFFORT"):
        kw["claude_effort"] = os.environ["CG_CLAUDE_EFFORT"]
    return ExtractionSettings(**kw)


def load_config(path: Path = MODELS_YAML) -> Config:
    load_dotenv(ROOT / ".env")
    raw = yaml.safe_load(Path(path).read_text())
    return Config(
        gemini=_pin(raw["extractors"]["gemini"], "CG_MODEL_GEMINI"),
        claude=_pin(raw["extractors"]["claude"], "CG_MODEL_CLAUDE"),
        triage=_pin(raw["triage"], "CG_MODEL_TRIAGE"),
        extraction=_extraction_settings(raw.get("extraction") or {}),
    )
