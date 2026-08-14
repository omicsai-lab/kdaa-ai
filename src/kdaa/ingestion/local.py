"""Local JSON/YAML/CV ingestion."""

from __future__ import annotations

import json
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader

from kdaa.ingestion.dedup import trace_identity_key
from kdaa.models import (
    ContributionRole,
    EvidenceTrace,
    FocalUnit,
    SourceKind,
    TraceType,
    UnitBundle,
    UnitType,
)


def load_bundle(path: str | Path) -> UnitBundle:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    elif source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
    else:
        raise ValueError("Bundle files must be JSON or YAML")
    return load_bundle_from_dict(payload)


def load_bundle_from_dict(payload: dict[str, Any]) -> UnitBundle:
    return UnitBundle.model_validate(payload)


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix in {".txt", ".md", ".rst", ".tex"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported document type: {suffix}")


def _year_from_text(text: str) -> date | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    if not match:
        return None
    return date(int(match.group(0)), 1, 1)


def parse_cv_document(
    path: str | Path,
    *,
    unit_id: str,
    unit_name: str,
    institution: str | None = None,
    unit_type: UnitType = UnitType.RESEARCHER,
) -> UnitBundle:
    """Create a conservative bundle from a CV-like document.

    This parser deliberately does not infer confirmed expertise. It segments
    likely evidence items and retains the full document as provenance.
    """

    source = Path(path)
    text = _extract_text(source)
    if not text.strip():
        raise ValueError(f"No extractable text found in {source}")

    unit = FocalUnit(
        id=unit_id,
        name=unit_name,
        unit_type=unit_type,
        institution=institution,
        description=f"Focal unit constructed from {source.name}",
        boundary_notes="Imported from a local CV-like document; attribution requires review.",
    )

    traces: list[EvidenceTrace] = [
        EvidenceTrace(
            id=f"trace-{uuid.uuid4().hex[:12]}",
            unit_id=unit_id,
            trace_type=TraceType.DOCUMENT,
            title=f"Source document: {source.name}",
            content=text,
            source_kind=SourceKind.CV,
            source_name=source.name,
            source_uri=str(source.resolve()),
            contribution_role=ContributionRole.UNKNOWN,
            sensitive=True,
            raw={"parser": "kdaa.cv_segmenter.v0.1"},
        )
    ]

    section = "unclassified"
    section_patterns: list[tuple[str, re.Pattern[str], TraceType]] = [
        ("publications", re.compile(r"^(selected\s+)?publications?\b", re.I), TraceType.PUBLICATION),
        ("grants", re.compile(r"^(research\s+)?grants?|funding\b", re.I), TraceType.GRANT),
        ("projects", re.compile(r"^(selected\s+)?projects?\b", re.I), TraceType.PROJECT),
        ("software", re.compile(r"^(software|repositories|open[- ]source)\b", re.I), TraceType.SOFTWARE),
        ("teaching", re.compile(r"^(teaching|courses?|curriculum)\b", re.I), TraceType.COURSE),
        ("talks", re.compile(r"^(invited\s+)?talks?|presentations?\b", re.I), TraceType.TALK),
        ("employment", re.compile(r"^(academic\s+)?appointments?|employment|experience\b", re.I), TraceType.EMPLOYMENT),
        ("awards", re.compile(r"^(honors?|awards?)\b", re.I), TraceType.AWARD),
    ]
    section_type = TraceType.OTHER

    blocks = [block.strip() for block in re.split(r"\n\s*\n|(?=\n[-•*]\s+)", text) if block.strip()]
    for block in blocks:
        first_line = block.splitlines()[0].strip(" :-\t")
        matched_heading = False
        for section_name, pattern, trace_type in section_patterns:
            if pattern.search(first_line) and len(first_line.split()) <= 8:
                section = section_name
                section_type = trace_type
                matched_heading = True
                break
        if matched_heading:
            continue
        cleaned = re.sub(r"^[-•*]\s*", "", block).strip()
        if len(cleaned) < 30:
            continue
        title = cleaned.splitlines()[0][:240]
        traces.append(
            EvidenceTrace(
                id=f"trace-{uuid.uuid4().hex[:12]}",
                unit_id=unit_id,
                trace_type=section_type,
                title=title,
                description=cleaned[:4000],
                source_kind=SourceKind.CV,
                source_name=source.name,
                source_uri=str(source.resolve()),
                event_date=_year_from_text(cleaned),
                contribution_role=ContributionRole.UNKNOWN,
                sensitive=True,
                raw={"cv_section": section, "parser": "kdaa.cv_segmenter.v0.1"},
            )
        )

    return UnitBundle(
        unit=unit,
        traces=traces,
        metadata={
            "source_document": source.name,
            "parser_warning": (
                "Section segmentation is heuristic. All inferred contribution roles remain unknown."
            ),
        },
    )


def merge_bundles(
    bundles: list[UnitBundle],
    *,
    unit: FocalUnit | None = None,
) -> UnitBundle:
    """Merge evidence sources into one focal-unit bundle.

    Trace IDs are preserved when unique and deterministically suffixed on
    collision. Source URIs are de-duplicated conservatively.
    """

    if not bundles:
        raise ValueError("At least one bundle is required")
    target = unit or bundles[0].unit
    goals = []
    goal_ids = set()
    traces: list[EvidenceTrace] = []
    seen_trace_ids: set[str] = set()
    seen_trace_keys: set[str] = set()
    source_metadata = []

    for bundle_index, bundle in enumerate(bundles):
        source_metadata.append(bundle.metadata)
        for goal in bundle.goals:
            if goal.id not in goal_ids:
                goals.append(goal)
                goal_ids.add(goal.id)
        for trace in bundle.traces:
            trace_key = trace_identity_key(trace)
            if trace_key in seen_trace_keys:
                continue
            seen_trace_keys.add(trace_key)
            trace_id = trace.id
            if trace_id in seen_trace_ids:
                trace_id = f"{trace_id}-m{bundle_index}"
            seen_trace_ids.add(trace_id)
            traces.append(trace.model_copy(update={"id": trace_id, "unit_id": target.id}))

    return UnitBundle(
        unit=target,
        goals=goals,
        traces=traces,
        metadata={
            "merged_sources": len(bundles),
            "source_metadata": source_metadata,
            "merge_warning": (
                "Unit identity, duplicate detection, and contribution attribution must be reviewed after merging."
            ),
        },
    )
