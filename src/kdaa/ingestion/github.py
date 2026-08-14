"""GitHub public-repository connector."""

from __future__ import annotations

import os
from datetime import date, datetime
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


class GitHubConnector:
    BASE_URL = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, config: ExternalDataConfig | None = None) -> None:
        self.config = config or ExternalDataConfig()
        self.token = os.getenv(self.config.github_token_env)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
            "User-Agent": self.config.user_agent,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        with httpx.Client(
            base_url=self.BASE_URL,
            timeout=self.config.request_timeout_seconds,
            follow_redirects=True,
            headers=self._headers(),
        ) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    def fetch_bundle(
        self,
        username: str,
        *,
        unit_id: str | None = None,
        unit_name: str | None = None,
        include_forks: bool = False,
        max_repos: int = 100,
    ) -> UnitBundle:
        profile = self._get(f"/users/{username}")
        repos = self._get(
            f"/users/{username}/repos",
            {
                "per_page": min(max_repos, 100),
                "sort": "updated",
                "direction": "desc",
                "type": "owner",
            },
        )
        selected = [repo for repo in repos if include_forks or not repo.get("fork")][:max_repos]
        focal_id = unit_id or f"github:{username.lower()}"
        unit = FocalUnit(
            id=focal_id,
            name=unit_name or profile.get("name") or username,
            unit_type=UnitType.RESEARCHER,
            institution=profile.get("company"),
            description=profile.get("bio") or "GitHub public profile",
            homepage=profile.get("blog") or profile.get("html_url"),
            identifiers={"github": profile.get("html_url") or username},
            boundary_notes=(
                "Repository ownership does not establish authorship of every line or component. "
                "Contribution and maintenance claims require review."
            ),
        )
        traces = [self._repo_to_trace(repo, focal_id) for repo in selected]
        return UnitBundle(
            unit=unit,
            traces=traces,
            metadata={
                "connector": "github",
                "username": username,
                "include_forks": include_forks,
                "rate_limit_note": (
                    "Unauthenticated public requests have lower rate limits; set GITHUB_TOKEN for "
                    "larger runs."
                ),
            },
        )

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    @classmethod
    def _repo_to_trace(cls, repo: dict[str, Any], unit_id: str) -> EvidenceTrace:
        topics = list(repo.get("topics") or [])
        language = repo.get("language")
        keywords = topics + ([language] if language else [])
        return EvidenceTrace(
            id=f"trace-github-{repo.get('id')}",
            unit_id=unit_id,
            trace_type=TraceType.SOFTWARE,
            title=repo.get("name") or "Unnamed repository",
            description=repo.get("description") or "",
            source_kind=SourceKind.GITHUB,
            source_name="GitHub",
            source_uri=repo.get("html_url"),
            source_record_id=str(repo.get("id")),
            event_date=cls._parse_date(repo.get("pushed_at") or repo.get("updated_at")),
            keywords=[str(item) for item in keywords if item],
            topics=[str(item) for item in topics if item],
            contribution_role=ContributionRole.LEAD,
            outcome_signals={
                "stars": int(repo.get("stargazers_count") or 0),
                "forks": int(repo.get("forks_count") or 0),
                "watchers": int(repo.get("watchers_count") or 0),
                "open_issues": int(repo.get("open_issues_count") or 0),
                "archived": bool(repo.get("archived")),
                "fork": bool(repo.get("fork")),
            },
            license=((repo.get("license") or {}).get("spdx_id")),
            raw={
                "default_branch": repo.get("default_branch"),
                "size_kb": repo.get("size"),
                "visibility": repo.get("visibility"),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
                "pushed_at": repo.get("pushed_at"),
            },
        )
