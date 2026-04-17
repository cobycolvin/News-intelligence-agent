from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, List, Protocol

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

logger = logging.getLogger(__name__)


class SynthesisLLMClient(Protocol):
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        ...


class SynthesisAgent:
    def __init__(self, use_mock: bool, llm_client: SynthesisLLMClient | None = None):
        self.use_mock = use_mock
        self.llm_client = llm_client

    async def run(self, synthesis_input: SynthesisInput) -> FinalReport:
        if self.use_mock or self.llm_client is None:
            return self._build_mock_report(synthesis_input.query, synthesis_input.ranked_articles, synthesis_input.visual_insights)

        try:
            llm_response = await self.llm_client.generate(
                self._build_prompt(synthesis_input),
                system_prompt=self._build_system_prompt(),
            )
        except Exception as exc:
            logger.warning("Synthesis LLM request failed (%s). Falling back to mock report.", exc)
            return self._build_mock_report(synthesis_input.query, synthesis_input.ranked_articles, synthesis_input.visual_insights)

        parsed = self._build_report_from_llm_response(
            query=synthesis_input.query,
            articles=synthesis_input.ranked_articles,
            visual_insights=synthesis_input.visual_insights,
            llm_response=llm_response,
        )
        if parsed is not None:
            return parsed

        logger.warning("Synthesis LLM returned unparseable output. Falling back to mock report.")
        return self._build_mock_report(
            query=synthesis_input.query,
            articles=synthesis_input.ranked_articles,
            visual_insights=synthesis_input.visual_insights,
            override_summary=self._safe_text_preview(llm_response),
        )

    def _build_mock_report(
        self,
        query: NewsQuery,
        articles: List[RankedArticle],
        visual_insights: List[VisualInsight],
        override_summary: str | None = None,
    ) -> FinalReport:
        evidence = self._default_evidence(articles)
        sections = [
            ReportSection(
                heading="Key Developments",
                content="; ".join([f"{a.title} ({a.source})" for a in articles[:4]]),
                evidence=evidence,
            ),
            ReportSection(
                heading="Important Visual Context",
                content=" ".join(v.image_summary for v in visual_insights[:3]),
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
        executive = override_summary or (
            f"This report analyzed {len(articles)} high-relevance articles for '{query.query}', "
            "combining textual evidence with image-derived context to produce traceable intelligence findings."
        )
        confidence = ConfidenceAssessment(
            score=0.79,
            notes="Strong topical overlap across sources.",
            uncertainty_factors=["Rapidly evolving events", "Limited primary imagery metadata"],
        )
        return self._build_final_report(query, executive, sections, confidence, articles)

    def _build_report_from_llm_response(
        self,
        query: NewsQuery,
        articles: List[RankedArticle],
        visual_insights: List[VisualInsight],
        llm_response: str,
    ) -> FinalReport | None:
        payload = self._parse_json_payload(llm_response)
        if payload is None:
            return None

        executive = self._as_non_empty_str(payload.get("executive_summary"))
        if not executive:
            executive = (
                f"Structured synthesis generated for '{query.query}' using {len(articles)} ranked sources and "
                f"{len(visual_insights)} visual insights."
            )

        article_lookup = {article.id: article for article in articles}
        default_evidence = self._default_evidence(articles)
        sections: List[ReportSection] = []
        raw_sections = payload.get("sections", [])
        if isinstance(raw_sections, list):
            for section in raw_sections:
                if not isinstance(section, dict):
                    continue
                heading = self._as_non_empty_str(section.get("heading"))
                content = self._as_non_empty_str(section.get("content"))
                if not heading or not content:
                    continue
                evidence = self._resolve_evidence(section.get("evidence_article_ids"), article_lookup) or default_evidence
                sections.append(ReportSection(heading=heading, content=content, evidence=evidence))

        if not sections:
            return None

        confidence_payload = payload.get("confidence", {})
        if not isinstance(confidence_payload, dict):
            confidence_payload = {}
        confidence = ConfidenceAssessment(
            score=self._coerce_score(confidence_payload.get("score"), fallback=0.75),
            notes=self._as_non_empty_str(confidence_payload.get("notes")) or "Confidence estimated by LLM synthesis.",
            uncertainty_factors=self._coerce_string_list(confidence_payload.get("uncertainty_factors")),
        )
        return self._build_final_report(query, executive, sections, confidence, articles)

    def _build_final_report(
        self,
        query: NewsQuery,
        executive: str,
        sections: List[ReportSection],
        confidence: ConfidenceAssessment,
        articles: List[RankedArticle],
    ) -> FinalReport:
        markdown = self._to_markdown(query.query, executive, sections, articles)
        return FinalReport(
            query=query.query,
            executive_summary=executive,
            sections=sections,
            confidence=confidence,
            sources=[a.model_dump(include={"id", "title", "source", "date", "url", "image_path"}) for a in articles],
            markdown_export=markdown,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _default_evidence(self, articles: List[RankedArticle]) -> List[EvidenceRef]:
        return [EvidenceRef(article_id=a.id, title=a.title, url=a.url) for a in articles[:3]]

    def _resolve_evidence(self, evidence_article_ids: Any, article_lookup: dict[str, RankedArticle]) -> List[EvidenceRef]:
        if not isinstance(evidence_article_ids, list):
            return []
        refs: List[EvidenceRef] = []
        seen: set[str] = set()
        for item in evidence_article_ids:
            article_id = str(item).strip()
            if not article_id or article_id in seen:
                continue
            article = article_lookup.get(article_id)
            if not article:
                continue
            seen.add(article_id)
            refs.append(EvidenceRef(article_id=article.id, title=article.title, url=article.url))
        return refs

    def _to_markdown(self, query: str, executive: str, sections: List[ReportSection], articles: List[RankedArticle]) -> str:
        lines = ["# Multimodal News Intelligence Report", f"**Query:** {query}", "## Executive Summary", executive]
        for section in sections:
            lines.append(f"\n## {section.heading}\n{section.content}")
            if section.evidence:
                lines.append("Evidence:")
                for evidence in section.evidence:
                    lines.append(f"- [{evidence.title}]({evidence.url})")
        lines.append("\n## Sources")
        for article in articles:
            lines.append(f"- [{article.title}]({article.url}) - {article.source} ({article.date})")
        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        return (
            "You are a multimodal news intelligence synthesis agent. "
            "Return only valid JSON matching this schema: "
            '{"executive_summary":"string",'
            '"sections":[{"heading":"string","content":"string","evidence_article_ids":["article-id"]}],'
            '"confidence":{"score":0.0,"notes":"string","uncertainty_factors":["string"]}}. '
            "Use only supplied evidence. Create 4-6 sections. "
            "Set confidence.score between 0 and 1."
        )

    def _build_prompt(self, synthesis_input: SynthesisInput) -> str:
        article_context = "\n".join(
            [
                (
                    f"- id: {article.id}\n"
                    f"  title: {article.title}\n"
                    f"  source: {article.source}\n"
                    f"  date: {article.date}\n"
                    f"  url: {article.url}\n"
                    f"  snippet: {article.snippet}\n"
                    f"  cleaned_text: {article.cleaned_text[:700]}"
                )
                for article in synthesis_input.ranked_articles
            ]
        )
        visual_context = "\n".join(
            [
                (
                    f"- article_id: {insight.article_id}\n"
                    f"  theme: {insight.detected_theme}\n"
                    f"  summary: {insight.image_summary}\n"
                    f"  elements: {', '.join(insight.notable_visual_elements)}\n"
                    f"  relevance: {insight.relevance_to_article}\n"
                    f"  confidence_score: {insight.confidence_score}"
                )
                for insight in synthesis_input.visual_insights
            ]
        )
        return (
            "User query:\n"
            f"{synthesis_input.query.query}\n\n"
            "Ranked article evidence:\n"
            f"{article_context}\n\n"
            "Visual evidence:\n"
            f"{visual_context}\n"
        )

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
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
        return None

    def _safe_text_preview(self, text: str, limit: int = 900) -> str:
        cleaned = " ".join(text.split())
        return cleaned[:limit] if cleaned else ""

    def _as_non_empty_str(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text

    def _coerce_score(self, value: Any, fallback: float) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = fallback
        return max(0.0, min(1.0, score))

    def _coerce_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        items = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
