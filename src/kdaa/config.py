"""Configuration models and loading helpers."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscoveryConfig(ConfigModel):
    min_trace_support: int = Field(default=2, ge=1)
    max_topic_assets: int = Field(default=12, ge=1)
    max_pair_assets: int = Field(default=8, ge=0)
    min_pair_support: int = Field(default=2, ge=1)
    include_single_artifact_assets: bool = True
    max_relational_assets: int = Field(default=3, ge=0)
    max_execution_assets: int = Field(default=5, ge=0)


class AssessmentWeights(ConfigModel):
    evidence_strength: float = 0.26
    attribution_confidence: float = 0.18
    maturity: float = 0.14
    transferability: float = 0.12
    recency: float = 0.08
    source_diversity: float = 0.12
    contradiction_penalty: float = 0.10


class AssessmentConfig(ConfigModel):
    provisional_threshold: float = Field(default=0.58, ge=0.0, le=1.0)
    human_review_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    tacitness_review_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    recency_half_life_years: float = Field(default=5.0, gt=0.0)
    weights: AssessmentWeights = Field(default_factory=AssessmentWeights)


class OpportunityConfig(ConfigModel):
    max_opportunities: int = Field(default=12, ge=1)
    min_fit_score: float = Field(default=0.28, ge=0.0, le=1.0)
    pairwise_candidates: bool = True
    include_all_five_containers: bool = True


class LLMConfig(ConfigModel):
    enabled: bool = False
    provider: Literal["openai_compatible"] = "openai_compatible"
    base_url: str = "https://api.openai.com/v1"
    model: str = ""
    api_key_env: str = "KDAA_LLM_API_KEY"
    timeout_seconds: float = 90.0
    allow_sensitive_traces: bool = False
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env)


class ExternalDataConfig(ConfigModel):
    openalex_api_key_env: str = "OPENALEX_API_KEY"
    openalex_email_env: str = "OPENALEX_EMAIL"
    github_token_env: str = "GITHUB_TOKEN"
    request_timeout_seconds: float = 30.0
    user_agent: str = "kdaa-ai/0.1.0"


class ExportConfig(ConfigModel):
    write_json: bool = True
    write_markdown: bool = True
    write_csv: bool = True
    write_graphml: bool = True
    write_html: bool = True


class KDAAConfig(ConfigModel):
    version: str = "0.1.0"
    random_seed: int = 42
    mode: Literal["deterministic", "hybrid", "llm"] = "deterministic"
    # Frozen analysis date for recency scoring. None (the default) means "use the current
    # local/system date" -- a convenience fallback for ordinary non-Paper-B use. Paper B
    # runs must set this explicitly so recency is reproducible regardless of execution day.
    # Resolved exactly once, at the KDAAPipeline.analyze boundary (see kdaa.pipeline).
    as_of_date: date | None = None
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    assessment: AssessmentConfig = Field(default_factory=AssessmentConfig)
    opportunities: OpportunityConfig = Field(default_factory=OpportunityConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    external_data: ExternalDataConfig = Field(default_factory=ExternalDataConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    def digest(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


def load_config(path: str | Path | None = None) -> KDAAConfig:
    if path is None:
        return KDAAConfig()
    with Path(path).open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return KDAAConfig.model_validate(payload)


def save_config(config: KDAAConfig, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config.model_dump(mode="json"), handle, sort_keys=False)
