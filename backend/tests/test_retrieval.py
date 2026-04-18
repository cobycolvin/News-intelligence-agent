from pathlib import Path

import pytest

from app.agents.retrieval_agent import RetrievalAgent
from app.models.schemas import NewsQuery
from app.services.embedding_service import EmbeddingService
from app.services.sample_data import SampleDataRepository
from app.services.vector_store import PgVectorStore, create_vector_store


def test_retrieval_returns_ranked_articles():
    sample_data_path = Path(__file__).resolve().parents[2] / "sample_data" / "articles.json"
    repo = SampleDataRepository(str(sample_data_path))
    agent = RetrievalAgent(repo, EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True))
    output = agent.run(NewsQuery(query="Red Sea shipping disruptions", max_articles=3))
    assert len(output) == 3
    assert output[0].relevance_score >= output[-1].relevance_score


class _FakeIngestionService:
    def fetch_articles(self, query: NewsQuery):
        return [
            {
                "id": "live-1",
                "title": "Live update on maritime corridor",
                "source": "LiveWire",
                "date": "2026-04-16",
                "url": "https://example.com/live/maritime",
                "image_path": None,
                "snippet": "A live article",
                "text": "Maritime corridor remains unstable according to officials.",
            },
            {
                "id": "live-dup",
                "title": "Duplicate by url",
                "source": "LiveWire",
                "date": "2026-04-16",
                "url": "https://example.com/live/maritime",
                "image_path": None,
                "snippet": "Duplicate article",
                "text": "Duplicate should be skipped due to URL.",
            },
        ]


def test_retrieval_ingests_live_articles_without_duplicate_urls():
    sample_data_path = Path(__file__).resolve().parents[2] / "sample_data" / "articles.json"
    repo = SampleDataRepository(str(sample_data_path))
    agent = RetrievalAgent(
        repo,
        EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True),
        ingestion_service=_FakeIngestionService(),
        live_ingestion_enabled=True,
    )

    added = agent.ingest_query(NewsQuery(query="maritime", max_articles=5))

    assert added == 1
    output = agent.run(NewsQuery(query="maritime corridor", max_articles=10))
    assert any(article.url == "https://example.com/live/maritime" for article in output)


class _TrackingVectorStore:
    def __init__(self):
        self.cleared = False
        self.rows: dict[str, list[float]] = {}

    def upsert(self, item_id, embedding):
        self.rows[item_id] = list(embedding)

    def search(self, query_embedding, top_k):
        ids = list(self.rows.keys())[:top_k]
        return [(item_id, 0.9) for item_id in ids]

    def clear(self):
        self.cleared = True
        self.rows.clear()


def test_retrieval_uses_injected_vector_store():
    sample_data_path = Path(__file__).resolve().parents[2] / "sample_data" / "articles.json"
    repo = SampleDataRepository(str(sample_data_path))
    tracking_store = _TrackingVectorStore()

    agent = RetrievalAgent(
        repo,
        EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True),
        vector_store=tracking_store,
    )

    output = agent.run(NewsQuery(query="trade", max_articles=2))

    assert tracking_store.cleared is True
    assert len(tracking_store.rows) > 0
    assert len(output) == 2


def test_vector_store_factory_falls_back_without_database_url():
    store = create_vector_store(backend="pgvector", database_url=None)
    assert store.__class__.__name__ == "InMemoryVectorStore"


def test_vector_store_factory_rejects_invalid_table_name():
    with pytest.raises(ValueError):
        create_vector_store(backend="pgvector", database_url="postgresql://invalid", table_name="bad-name")


def test_pgvector_string_conversion_validates_dimension():
    store = PgVectorStore(database_url="postgresql://invalid", table_name="article_embeddings", dimension=3)
    with pytest.raises(ValueError):
        store._to_pgvector(EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True).embed(["x"])[0])
