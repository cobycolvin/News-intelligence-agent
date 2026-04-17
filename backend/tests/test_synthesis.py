import asyncio
import json

from app.agents.synthesis_agent import SynthesisAgent
from app.models.schemas import NewsQuery, RankedArticle, SynthesisInput, VisualInsight


class FakeLLMClient:
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        del prompt, system_prompt
        return json.dumps(
            {
                "executive_summary": "LLM executive summary",
                "sections": [
                    {
                        "heading": "Key Developments",
                        "content": "Structured synthesis content",
                        "evidence_article_ids": ["a1"],
                    }
                ],
                "confidence": {
                    "score": 0.88,
                    "notes": "Consistent evidence across sources.",
                    "uncertainty_factors": ["Fast-moving events"],
                },
            }
        )


def test_synthesis_mock_report_sections():
    agent = SynthesisAgent(use_mock=True)
    ranked = [
        RankedArticle(
            id="a1", title="A", source="S", date="2026-01-01", url="https://x", image_path=None,
            relevance_score=0.8, snippet="s", cleaned_text="c"
        )
    ]
    visual = [
        VisualInsight(
            article_id="a1", image_summary="summary", detected_theme="theme", relevance_to_article="high",
            notable_visual_elements=["x"], confidence_score=0.8
        )
    ]
    report = asyncio.run(agent.run(SynthesisInput(query=NewsQuery(query="test"), ranked_articles=ranked, visual_insights=visual)))
    assert report.executive_summary
    assert len(report.sections) >= 5


def test_synthesis_llm_structured_report_used():
    ranked = [
        RankedArticle(
            id="a1",
            title="A",
            source="S",
            date="2026-01-01",
            url="https://x",
            image_path=None,
            relevance_score=0.8,
            snippet="s",
            cleaned_text="c",
        )
    ]
    visual = [
        VisualInsight(
            article_id="a1",
            image_summary="summary",
            detected_theme="theme",
            relevance_to_article="high",
            notable_visual_elements=["x"],
            confidence_score=0.8,
        )
    ]
    agent = SynthesisAgent(use_mock=False, llm_client=FakeLLMClient())
    report = asyncio.run(agent.run(SynthesisInput(query=NewsQuery(query="test"), ranked_articles=ranked, visual_insights=visual)))
    assert report.executive_summary == "LLM executive summary"
    assert report.sections[0].heading == "Key Developments"
    assert report.sections[0].evidence[0].article_id == "a1"
    assert report.confidence.score == 0.88
