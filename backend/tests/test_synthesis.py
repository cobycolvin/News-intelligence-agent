import pytest
from app.agents.synthesis_agent import SynthesisAgent
from app.models.schemas import NewsQuery, RankedArticle, SynthesisInput, VisualInsight


@pytest.mark.asyncio
async def test_synthesis_mock_report_sections():
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
    report = await agent.run(SynthesisInput(query=NewsQuery(query="test"), ranked_articles=ranked, visual_insights=visual))
    assert report.executive_summary
    assert len(report.sections) >= 5
