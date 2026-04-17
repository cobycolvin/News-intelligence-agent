from __future__ import annotations

import logging
import importlib
import re
from datetime import datetime, timezone
from html import unescape
from hashlib import sha1
from typing import Any, Dict, List

import httpx

from app.models.schemas import NewsQuery

logger = logging.getLogger(__name__)


class NewsIngestionService:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://newsapi.org/v2",
        language: str = "en",
        page_size: int = 30,
        timeout_seconds: int = 12,
        extract_full_text: bool = True,
        article_timeout_seconds: int = 8,
        placeholder_image_url: str | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.language = language
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self.extract_full_text = extract_full_text
        self.article_timeout_seconds = article_timeout_seconds
        self.placeholder_image_url = placeholder_image_url

    def fetch_articles(self, query: NewsQuery) -> List[dict[str, Any]]:
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

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("News ingestion request failed: %s", exc)
            return []

        payload = response.json()
        rows: List[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for item in payload.get("articles", []):
            normalized = self._normalize_article(item)
            if not normalized:
                continue
            url_value = normalized["url"]
            if url_value in seen_urls:
                continue
            seen_urls.add(url_value)
            rows.append(normalized)

        return rows

    def _normalize_article(self, item: Dict[str, Any]) -> dict[str, Any] | None:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        if not title or not url:
            return None

        snippet = (item.get("description") or "").strip()
        body = (item.get("content") or "").strip()
        if self.extract_full_text:
            extracted_body = self._extract_article_text(url)
            if extracted_body:
                body = extracted_body
        if not body:
            body = snippet or title

        source_name = ((item.get("source") or {}).get("name") or "Unknown").strip()
        date_str = self._normalize_date(item.get("publishedAt"))
        image_url = (item.get("urlToImage") or "").strip() or self.placeholder_image_url
        article_id = sha1(url.encode("utf-8")).hexdigest()[:16]

        return {
            "id": article_id,
            "title": title,
            "source": source_name,
            "date": date_str,
            "url": url,
            "image_path": image_url,
            "snippet": snippet or title,
            "text": body,
        }

    def _normalize_date(self, published_at: Any) -> str:
        if not published_at:
            return datetime.now(timezone.utc).date().isoformat()
        try:
            # NewsAPI emits ISO timestamps like 2026-04-16T08:20:00Z
            return datetime.fromisoformat(str(published_at).replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return datetime.now(timezone.utc).date().isoformat()

    def _extract_article_text(self, url: str) -> str | None:
        text = self._extract_with_newspaper(url)
        if text:
            return text
        return self._extract_with_http(url)

    def _extract_with_newspaper(self, url: str) -> str | None:
        try:
            newspaper = importlib.import_module("newspaper")
            article_cls = getattr(newspaper, "Article")
        except Exception:
            return None

        try:
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
        return text if len(text) >= 80 else None

    def _strip_html(self, html: str) -> str:
        no_scripts = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        no_styles = re.sub(r"<style[^>]*>.*?</style>", " ", no_scripts, flags=re.IGNORECASE | re.DOTALL)
        raw_text = re.sub(r"<[^>]+>", " ", no_styles)
        normalized = re.sub(r"\s+", " ", unescape(raw_text)).strip()
        return normalized
