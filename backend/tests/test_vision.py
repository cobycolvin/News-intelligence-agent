from app.agents.vision_agent import VisionAgent
from app.models.schemas import RankedArticle


def test_vision_schema_output():
    agent = VisionAgent(mock_mode=True)
    articles = [
        RankedArticle(
            id="a1",
            title="Shipping disruptions intensify",
            source="Demo",
            date="2026-03-01",
            url="https://example.com",
            image_path="sample_data/images/shipping.svg",
            relevance_score=0.9,
            snippet="maritime",
            cleaned_text="Some cleaned text",
        )
    ]
    insights = agent.run(articles)
    assert insights[0].article_id == "a1"
    assert isinstance(insights[0].notable_visual_elements, list)
