from fastapi.testclient import TestClient
from app.main import app
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.vision_agent import VisionAgent
from app.core.dependencies import get_ingestion_task_store, get_orchestrator
from app.models.schemas import NewsQuery
from app.services.ingestion_tasks import IngestionTaskStore
from app.services.orchestrator import NewsPipelineOrchestrator


client = TestClient(app)


class _FakeRetrievalAgent:
    def __init__(self, indexed_articles: int, live_enabled: bool = True):
        self.live_ingestion_enabled = live_enabled
        self.ingestion_service = object() if live_enabled else None
        self._indexed_articles = indexed_articles

    def ingest_query(self, query: NewsQuery, progress_callback=None) -> int:
        if progress_callback is not None:
            progress_callback(
                state="indexing_articles",
                message="Fake indexing in progress.",
                progress_current=1,
                progress_total=1,
                meta={"fake": True},
            )
        return self._indexed_articles

    def run(self, query: NewsQuery):
        return []


def _override_orchestrator(indexed_articles: int, live_enabled: bool = True) -> NewsPipelineOrchestrator:
    return NewsPipelineOrchestrator(
        retrieval_agent=_FakeRetrievalAgent(indexed_articles=indexed_articles, live_enabled=live_enabled),
        vision_agent=VisionAgent(mock_mode=True),
        synthesis_agent=SynthesisAgent(use_mock=True),
    )


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


def test_ingest_route_creates_task_when_live_ingestion_is_enabled():
    task_store = IngestionTaskStore()
    app.dependency_overrides[get_orchestrator] = lambda: _override_orchestrator(indexed_articles=2, live_enabled=True)
    app.dependency_overrides[get_ingestion_task_store] = lambda: task_store
    try:
        response = client.post("/api/ingest", json={"query": "Maritime disruptions", "max_articles": 4})
        status_response = client.get(f"/api/status/{response.json()['task_id']}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"]
    assert data["query"] == "Maritime disruptions"
    assert data["state"] in {"queued", "warming_embeddings", "completed"}
    assert "progress_current" in data
    assert "progress_total" in data
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "completed"


def test_status_route_returns_404_for_missing_task():
    response = client.get("/api/status/does-not-exist")
    assert response.status_code == 404


def test_ingest_route_returns_503_when_live_ingestion_disabled():
    app.dependency_overrides[get_orchestrator] = lambda: _override_orchestrator(indexed_articles=1, live_enabled=False)
    try:
        response = client.post("/api/ingest", json={"query": "Maritime disruptions", "max_articles": 4})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "Live ingestion is not enabled" in response.json()["detail"]


def test_ingest_route_marks_task_failed_when_no_articles_indexed():
    task_store = IngestionTaskStore()
    app.dependency_overrides[get_orchestrator] = lambda: _override_orchestrator(indexed_articles=0, live_enabled=True)
    app.dependency_overrides[get_ingestion_task_store] = lambda: task_store
    try:
        response = client.post("/api/ingest", json={"query": "Maritime disruptions", "max_articles": 4})
        task_id = response.json()["task_id"]
        status_response = client.get(f"/api/status/{task_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["state"] == "failed"
    assert data["indexed_articles"] == 0
    assert data["error"] == "No new live articles were indexed for the query."
    assert data["progress_percent"] == 100.0
