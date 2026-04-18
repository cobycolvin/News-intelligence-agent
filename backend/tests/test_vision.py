import asyncio
import json

from app.agents.vision_agent import VisionAgent
from app.models.schemas import RankedArticle


class FakeVisionClient:
    async def analyze(self, article: RankedArticle) -> str:
        del article
        return json.dumps(
            {
                "image_summary": "A podium scene with officials and national flags.",
                "detected_theme": "Regional security and geopolitics",
                "relevance_to_article": "high",
                "notable_visual_elements": ["podium", "national flags", "official briefing room"],
                "confidence_score": 0.91,
            }
        )


def _article(image_path: str | None = "sample_data/images/shipping.svg") -> RankedArticle:
    return RankedArticle(
        id="a1",
        title="Shipping disruptions intensify",
        source="Demo",
        date="2026-03-01",
        url="https://example.com",
        image_path=image_path,
        relevance_score=0.9,
        snippet="maritime",
        cleaned_text="Some cleaned text",
    )


def test_vision_schema_output():
    agent = VisionAgent(mock_mode=True)
    insights = asyncio.run(agent.run([_article()]))
    assert insights[0].article_id == "a1"
    assert isinstance(insights[0].notable_visual_elements, list)


def test_vision_llm_output_is_used_when_available():
    agent = VisionAgent(mock_mode=False, llm_client=FakeVisionClient())
    insights = asyncio.run(agent.run([_article("https://example.com/image.jpg")]))

    assert insights[0].detected_theme == "Regional security and geopolitics"
    assert insights[0].relevance_to_article == "high"
    assert insights[0].confidence_score == 0.91


def test_vision_falls_back_when_no_image_is_available():
    agent = VisionAgent(mock_mode=False, llm_client=FakeVisionClient())
    insights = asyncio.run(agent.run([_article(None)]))

    assert insights[0].article_id == "a1"
    assert insights[0].detected_theme == "Maritime logistics and security"
