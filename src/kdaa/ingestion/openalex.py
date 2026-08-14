"""OpenAlex public scholarly-metadata connector.

OpenAlex is treated as evidence, not as ground truth about contribution. The
connector preserves author-position and authorship metadata so the assessment
layer can penalize uncertain attribution.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import date
from typing import Any

import httpx

from kdaa.config import ExternalDataConfig
from kdaa.models import (
    ContributionRole,
    EvidenceTrace,
    FocalUnit,
    SourceKind,
    TraceType,
    UnitBundle,
    UnitType,
)

_ORCID_RE = re.compile(r"^(?:https?://orcid\.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", re.I)
_OPENALEX_AUTHOR_RE = re.compile(r"^(?:https?://openalex\.org/)?(A\d+)$", re.I)


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for token, indexes in inverted_index.items():
        positions.extend((int(index), token) for index in indexes)
    return " ".join(token for _, token in sorted(positions))


class OpenAlexConnector:
    BASE_URL = "https://api.openalex.org"

    def __init__(self, config: ExternalDataConfig | None = None) -> None:
        self.config = config or ExternalDataConfig()
        self.api_key = os.getenv(self.config.openalex_api_key_env)
        self.email = os.getenv(self.config.openalex_email_env)

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(extra or {})
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["mailto"] = self.email
        return params

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"User-Agent": self.config.user_agent}
        with httpx.Client(
            base_url=self.BASE_URL,
            timeout=self.config.request_timeout_seconds,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = client.get(path, params=self._params(params))
            response.raise_for_status()
            return response.json()

    def resolve_author(self, identifier: str) -> dict[str, Any]:
        value = identifier.strip()
        openalex_match = _OPENALEX_AUTHOR_RE.match(value)
        if openalex_match:
            return self._get(f"/authors/{openalex_match.group(1).upper()}")

        orcid_match = _ORCID_RE.match(value)
        if orcid_match:
            payload = self._get(
                "/authors",
                {"filter": f"orcid:{orcid_match.group(1)}", "per_page": 5},
            )
            results = payload.get("results", [])
            if not results:
                raise LookupError(f"No OpenAlex author found for ORCID {orcid_match.group(1)}")
            return results[0]

        payload = self._get("/authors", {"search": value, "per_page": 5})
        results = payload.get("results", [])
        if not results:
            raise LookupError(f"No OpenAlex author found for name: {value}")
        # Name searches are ambiguous; caller must review the selected profile.
        return results[0]

    def fetch_bundle(self, identifier: str, *, max_works: int = 50) -> UnitBundle:
        author = self.resolve_author(identifier)
        author_id = str(author["id"]).rsplit("/", 1)[-1]
        works_payload = self._get(
            "/works",
            {
                "filter": f"author.id:{author_id}",
                "sort": "-publication_date",
                "per_page": min(max_works, 100),
                "select": (
                    "id,doi,display_name,title,publication_date,type,cited_by_count,"
                    "abstract_inverted_index,authorships,topics,keywords,primary_location,"
                    "open_access,awards"
                ),
            },
        )
        works = works_payload.get("results", [])[:max_works]

        institutions = [
            item.get("display_name", "")
            for item in author.get("last_known_institutions", [])
            if item.get("display_name")
        ]
        unit = FocalUnit(
            id=f"openalex:{author_id}",
            name=author.get("display_name") or identifier,
            unit_type=UnitType.RESEARCHER,
            institution=institutions[0] if institutions else None,
            description="Researcher profile imported from OpenAlex public metadata.",
            homepage=author.get("homepage_url"),
            identifiers={
                key: value
                for key, value in (author.get("ids") or {}).items()
                if value
            },
            boundary_notes=(
                "OpenAlex author disambiguation and work attribution can contain merges or splits; "
                "all inferred assets remain hypotheses until reviewed."
            ),
        )

        traces = [self._work_to_trace(work, unit.id, author_id) for work in works]
        return UnitBundle(
            unit=unit,
            traces=traces,
            metadata={
                "connector": "openalex",
                "selected_author": author,
                "max_works": max_works,
                "selection_warning": (
                    "Name-based resolution selects the top OpenAlex match and must be manually verified."
                ),
            },
        )

    @staticmethod
    def _work_to_trace(work: dict[str, Any], unit_id: str, author_id: str) -> EvidenceTrace:
        authorships = work.get("authorships") or []
        target = None
        for authorship in authorships:
            current_id = str((authorship.get("author") or {}).get("id", "")).rsplit("/", 1)[-1]
            if current_id.upper() == author_id.upper():
                target = authorship
                break

        role = ContributionRole.UNKNOWN
        author_position = (target or {}).get("author_position")
        is_corresponding = bool((target or {}).get("is_corresponding"))
        if author_position == "first" or is_corresponding:
            role = ContributionRole.LEAD
        elif author_position == "last":
            role = ContributionRole.SUPERVISOR
        elif target:
            role = ContributionRole.CONTRIBUTOR

        publication_date = None
        raw_date = work.get("publication_date")
        if raw_date:
            try:
                publication_date = date.fromisoformat(raw_date)
            except ValueError:
                publication_date = None

        topics = [
            item.get("display_name", "")
            for item in work.get("topics", [])
            if item.get("display_name")
        ]
        keywords = [
            item.get("display_name", "")
            for item in work.get("keywords", [])
            if item.get("display_name")
        ]
        contributors = [
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in authorships
            if (authorship.get("author") or {}).get("display_name")
        ]
        affiliations = [
            institution.get("display_name", "")
            for institution in (target or {}).get("institutions", [])
            if institution.get("display_name")
        ]
        source = ((work.get("primary_location") or {}).get("source") or {}).get(
            "display_name", "OpenAlex"
        )
        trace_type = TraceType.DATASET if work.get("type") == "dataset" else TraceType.PUBLICATION

        return EvidenceTrace(
            id=f"trace-openalex-{str(work.get('id', uuid.uuid4().hex)).rsplit('/', 1)[-1]}",
            unit_id=unit_id,
            trace_type=trace_type,
            title=work.get("display_name") or work.get("title") or "Untitled work",
            abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
            source_kind=SourceKind.OPENALEX,
            source_name=source or "OpenAlex",
            source_uri=work.get("doi") or work.get("id"),
            source_record_id=work.get("id"),
            event_date=publication_date,
            authors_or_contributors=contributors,
            affiliations=affiliations,
            keywords=keywords,
            topics=topics,
            contribution_role=role,
            outcome_signals={
                "cited_by_count": int(work.get("cited_by_count") or 0),
                "is_open_access": bool((work.get("open_access") or {}).get("is_oa")),
                "has_award_metadata": bool(work.get("awards")),
            },
            license=((work.get("primary_location") or {}).get("license")),
            raw={
                "author_position": author_position,
                "is_corresponding": is_corresponding,
                "openalex_work_type": work.get("type"),
            },
        )
