from __future__ import annotations

import importlib
import logging
import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from hashlib import sha1
from html import unescape
from threading import Lock
from time import monotonic
from typing import Any, Callable, Dict, List

import httpx

from app.models.schemas import NewsQuery

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., None]


class NewsIngestionService:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://newsapi.org/v2",
        language: str = "en",
        page_size: int = 30,
        timeout_seconds: int = 12,
        extract_full_text: bool = False,
        article_timeout_seconds: int = 8,
        full_text_max_articles: int = 6,
        full_text_max_workers: int = 4,
        use_newspaper: bool = False,
        max_runtime_seconds: int = 180,
        placeholder_image_url: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.language = language
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.extract_full_text = extract_full_text
        self.article_timeout_seconds = article_timeout_seconds
        self.full_text_max_articles = max(0, full_text_max_articles)
        self.full_text_max_workers = max(1, full_text_max_workers)
        self.use_newspaper = use_newspaper
        self.max_runtime_seconds = max(15, max_runtime_seconds)
        self.placeholder_image_url = placeholder_image_url
        self._article_text_cache: Dict[str, str | None] = {}
        self._cache_lock = Lock()

    def fetch_articles(
        self,
        query: NewsQuery,
        progress_callback: ProgressCallback | None = None,
        known_urls: set[str] | None = None,
    ) -> List[dict[str, Any]]:
        known_urls = known_urls or set()
        deadline = monotonic() + self.max_runtime_seconds
        params = {
            "q": query.query,
            "language": self.language,
            "sortBy": "publishedAt",
            "pageSize": max(query.max_articles, min(self.page_size, query.max_articles * 4)),
        }
        if query.date_from:
            params["from"] = query.date_from.isoformat()
        if query.date_to:
            params["to"] = query.date_to.isoformat()

        url = f"{self.base_url}/everything"
        headers = {"X-Api-Key": self.api_key}
        self._emit_progress(
            progress_callback,
            state="fetching_news_api",
            message="Fetching articles from NewsAPI.",
            progress_current=0,
            progress_total=1,
            meta={"query": query.query},
        )
        self._check_deadline(deadline)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("News ingestion request failed: %s", exc)
            return []

        payload = response.json()
        raw_articles = payload.get("articles", [])
        candidates, skipped_known = self._build_candidates(raw_articles, known_urls)
        self._emit_progress(
            progress_callback,
            state="fetching_news_api",
            message="NewsAPI response normalized.",
            progress_current=1,
            progress_total=1,
            meta={
                "raw_articles": len(raw_articles),
                "candidate_articles": len(candidates),
                "skipped_existing_urls": skipped_known,
            },
        )
        if not candidates:
            return []

        if self.extract_full_text:
            self._apply_full_text_extraction(candidates, progress_callback, deadline)

        rows: List[dict[str, Any]] = []
        for candidate in candidates:
            rows.append(
                {
                    "id": candidate["id"],
                    "title": candidate["title"],
                    "source": candidate["source"],
                    "date": candidate["date"],
                    "url": candidate["url"],
                    "image_path": candidate["image_path"],
                    "snippet": candidate["snippet"],
                    "text": candidate["text"] or candidate["snippet"] or candidate["title"],
                }
            )
        return rows

    def _build_candidates(self, articles: list[dict[str, Any]], known_urls: set[str]) -> tuple[list[dict[str, Any]], int]:
        candidates: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        skipped_known = 0

        for item in articles:
            title = (item.get("title") or "").strip()
            article_url = (item.get("url") or "").strip()
            if not title or not article_url:
                continue
            if article_url in known_urls:
                skipped_known += 1
                continue
            if article_url in seen_urls:
                continue

            seen_urls.add(article_url)
            snippet = (item.get("description") or "").strip()
            body = (item.get("content") or "").strip()
            source_name = ((item.get("source") or {}).get("name") or "Unknown").strip()
            date_str = self._normalize_date(item.get("publishedAt"))
            image_url = (item.get("urlToImage") or "").strip() or self.placeholder_image_url
            article_id = sha1(article_url.encode("utf-8")).hexdigest()[:16]
            candidates.append(
                {
                    "id": article_id,
                    "title": title,
                    "source": source_name,
                    "date": date_str,
                    "url": article_url,
                    "image_path": image_url,
                    "snippet": snippet or title,
                    "text": body or snippet or title,
                }
            )

        return candidates, skipped_known

    def _normalize_article(self, item: Dict[str, Any]) -> dict[str, Any] | None:
        title = (item.get("title") or "").strip()
        article_url = (item.get("url") or "").strip()
        if not title or not article_url:
            return None

        snippet = (item.get("description") or "").strip()
        body = (item.get("content") or "").strip()
        if self.extract_full_text:
            extracted_body = self._extract_article_text(article_url)
            if extracted_body:
                body = extracted_body
        if not body:
            body = snippet or title

        source_name = ((item.get("source") or {}).get("name") or "Unknown").strip()
        date_str = self._normalize_date(item.get("publishedAt"))
        image_url = (item.get("urlToImage") or "").strip() or self.placeholder_image_url
        article_id = sha1(article_url.encode("utf-8")).hexdigest()[:16]

        return {
            "id": article_id,
            "title": title,
            "source": source_name,
            "date": date_str,
            "url": article_url,
            "image_path": image_url,
            "snippet": snippet or title,
            "text": body,
        }

    def _apply_full_text_extraction(
        self,
        candidates: list[dict[str, Any]],
        progress_callback: ProgressCallback | None,
        deadline: float,
    ) -> None:
        to_extract = [c for c in candidates if self._needs_full_text(c)]
        if self.full_text_max_articles > 0:
            to_extract = to_extract[: self.full_text_max_articles]
        total = len(to_extract)
        if total == 0:
            return

        self._emit_progress(
            progress_callback,
            state="extracting_article_text",
            message="Extracting full article text from source URLs.",
            progress_current=0,
            progress_total=total,
            meta={"full_text_enabled": True},
        )

        completed = 0
        with ThreadPoolExecutor(max_workers=self.full_text_max_workers) as executor:
            pending = {executor.submit(self._extract_article_text, candidate["url"]): candidate for candidate in to_extract}
            try:
                while pending:
                    self._check_deadline(deadline)
                    done, _ = wait(pending.keys(), timeout=1, return_when=FIRST_COMPLETED)
                    if not done:
                        continue
                    for future in done:
                        candidate = pending.pop(future)
                        extracted_text: str | None = None
                        try:
                            extracted_text = future.result()
                        except Exception as exc:
                            logger.debug("Full-text extraction failed for %s: %s", candidate["url"], exc)
                        if extracted_text:
                            candidate["text"] = extracted_text
                        completed += 1
                        self._emit_progress(
                            progress_callback,
                            state="extracting_article_text",
                            message="Extracting full article text from source URLs.",
                            progress_current=completed,
                            progress_total=total,
                            meta={"full_text_enabled": True},
                        )
            except TimeoutError:
                for future in pending:
                    future.cancel()
                raise

    def _needs_full_text(self, candidate: dict[str, Any]) -> bool:
        text = (candidate.get("text") or "").strip()
        if not text:
            return True
        if len(text) < 220:
            return True
        return "[+" in text and "chars]" in text

    def _normalize_date(self, published_at: Any) -> str:
        if not published_at:
            return datetime.now(timezone.utc).date().isoformat()
        try:
            return datetime.fromisoformat(str(published_at).replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return datetime.now(timezone.utc).date().isoformat()

    def _extract_article_text(self, url: str) -> str | None:
        with self._cache_lock:
            if url in self._article_text_cache:
                return self._article_text_cache[url]

        text = self._extract_with_http(url)
        if not text and self.use_newspaper:
            text = self._extract_with_newspaper(url)

        with self._cache_lock:
            self._article_text_cache[url] = text
        return text

    def _extract_with_newspaper(self, url: str) -> str | None:
        try:
            newspaper = importlib.import_module("newspaper")
            article_cls = getattr(newspaper, "Article")
            config_cls = getattr(newspaper, "Config", None)
        except Exception:
            return None

        try:
            if callable(config_cls):
                config = config_cls()
                config.request_timeout = max(1, int(self.article_timeout_seconds))
                article = article_cls(url, config=config)
            else:
                article = article_cls(url)
            article.download()
            article.parse()
        except Exception as exc:
            logger.debug("newspaper extraction failed for %s: %s", url, exc)
            return None

        text = (article.text or "").strip()
        return text or None

    def _extract_with_http(self, url: str) -> str | None:
        try:
            with httpx.Client(timeout=self.article_timeout_seconds, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.debug("HTTP extraction failed for %s: %s", url, exc)
            return None

        text = self._strip_html(response.text)
        return text if len(text) >= 120 else None

    def _strip_html(self, html: str) -> str:
        no_scripts = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        no_styles = re.sub(r"<style[^>]*>.*?</style>", " ", no_scripts, flags=re.IGNORECASE | re.DOTALL)
        raw_text = re.sub(r"<[^>]+>", " ", no_styles)
        normalized = re.sub(r"\s+", " ", unescape(raw_text)).strip()
        return normalized

    def _check_deadline(self, deadline: float) -> None:
        if monotonic() > deadline:
            raise TimeoutError(f"Live ingestion timed out after {self.max_runtime_seconds} seconds.")

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
