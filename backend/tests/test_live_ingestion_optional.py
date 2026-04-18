import os

import pytest

from app.models.schemas import NewsQuery
from app.services.news_ingestion_service import NewsIngestionService


@pytest.mark.integration
def test_live_ingestion_fetch_optional_smoke():
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        pytest.skip("Set NEWS_API_KEY to run live ingestion smoke test")

    service = NewsIngestionService(
        api_key=api_key,
        timeout_seconds=12,
        extract_full_text=False,
    )

    rows = service.fetch_articles(NewsQuery(query="global technology policy", max_articles=3))

    assert isinstance(rows, list)
    if not rows:
        pytest.skip("Live provider returned no rows; verify quota and query conditions")

    required_keys = {"id", "title", "source", "date", "url", "image_path", "snippet", "text"}
    assert required_keys.issubset(rows[0].keys())
