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


# --- E: conservative GitHub contribution role ----------------------------------------------


def test_github_owned_repository_defaults_to_unknown_contribution_role(monkeypatch) -> None:
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
    assert bundle.traces, "fixture must contain at least one owned repository"
    for trace in bundle.traces:
        assert trace.contribution_role.value == "unknown"


def test_github_forked_repository_also_defaults_to_unknown_contribution_role(monkeypatch) -> None:
    profile = json.loads((FIXTURES / "github_profile.json").read_text())
    repos = json.loads((FIXTURES / "github_repos.json").read_text())
    forked_repos = [{**repo, "fork": True} for repo in repos]
    connector = GitHubConnector()

    def fake_get(path, params=None):
        if path.startswith("/users/") and path.endswith("/repos"):
            return forked_repos
        if path.startswith("/users/"):
            return profile
        raise AssertionError(path)

    monkeypatch.setattr(connector, "_get", fake_get)
    bundle = connector.fetch_bundle("synthetic-user", include_forks=True)
    assert bundle.traces
    for trace in bundle.traces:
        assert trace.contribution_role.value == "unknown"


def test_github_connector_preserves_ownership_boundary_note(monkeypatch) -> None:
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
    assert "does not establish authorship" in bundle.unit.boundary_notes


def test_github_connector_does_not_infer_typed_ownership_field(monkeypatch) -> None:
    # The GitHub connector produces EvidenceTrace records only; it must never set a typed
    # AssetRecord.ownership_state (that field belongs to discovery/assessment, which
    # independently defaults to UNRESOLVED -- see tests/test_models.py).
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
    assert not hasattr(bundle.unit, "ownership_state")
    for trace in bundle.traces:
        assert not hasattr(trace, "ownership_state")


def test_github_connector_makes_no_live_network_calls(monkeypatch) -> None:
    # Every other GitHub test in this module monkeypatches `_get` directly. This test
    # proves that convention actually bypasses the network: it forces the real,
    # unmocked `_get` implementation (which opens an httpx.Client) to fail loudly if it
    # is ever reached, then confirms a normal fetch_bundle call -- using a monkeypatched
    # `_get`, exactly like every other test here -- succeeds without hitting it.
    import httpx

    def _forbidden_client(*args, **kwargs):
        raise AssertionError("GitHubConnector attempted a live network call in tests")

    monkeypatch.setattr(httpx, "Client", _forbidden_client)

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
    assert bundle.traces
