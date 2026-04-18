from __future__ import annotations

from collections import Counter
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
                system_prompt=self._build_system_prompt(synthesis_input.query.report_depth),
            )
        except Exception as exc:
            logger.warning("Synthesis LLM request failed (%s). Falling back to grounded report.", exc)
            return self._build_mock_report(synthesis_input.query, synthesis_input.ranked_articles, synthesis_input.visual_insights)

        parsed = self._build_report_from_llm_response(
            query=synthesis_input.query,
            articles=synthesis_input.ranked_articles,
            visual_insights=synthesis_input.visual_insights,
            llm_response=llm_response,
        )
        if parsed is not None:
            return parsed

        logger.warning("Synthesis LLM returned unparseable output. Falling back to grounded report.")
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
        ordered_articles = self._sort_articles_for_status(articles)
        evidence = self._default_evidence(ordered_articles)
        executive = override_summary or self._build_executive_summary(query, ordered_articles)
        sections = [
            ReportSection(
                heading="Current Status",
                content=self._build_current_status(query, ordered_articles),
                evidence=evidence,
            ),
            ReportSection(
                heading="Recent Developments",
                content=self._build_recent_developments(query, ordered_articles),
                evidence=evidence,
            ),
            ReportSection(
                heading="Military and Diplomatic Signals",
                content=self._build_signal_summary(query, ordered_articles),
                evidence=evidence,
            ),
            ReportSection(
                heading="Visual Evidence",
                content=self._build_visual_context(query, visual_insights),
                evidence=evidence,
            ),
            ReportSection(
                heading="What To Watch",
                content=self._build_watchpoints(query, ordered_articles),
                evidence=evidence,
            ),
        ]
        if query.report_depth == "in_depth":
            sections.insert(
                3,
                ReportSection(
                    heading="Where Sources Agree and Differ",
                    content=self._build_source_agreement_summary(ordered_articles),
                    evidence=evidence,
                ),
            )
        confidence = self._build_confidence(ordered_articles, visual_insights)
        return self._build_final_report(query, executive, sections, confidence, ordered_articles)

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

    def _build_system_prompt(self, report_depth: str) -> str:
        depth_instruction = (
            "Produce a richer, more explanatory report. Use longer sections, explain why developments matter, "
            "surface areas of agreement and disagreement across sources, and provide a more complete current-status picture."
            if report_depth == "in_depth"
            else "Produce a concise but informative report that gives the user a fast status update."
        )
        return (
            "You are a multimodal news intelligence synthesis agent. "
            "Return only valid JSON matching this schema: "
            '{"executive_summary":"string",'
            '"sections":[{"heading":"string","content":"string","evidence_article_ids":["article-id"]}],'
            '"confidence":{"score":0.0,"notes":"string","uncertainty_factors":["string"]}}. '
            "Use only supplied evidence. Prioritize the freshest developments using article dates. "
            "The report should clearly tell the user the current status, recent developments, military or diplomatic signals, "
            "points of disagreement, and what to watch next. "
            f"{depth_instruction} "
            "Avoid boilerplate, repetition, and generic geopolitical language. "
            "Create 4-6 sections. Set confidence.score between 0 and 1."
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
                    f"  cleaned_text: {article.cleaned_text[:1000]}"
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
            f"Requested report depth: {synthesis_input.query.report_depth}\n\n"
            "Write for a reader who wants to understand the current status quickly. "
            "Anchor every section in the supplied evidence and cite the article ids that support each section.\n\n"
            "Ranked article evidence:\n"
            f"{article_context}\n\n"
            "Visual evidence:\n"
            f"{visual_context}\n"
        )

    def _sort_articles_for_status(self, articles: List[RankedArticle]) -> List[RankedArticle]:
        return sorted(articles, key=lambda article: (article.date, article.relevance_score), reverse=True)

    def _build_executive_summary(self, query: NewsQuery, articles: List[RankedArticle]) -> str:
        if not articles:
            return f"No relevant articles were available to assess the current status of '{query.query}'."
        latest = articles[0]
        top_titles = ", ".join(article.source for article in articles[:3])
        return (
            f"Latest coverage on '{query.query}' indicates the story is still evolving. "
            f"The freshest high-relevance source in this set is '{latest.title}' from {latest.source} ({latest.date}), "
            f"with additional reporting from {top_titles}."
        )

    def _build_current_status(self, query: NewsQuery, articles: List[RankedArticle]) -> str:
        if not articles:
            return "Current status could not be established because no ranked articles were available."
        latest = articles[: (4 if query.report_depth == "in_depth" else 3)]
        parts = [
            f"As of {latest[0].date}, the strongest current-status signal comes from {latest[0].source}, which reports: {self._best_excerpt(latest[0])}."
        ]
        if len(latest) > 1:
            parts.append(f"Recent follow-on coverage also highlights {self._best_excerpt(latest[1])}.")
        if len(latest) > 2:
            parts.append(f"A third source adds that {self._best_excerpt(latest[2])}.")
        if query.report_depth == "in_depth" and len(latest) > 3:
            parts.append(f"A fourth notable source, {latest[3].source}, frames the situation as {self._best_excerpt(latest[3])}.")
        return " ".join(parts)

    def _build_recent_developments(self, query: NewsQuery, articles: List[RankedArticle]) -> str:
        if not articles:
            return "No developments were available in the ranked article set."
        lines = []
        limit = 6 if query.report_depth == "in_depth" else 4
        for article in articles[:limit]:
            lines.append(f"{article.date}: {article.source} says {self._best_excerpt(article)}")
        return " ".join(lines)

    def _build_signal_summary(self, query: NewsQuery, articles: List[RankedArticle]) -> str:
        if not articles:
            return "No military or diplomatic signals could be extracted."
        military_keywords = {"strike", "missile", "navy", "blockade", "military", "attack", "security", "front"}
        diplomatic_keywords = {"talk", "ceasefire", "negotiat", "official", "diplomat", "meeting", "ultimatum"}
        military_hits = []
        diplomatic_hits = []
        for article in articles[:6]:
            text = f"{article.title} {article.snippet} {article.cleaned_text}".lower()
            if any(keyword in text for keyword in military_keywords):
                military_hits.append(article)
            if any(keyword in text for keyword in diplomatic_keywords):
                diplomatic_hits.append(article)

        statements = []
        if military_hits:
            article = military_hits[0]
            statements.append(f"Military reporting emphasizes {self._best_excerpt(article)}")
        if diplomatic_hits:
            article = diplomatic_hits[0]
            statements.append(f"Diplomatic coverage points to {self._best_excerpt(article)}")
        if query.report_depth == "in_depth" and len(diplomatic_hits) > 1:
            statements.append(f"Additional diplomatic framing appears in {diplomatic_hits[1].source}, which highlights {self._best_excerpt(diplomatic_hits[1])}")
        if not statements:
            statements.append("The article set mixes security and political framing, but no single military or diplomatic thread dominates.")
        return " ".join(statements)

    def _build_visual_context(self, query: NewsQuery, visual_insights: List[VisualInsight]) -> str:
        if not visual_insights:
            return "No visual insights were produced for the ranked articles."
        themes = [insight.detected_theme for insight in visual_insights if insight.detected_theme]
        theme_counts = Counter(themes)
        top_themes = ", ".join(theme for theme, _ in theme_counts.most_common(3))
        summaries = []
        limit = 5 if query.report_depth == "in_depth" else 3
        for insight in visual_insights[:limit]:
            elements = ", ".join(insight.notable_visual_elements[:3])
            summaries.append(f"{insight.detected_theme}: {insight.image_summary} Key elements include {elements}.")
        prefix = f"Across the ranked images, the dominant visual themes are {top_themes}. " if top_themes else ""
        return prefix + " ".join(summaries)

    def _build_watchpoints(self, query: NewsQuery, articles: List[RankedArticle]) -> str:
        if not articles:
            return "No watchpoints could be identified."
        watch_terms = []
        corpus = " ".join(f"{article.title} {article.snippet} {article.cleaned_text}" for article in articles[:6]).lower()
        if any(term in corpus for term in ["ceasefire", "talk", "negotiat"]):
            watch_terms.append("whether negotiations or ceasefire talks hold")
        if any(term in corpus for term in ["blockade", "hormuz", "shipping", "navy"]):
            watch_terms.append("whether maritime disruption widens")
        if any(term in corpus for term in ["strike", "missile", "front", "attack"]):
            watch_terms.append("whether direct attacks or retaliation intensify")
        if any(term in corpus for term in ["ultimatum", "sanction", "trump", "official"]):
            watch_terms.append("whether outside political pressure changes the timeline")
        if not watch_terms:
            watch_terms.append("whether the next 24-72 hours produce clearer confirmation from primary sources")
        suffix = " These are the decision points most likely to change the status picture quickly." if query.report_depth == "in_depth" else ""
        return "Key watchpoints are " + "; ".join(watch_terms) + "." + suffix

    def _build_source_agreement_summary(self, articles: List[RankedArticle]) -> str:
        if not articles:
            return "There were not enough sources to compare areas of agreement and disagreement."
        phrases = [self._best_excerpt(article) for article in articles[:5]]
        agreement = f"Across the strongest-ranked sources, there is broad agreement that {phrases[0]}" if phrases else ""
        divergence = ""
        if len(phrases) > 1:
            divergence = (
                f" The main differences are in emphasis: one source focuses on {phrases[1].lower()} while another stresses "
                f"{phrases[2].lower()}" if len(phrases) > 2 else f" The main differences are in emphasis: another source stresses {phrases[1].lower()}"
            )
        return agreement + divergence

    def _build_confidence(self, articles: List[RankedArticle], visual_insights: List[VisualInsight]) -> ConfidenceAssessment:
        score = 0.55
        if len(articles) >= 3:
            score += 0.12
        if len({article.source for article in articles}) >= 3:
            score += 0.08
        if visual_insights:
            score += 0.05
        score = min(score, 0.87)
        return ConfidenceAssessment(
            score=score,
            notes="Confidence is based on source count, source diversity, and whether the retrieved articles point in a similar direction.",
            uncertainty_factors=[
                "Events may be moving faster than publication cycles",
                "Some sources may frame the same developments differently",
                "Image availability and quality vary across retrieved articles",
            ],
        )

    def _best_excerpt(self, article: RankedArticle) -> str:
        candidates = [article.snippet, article.cleaned_text, article.title]
        for candidate in candidates:
            text = self._clean_sentence(candidate)
            if text:
                return text
        return article.title

    def _clean_sentence(self, text: str) -> str:
        cleaned = " ".join(str(text).split()).strip()
        if not cleaned:
            return ""
        cleaned = re.sub(r"\s*\[[^\]]+\]\s*", " ", cleaned)
        if len(cleaned) > 220:
            trimmed = cleaned[:220].rsplit(" ", 1)[0]
            cleaned = trimmed or cleaned[:220]
        return cleaned.rstrip(" .") + "."

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
