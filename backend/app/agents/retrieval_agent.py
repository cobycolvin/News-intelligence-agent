from __future__ import annotations

import logging
from threading import Lock
from typing import Any, Callable, List

from app.models.schemas import NewsQuery, RankedArticle
from app.services.embedding_service import EmbeddingService
from app.services.news_ingestion_service import NewsIngestionService
from app.services.sample_data import SampleDataRepository
from app.services.vector_store import InMemoryVectorStore, VectorStore
from app.utils.source_quality import is_source_allowed, source_quality_score
from app.utils.text import clean_article_text

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., None]


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
        self._cache: dict[str, dict[str, Any]] = {}
        self._urls: set[str] = set()
        self._index_lock = Lock()
        self._sample_indexed = False

    def _ensure_sample_index(self, progress_callback: ProgressCallback | None = None) -> None:
        if self._sample_indexed:
            return
        with self._index_lock:
            if self._sample_indexed:
                return
            self.vector_store.clear()
            self._cache.clear()
            self._urls.clear()
            rows = self.repository.load_articles()
            self._upsert_rows(
                rows,
                progress_callback=progress_callback,
                embedding_state="warming_embeddings",
                indexing_state="warming_embeddings",
                embedding_message="Warming embeddings and indexing baseline sample corpus.",
                indexing_message="Warming embeddings and indexing baseline sample corpus.",
            )
            self._sample_indexed = True
            logger.info("Indexed %s sample articles", len(rows))

    def _upsert_rows(
        self,
        rows: List[dict],
        progress_callback: ProgressCallback | None = None,
        *,
        embedding_state: str = "embedding_articles",
        indexing_state: str = "indexing_articles",
        embedding_message: str = "Generating embeddings for articles.",
        indexing_message: str = "Indexing articles into vector store.",
    ) -> int:
        if not rows:
            return 0

        total = len(rows)
        self._emit_progress(
            progress_callback,
            state=embedding_state,
            message=embedding_message,
            progress_current=0,
            progress_total=total,
            meta={"candidate_articles": total},
        )
        texts = [f"{r['title']} {r['snippet']} {r['text']}" for r in rows]
        embeddings = self.embedding_service.embed(texts)
        self._emit_progress(
            progress_callback,
            state=indexing_state,
            message=indexing_message,
            progress_current=0,
            progress_total=total,
            meta={"candidate_articles": total},
        )

        added = 0
        for processed, (row, emb) in enumerate(zip(rows, embeddings), start=1):
            if not is_source_allowed(row["url"]):
                logger.info("Skipping blocked source during indexing: %s", row["url"])
                self._emit_progress(
                    progress_callback,
                    state=indexing_state,
                    message=indexing_message,
                    progress_current=processed,
                    progress_total=total,
                    meta={"indexed_articles": added, "processed_articles": processed},
                )
                continue
            if row["url"] in self._urls:
                self._emit_progress(
                    progress_callback,
                    state=indexing_state,
                    message=indexing_message,
                    progress_current=processed,
                    progress_total=total,
                    meta={"indexed_articles": added, "processed_articles": processed},
                )
                continue
            self.vector_store.upsert(row["id"], emb)
            self._cache[row["id"]] = row
            self._urls.add(row["url"])
            added += 1
            self._emit_progress(
                progress_callback,
                state=indexing_state,
                message=indexing_message,
                progress_current=processed,
                progress_total=total,
                meta={"indexed_articles": added, "processed_articles": processed},
            )
        return added

    def ingest_query(self, query: NewsQuery, progress_callback: ProgressCallback | None = None) -> int:
        if not self.live_ingestion_enabled or self.ingestion_service is None:
            return 0

        self._ensure_sample_index(progress_callback=progress_callback)
        rows: list[dict]
        try:
            rows = self.ingestion_service.fetch_articles(
                query,
                progress_callback=progress_callback,
                known_urls=set(self._urls),
            )
        except TypeError:
            # Backward compatibility for tests and simple fake services.
            rows = self.ingestion_service.fetch_articles(query)
        added = self._upsert_rows(
            rows,
            progress_callback=progress_callback,
            embedding_state="embedding_articles",
            indexing_state="indexing_articles",
            embedding_message="Generating embeddings for live articles.",
            indexing_message="Indexing live articles into vector store.",
        )
        logger.info("Ingestion fetched=%s added=%s", len(rows), added)
        return added

    def run(self, query: NewsQuery) -> List[RankedArticle]:
        self._ensure_sample_index()
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

    def _emit_progress(
        self,
        callback: ProgressCallback | None,
        *,
        state: str,
        message: str,
        progress_current: int | None = None,
        progress_total: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if callback is None:
            return
        try:
            callback(
                state=state,
                message=message,
                progress_current=progress_current,
                progress_total=progress_total,
                meta=meta,
            )
        except Exception:
            logger.debug("Progress callback failed for state=%s", state, exc_info=True)
