from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_route():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_route_mock_mode():
    response = client.post("/api/analyze", json={"query": "AI regulation news", "max_articles": 3})
    assert response.status_code == 200
    data = response.json()
    assert len(data["ranked_articles"]) == 3
    assert data["final_report"]["sources"][0]["url"].startswith("http")
