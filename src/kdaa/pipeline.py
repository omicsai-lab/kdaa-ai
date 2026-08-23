"""End-to-end KDAA-AI analysis pipeline."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from kdaa.amplification import generate_opportunities
from kdaa.assessment import assess_asset_records
from kdaa.config import KDAAConfig
from kdaa.discovery import (
    add_trace_relation_edges,
    build_evidence_graph,
    discover_asset_hypotheses,
    enrich_graph_with_analysis,
    extract_trace_features,
)
from kdaa.discovery.llm import discover_with_llm
from kdaa.discovery.provenance import graph_summary
from kdaa.ingestion import deduplicate_traces
from kdaa.models import AnalysisRun, AssetRecord, RunManifest, UnitBundle
from kdaa.ontology import Ontology
from kdaa.providers.base import JSONProvider
from kdaa.providers.openai_compatible import OpenAICompatibleProvider
from kdaa.report import write_run_outputs


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _merge_assets(primary: list[AssetRecord], secondary: list[AssetRecord]) -> list[AssetRecord]:
    """Merge LLM and deterministic hypotheses without silently collapsing provenance."""

    result = list(primary)
    for candidate in secondary:
        candidate_evidence = {link.trace_id for link in candidate.evidence_links}
        candidate_tags = {tag.lower() for tag in candidate.concept_tags}
        duplicate = False
        for existing in result:
            existing_evidence = {link.trace_id for link in existing.evidence_links}
            existing_tags = {tag.lower() for tag in existing.concept_tags}
            evidence_union = candidate_evidence | existing_evidence
            tag_union = candidate_tags | existing_tags
            evidence_overlap = (
                len(candidate_evidence & existing_evidence) / len(evidence_union)
                if evidence_union
                else 0.0
            )
            tag_overlap = len(candidate_tags & existing_tags) / len(tag_union) if tag_union else 0.0
            if evidence_overlap >= 0.80 and tag_overlap >= 0.70:
                duplicate = True
                existing.notes.append(
                    f"A second discovery method ({candidate.discovery_method}) generated a similar claim."
                )
                break
        if not duplicate:
            result.append(candidate)
    return result


class KDAAPipeline:
    def __init__(
        self,
        config: KDAAConfig | None = None,
        *,
        ontology: Ontology | None = None,
        provider: JSONProvider | None = None,
    ) -> None:
        self.config = config or KDAAConfig()
        self.ontology = ontology or Ontology.default()
        self.provider = provider

    def _get_provider(self) -> JSONProvider:
        if self.provider is not None:
            return self.provider
        llm = self.config.llm
        if not llm.enabled:
            raise RuntimeError("LLM mode requested but llm.enabled is false")
        api_key = llm.api_key
        if not api_key:
            raise RuntimeError(f"Missing LLM API key in environment variable {llm.api_key_env}")
        self.provider = OpenAICompatibleProvider(
            base_url=llm.base_url,
            api_key=api_key,
            model=llm.model,
            timeout_seconds=llm.timeout_seconds,
            temperature=llm.temperature,
        )
        return self.provider

    def analyze(
        self,
        bundle: UnitBundle,
        *,
        output_dir: str | Path | None = None,
    ) -> tuple[AnalysisRun, Any]:
        effective_as_of_date = self.config.as_of_date or date.today()

        deduplication = deduplicate_traces(bundle.traces)
        analysis_bundle = bundle.model_copy(
            update={
                "traces": deduplication.canonical_traces,
                "metadata": {
                    **bundle.metadata,
                    "analysis_duplicate_count": deduplication.duplicate_count,
                },
            }
        )
        features = extract_trace_features(analysis_bundle.traces, self.ontology)
        base_graph = add_trace_relation_edges(
            build_evidence_graph(bundle), deduplication.trace_relations
        )

        deterministic_assets: list[AssetRecord] = []
        llm_assets: list[AssetRecord] = []
        if self.config.mode in {"deterministic", "hybrid"}:
            deterministic_assets = discover_asset_hypotheses(
                analysis_bundle,
                features,
                self.ontology,
                self.config.discovery,
            )
        if self.config.mode in {"hybrid", "llm"}:
            provider = self._get_provider()
            llm_assets = discover_with_llm(
                analysis_bundle,
                provider,
                allow_sensitive=self.config.llm.allow_sensitive_traces,
            )

        assets = _merge_assets(deterministic_assets, llm_assets)
        assets = assess_asset_records(
            assets,
            analysis_bundle.traces,
            features,
            self.ontology,
            self.config.assessment,
            as_of_date=effective_as_of_date,
        )
        opportunities = generate_opportunities(
            bundle.unit.id,
            assets,
            bundle.goals,
            self.config.opportunities,
        )

        input_digest = _digest(bundle.model_dump(mode="json"))
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        notes = [
            "Trace-to-asset separation enforced.",
            "No asset is confirmed without a calibration record.",
            "AI amplifiability is evaluated relative to a stated opportunity and baseline.",
        ]
        if deduplication.duplicate_count:
            notes.append(
                f"Excluded {deduplication.duplicate_count} exact/source-record-equivalent "
                "duplicate trace(s) from discovery and assessment while retaining them in provenance."
            )
        if self.config.mode in {"hybrid", "llm"}:
            notes.append("Language-model suggestions are subject to trace-ID provenance gates.")
        manifest = RunManifest(
            run_id=run_id,
            kdaa_version=self.config.version,
            config_digest=self.config.digest(),
            input_digest=input_digest,
            random_seed=self.config.random_seed,
            mode=self.config.mode,
            llm_model=(self.provider.model_name if self.provider else None),
            analysis_as_of_date=effective_as_of_date,
            notes=notes,
        )
        warnings = [
            "All asset scores are transparent engineering proxies, not validated latent-variable measures.",
            "A provisional state does not establish expertise, ownership, causality, or value.",
            "Opportunity scores are prioritization aids; they do not replace scientific, legal, ethical, or managerial judgment.",
            "Human calibration is optional for running the MVP but is required before treating high-impact claims as confirmed assets.",
        ]
        if deduplication.duplicate_count:
            warnings.append(
                f"{deduplication.duplicate_count} duplicate trace(s) were retained in the evidence graph "
                "but excluded from analytical support counts. Semantic near-duplicates may still require review."
            )
        if bundle.unit.is_synthetic:
            warnings.insert(0, "The focal-unit data are synthetic and cannot support empirical claims about real people or organizations.")
        if not bundle.traces:
            warnings.append("No evidence traces were supplied; outputs will be empty.")
        if any(trace.sensitive for trace in bundle.traces):
            warnings.append("Sensitive traces are present. Review exports before sharing or invoking any remote model.")

        run = AnalysisRun(
            manifest=manifest,
            unit=bundle.unit,
            goals=bundle.goals,
            traces=bundle.traces,
            assets=assets,
            opportunities=opportunities,
            graph_summary={},
            warnings=warnings,
        )
        enriched_graph = enrich_graph_with_analysis(base_graph, run)
        run = run.model_copy(update={"graph_summary": graph_summary(enriched_graph)})
        if output_dir is not None:
            write_run_outputs(run, enriched_graph, output_dir)
        return run, enriched_graph
