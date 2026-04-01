from __future__ import annotations

from typing import List

from app.models.schemas import RankedArticle, VisualInsight


class VisionAgent:
    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

    def run(self, ranked_articles: List[RankedArticle]) -> List[VisualInsight]:
        insights: List[VisualInsight] = []
        for article in ranked_articles:
            theme = self._infer_theme(article)
            insights.append(
                VisualInsight(
                    article_id=article.id,
                    image_summary=f"Image suggests {theme.lower()} context supporting the article narrative.",
                    detected_theme=theme,
                    relevance_to_article="high" if article.relevance_score > 0.55 else "medium",
                    notable_visual_elements=self._elements_for_theme(theme),
                    confidence_score=0.78 if self.mock_mode else 0.84,
                )
            )
        return insights

    def _infer_theme(self, article: RankedArticle) -> str:
        text = f"{article.title} {article.snippet}".lower()
        if "shipping" in text or "maritime" in text:
            return "Maritime logistics and security"
        if "semiconductor" in text or "chip" in text:
            return "Semiconductor supply chain"
        if "ai" in text or "regulation" in text:
            return "AI governance and policy"
        return "General geopolitical context"

    def _elements_for_theme(self, theme: str) -> List[str]:
        mapping = {
            "Maritime logistics and security": ["cargo vessel", "naval activity", "trade route visuals"],
            "Semiconductor supply chain": ["chip wafers", "fab equipment", "industrial cleanroom"],
            "AI governance and policy": ["hearing room", "policy documents", "technology displays"],
        }
        return mapping.get(theme, ["contextual scene", "human actors", "environmental cues"])
