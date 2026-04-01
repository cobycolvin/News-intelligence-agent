from __future__ import annotations

import logging
from typing import List

from app.models.schemas import NewsQuery, RankedArticle
from app.services.embedding_service import EmbeddingService
from app.services.sample_data import SampleDataRepository
from app.services.vector_store import InMemoryVectorStore
from app.utils.text import clean_article_text

logger = logging.getLogger(__name__)


class RetrievalAgent:
    def __init__(self, repository: SampleDataRepository, embedding_service: EmbeddingService):
        self.repository = repository
        self.embedding_service = embedding_service
        self.vector_store = InMemoryVectorStore()
        self._cache: dict[str, dict] = {}
        self._index_articles()

    def _index_articles(self) -> None:
        rows = self.repository.load_articles()
        texts = [f"{r['title']} {r['snippet']} {r['text']}" for r in rows]
        embeddings = self.embedding_service.embed(texts)
        for row, emb in zip(rows, embeddings):
            self.vector_store.upsert(row["id"], emb)
            self._cache[row["id"]] = row
        logger.info("Indexed %s articles", len(rows))

    def run(self, query: NewsQuery) -> List[RankedArticle]:
        query_embedding = self.embedding_service.embed([query.query])[0]
        matches = self.vector_store.search(query_embedding, query.max_articles)
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
        return results
