import json
from pathlib import Path

from kdaa.ingestion.github import GitHubConnector
from kdaa.ingestion.openalex import OpenAlexConnector, reconstruct_abstract

FIXTURES = Path(__file__).parent / "fixtures"


def test_reconstruct_abstract() -> None:
    assert reconstruct_abstract({"hello": [0], "world": [1]}) == "hello world"
    assert reconstruct_abstract(None) == ""


def test_openalex_connector_parses_mocked_responses(monkeypatch) -> None:
    author = json.loads((FIXTURES / "openalex_author.json").read_text())
    works = json.loads((FIXTURES / "openalex_works.json").read_text())
    connector = OpenAlexConnector()

    def fake_get(path, params=None):
        if path.startswith("/authors/"):
            return author
        if path == "/authors":
            return {"results": [author]}
        if path == "/works":
            return works
        raise AssertionError(path)

    monkeypatch.setattr(connector, "_get", fake_get)
    bundle = connector.fetch_bundle("A123456789", max_works=10)
    assert bundle.unit.name == "Synthetic Public Researcher"
    assert len(bundle.traces) == 2
    assert bundle.traces[0].contribution_role.value == "lead"
    assert "Agentic AI" in bundle.traces[0].keywords


def test_github_connector_parses_mocked_responses(monkeypatch) -> None:
    profile = json.loads((FIXTURES / "github_profile.json").read_text())
    repos = json.loads((FIXTURES / "github_repos.json").read_text())
    connector = GitHubConnector()

    def fake_get(path, params=None):
        if path.startswith("/users/") and path.endswith("/repos"):
            return repos
        if path.startswith("/users/"):
            return profile
        raise AssertionError(path)

    monkeypatch.setattr(connector, "_get", fake_get)
    bundle = connector.fetch_bundle("synthetic-user", include_forks=False)
    assert bundle.unit.name == "Synthetic Developer"
    assert len(bundle.traces) == 1
    assert bundle.traces[0].title == "omics-agent"
    assert bundle.traces[0].license == "MIT"
