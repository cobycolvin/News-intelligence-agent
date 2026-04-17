import os
import uuid
from pathlib import Path

import numpy as np
import pytest

from app.agents.retrieval_agent import RetrievalAgent
from app.models.schemas import NewsQuery
from app.services.embedding_service import EmbeddingService
from app.services.sample_data import SampleDataRepository
from app.services.vector_store import create_vector_store


@pytest.mark.integration
def test_pgvector_backend_round_trip_when_database_is_configured():
    database_url = os.getenv("PGVECTOR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set PGVECTOR_TEST_DATABASE_URL to run pgvector integration test")

    table_name = f"article_embeddings_it_{uuid.uuid4().hex[:8]}"
    store = create_vector_store(
        backend="pgvector",
        database_url=database_url,
        table_name=table_name,
        dimension=3,
    )

    # If a DB URL is provided, this must not silently fall back to memory.
    assert store.__class__.__name__ == "PgVectorStore"

    store.clear()
    store.upsert("a", np.array([1.0, 0.0, 0.0], dtype=float))
    store.upsert("b", np.array([0.0, 1.0, 0.0], dtype=float))

    matches = store.search(np.array([0.9, 0.1, 0.0], dtype=float), top_k=2)

    assert len(matches) == 2
    assert matches[0][0] == "a"


@pytest.mark.integration
def test_pgvector_backend_supports_retrieval_agent_flow_when_database_is_configured():
    database_url = os.getenv("PGVECTOR_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set PGVECTOR_TEST_DATABASE_URL to run pgvector integration test")

    table_name = f"article_embeddings_it_{uuid.uuid4().hex[:8]}"
    store = create_vector_store(
        backend="pgvector",
        database_url=database_url,
        table_name=table_name,
        dimension=32,
    )
    assert store.__class__.__name__ == "PgVectorStore"

    sample_data_path = Path(__file__).resolve().parents[2] / "sample_data" / "articles.json"
    repository = SampleDataRepository(str(sample_data_path))
    retrieval = RetrievalAgent(
        repository=repository,
        embedding_service=EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True),
        vector_store=store,
    )

    results = retrieval.run(NewsQuery(query="shipping disruptions", max_articles=3))

    assert len(results) == 3
    assert all(item.relevance_score >= 0 for item in results)
