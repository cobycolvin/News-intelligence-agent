import asyncio

from app.core.dependencies import get_orchestrator
from app.models.schemas import NewsQuery


def test_e2e_mock_pipeline_flow():
    orchestrator = get_orchestrator()
    result = asyncio.run(orchestrator.run(NewsQuery(query="semiconductor export controls", max_articles=4)))
    assert len(result.ranked_articles) == 4
    assert len(result.visual_insights) == 4
    assert "Executive" not in result.final_report.executive_summary or len(result.final_report.executive_summary) > 10
