from fastapi.testclient import TestClient

from kdaa.api import app
from kdaa.ingestion.synthetic import build_demo_bundle


def test_health_and_demo_api() -> None:
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    response = client.post("/v1/demo")
    assert response.status_code == 200
    assert response.json()["unit"]["is_synthetic"] is True


def test_analyze_api() -> None:
    client = TestClient(app)
    bundle = build_demo_bundle().model_dump(mode="json")
    response = client.post("/v1/analyze", json=bundle)
    assert response.status_code == 200
    assert len(response.json()["assets"]) > 0
