from __future__ import annotations

import logging
from typing import List

from app.models.schemas import NewsQuery, RankedArticle
from app.services.embedding_service import EmbeddingService
from app.services.news_ingestion_service import NewsIngestionService
from app.services.sample_data import SampleDataRepository
from app.services.vector_store import InMemoryVectorStore, VectorStore
from app.utils.source_quality import is_source_allowed, source_quality_score
from app.utils.text import clean_article_text

logger = logging.getLogger(__name__)


class RetrievalAgent:
    def __init__(
        self,
        repository: SampleDataRepository,
        embedding_service: EmbeddingService,
        ingestion_service: NewsIngestionService | None = None,
        live_ingestion_enabled: bool = False,
        vector_store: VectorStore | None = None,
    ):
        self.repository = repository
        self.embedding_service = embedding_service
        self.ingestion_service = ingestion_service
        self.live_ingestion_enabled = live_ingestion_enabled
        self.vector_store = vector_store or InMemoryVectorStore()
        self._cache: dict[str, dict] = {}
        self._urls: set[str] = set()
        self._index_articles()

    def _index_articles(self) -> None:
        self.vector_store.clear()
        rows = self.repository.load_articles()
        self._upsert_rows(rows)
        logger.info("Indexed %s sample articles", len(rows))

    def _upsert_rows(self, rows: List[dict]) -> int:
        if not rows:
            return 0

        texts = [f"{r['title']} {r['snippet']} {r['text']}" for r in rows]
        embeddings = self.embedding_service.embed(texts)
        added = 0
        for row, emb in zip(rows, embeddings):
            if not is_source_allowed(row["url"]):
                logger.info("Skipping blocked source during indexing: %s", row["url"])
                continue
            if row["url"] in self._urls:
                continue
            self.vector_store.upsert(row["id"], emb)
            self._cache[row["id"]] = row
            self._urls.add(row["url"])
            added += 1
        return added

    def ingest_query(self, query: NewsQuery) -> int:
        if not self.live_ingestion_enabled or self.ingestion_service is None:
            return 0

        rows = self.ingestion_service.fetch_articles(query)
        added = self._upsert_rows(rows)
        logger.info("Ingestion fetched=%s added=%s", len(rows), added)
        return added

    def run(self, query: NewsQuery) -> List[RankedArticle]:
        self.ingest_query(query)
        query_embedding = self.embedding_service.embed([query.query])[0]
        candidate_count = min(max(query.max_articles * 4, query.max_articles), max(len(self._cache), query.max_articles))
        matches = self.vector_store.search(query_embedding, candidate_count)
        results: List[RankedArticle] = []
        for article_id, score in matches:
            raw = self._cache[article_id]
            cleaned = clean_article_text(raw["text"])
            results.append(
                RankedArticle(
                    id=raw["id"],
                    title=raw["title"],
                    source=raw["source"],
                    date=raw["date"],
                    url=raw["url"],
                    image_path=raw.get("image_path"),
                    relevance_score=round(score, 4),
                    snippet=raw["snippet"],
                    cleaned_text=cleaned,
                )
            )
        results.sort(key=self._ranking_sort_key, reverse=True)
        return results[: query.max_articles]

    def _ranking_sort_key(self, article: RankedArticle) -> tuple[float, str]:
        adjusted_score = article.relevance_score + source_quality_score(article.url)
        return (adjusted_score, article.date)
