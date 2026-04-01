from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.models.schemas import (
    ConfidenceAssessment,
    EvidenceRef,
    FinalReport,
    NewsQuery,
    RankedArticle,
    ReportSection,
    SynthesisInput,
    VisualInsight,
)
from app.services.ollama_client import OllamaClient


class SynthesisAgent:
    def __init__(self, use_mock: bool, ollama_client: OllamaClient | None = None):
        self.use_mock = use_mock
        self.ollama_client = ollama_client

    async def run(self, synthesis_input: SynthesisInput) -> FinalReport:
        if self.use_mock or self.ollama_client is None:
            return self._build_mock_report(synthesis_input.query, synthesis_input.ranked_articles, synthesis_input.visual_insights)

        prompt = self._build_prompt(synthesis_input)
        response_text = await self.ollama_client.generate(prompt)
        return self._build_mock_report(synthesis_input.query, synthesis_input.ranked_articles, synthesis_input.visual_insights, override_summary=response_text[:900])

    def _build_mock_report(
        self,
        query: NewsQuery,
        articles: List[RankedArticle],
        visual_insights: List[VisualInsight],
        override_summary: str | None = None,
    ) -> FinalReport:
        evidence = [EvidenceRef(article_id=a.id, title=a.title, url=a.url) for a in articles[:3]]
        visual_lines = " ".join(v.image_summary for v in visual_insights[:3])

        sections = [
            ReportSection(
                heading="Key Developments",
                content="; ".join([f"{a.title} ({a.source})" for a in articles[:4]]),
                evidence=evidence,
            ),
            ReportSection(
                heading="Important Visual Context",
                content=visual_lines,
                evidence=evidence,
            ),
            ReportSection(
                heading="Cross-Article Themes",
                content="Recurring themes include supply chain resilience, policy coordination, and operational risk management.",
                evidence=evidence,
            ),
            ReportSection(
                heading="Notable Differences or Tensions",
                content="Some sources emphasize deterrence and policy response, while others focus on immediate cost and schedule disruptions.",
                evidence=evidence,
            ),
            ReportSection(
                heading="Confidence / Uncertainty Notes",
                content="Confidence is moderate-high due to consistent cross-source signals; uncertainty remains around escalation timing and policy enforcement details.",
                evidence=evidence,
            ),
        ]
        executive = override_summary or f"This report analyzed {len(articles)} high-relevance articles for '{query.query}', combining textual evidence with image-derived context to produce traceable intelligence findings."
        markdown = self._to_markdown(query.query, executive, sections, articles)
        return FinalReport(
            query=query.query,
            executive_summary=executive,
            sections=sections,
            confidence=ConfidenceAssessment(score=0.79, notes="Strong topical overlap across sources.", uncertainty_factors=["Rapidly evolving events", "Limited primary imagery metadata"]),
            sources=[a.model_dump(include={"id", "title", "source", "date", "url", "image_path"}) for a in articles],
            markdown_export=markdown,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _to_markdown(self, query: str, executive: str, sections: List[ReportSection], articles: List[RankedArticle]) -> str:
        lines = [f"# Multimodal News Intelligence Report\n", f"**Query:** {query}\n", "## Executive Summary", executive]
        for section in sections:
            lines.append(f"\n## {section.heading}\n{section.content}")
        lines.append("\n## Sources")
        for article in articles:
            lines.append(f"- [{article.title}]({article.url}) — {article.source} ({article.date})")
        return "\n".join(lines)

    def _build_prompt(self, synthesis_input: SynthesisInput) -> str:
        article_context = "\n".join([f"- {a.title}: {a.snippet}" for a in synthesis_input.ranked_articles])
        visual_context = "\n".join([f"- {v.article_id}: {v.image_summary}" for v in synthesis_input.visual_insights])
        return (
            "Create a concise intelligence summary with key developments and uncertainty notes.\n"
            f"User query: {synthesis_input.query.query}\n"
            f"Articles:\n{article_context}\n"
            f"Visual findings:\n{visual_context}\n"
        )
