from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Protocol

from app.models.schemas import RankedArticle, VisualInsight

logger = logging.getLogger(__name__)


class VisionLLMClient(Protocol):
    async def analyze(self, article: RankedArticle) -> str:
        ...


class VisionAgent:
    def __init__(self, mock_mode: bool = True, llm_client: VisionLLMClient | None = None):
        self.mock_mode = mock_mode
        self.llm_client = llm_client

    async def run(self, ranked_articles: List[RankedArticle]) -> List[VisualInsight]:
        insights: List[VisualInsight] = []
        for article in ranked_articles:
            llm_insight = await self._analyze_with_llm(article)
            insights.append(llm_insight or self._build_fallback_insight(article))
        return insights

    async def _analyze_with_llm(self, article: RankedArticle) -> VisualInsight | None:
        if self.mock_mode or self.llm_client is None or not article.image_path:
            return None

        try:
            llm_response = await self.llm_client.analyze(article)
        except Exception as exc:
            logger.warning("Vision LLM request failed for article %s (%s). Falling back to heuristic vision.", article.id, exc)
            return None

        payload = self._parse_json_payload(llm_response)
        if payload is None:
            logger.warning("Vision LLM returned unparseable output for article %s. Falling back to heuristic vision.", article.id)
            return None

        summary = self._as_non_empty_str(payload.get("image_summary"))
        theme = self._as_non_empty_str(payload.get("detected_theme"))
        relevance = self._coerce_relevance(payload.get("relevance_to_article"))
        elements = self._coerce_string_list(payload.get("notable_visual_elements"))
        confidence = self._coerce_score(payload.get("confidence_score"), fallback=0.84)

        if not summary or not theme:
            return None

        return VisualInsight(
            article_id=article.id,
            image_summary=summary,
            detected_theme=theme,
            relevance_to_article=relevance,
            notable_visual_elements=elements or self._elements_for_theme(theme),
            confidence_score=confidence,
        )

    def _build_fallback_insight(self, article: RankedArticle) -> VisualInsight:
        theme = self._infer_theme(article)
        return VisualInsight(
            article_id=article.id,
            image_summary=f"Image suggests {theme.lower()} context supporting the article narrative.",
            detected_theme=theme,
            relevance_to_article="high" if article.relevance_score > 0.55 else "medium",
            notable_visual_elements=self._elements_for_theme(theme),
            confidence_score=0.78 if self.mock_mode else 0.84,
        )

    def _infer_theme(self, article: RankedArticle) -> str:
        text = f"{article.title} {article.snippet}".lower()
        if "shipping" in text or "maritime" in text:
            return "Maritime logistics and security"
        if "semiconductor" in text or "chip" in text:
            return "Semiconductor supply chain"
        if "ai" in text or "regulation" in text:
            return "AI governance and policy"
        if "iran" in text or "military" in text or "missile" in text:
            return "Regional security and geopolitics"
        return "General geopolitical context"

    def _elements_for_theme(self, theme: str) -> List[str]:
        mapping = {
            "Maritime logistics and security": ["cargo vessel", "naval activity", "trade route visuals"],
            "Semiconductor supply chain": ["chip wafers", "fab equipment", "industrial cleanroom"],
            "AI governance and policy": ["hearing room", "policy documents", "technology displays"],
            "Regional security and geopolitics": ["military hardware", "national symbols", "official briefing imagery"],
        }
        return mapping.get(theme, ["contextual scene", "human actors", "environmental cues"])

    def _parse_json_payload(self, text: str) -> dict[str, Any] | None:
        candidates = [text.strip()]
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1).strip())
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1].strip())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    def _as_non_empty_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _coerce_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        items: List[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items

    def _coerce_score(self, value: Any, fallback: float) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = fallback
        return max(0.0, min(1.0, score))

    def _coerce_relevance(self, value: Any) -> str:
        text = str(value).strip().lower()
        if text in {"high", "medium", "low"}:
            return text
        return "medium"
