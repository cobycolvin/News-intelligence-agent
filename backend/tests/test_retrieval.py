from pathlib import Path

from app.agents.retrieval_agent import RetrievalAgent
from app.models.schemas import NewsQuery
from app.services.embedding_service import EmbeddingService
from app.services.sample_data import SampleDataRepository


def test_retrieval_returns_ranked_articles():
    sample_data_path = Path(__file__).resolve().parents[2] / "sample_data" / "articles.json"
    repo = SampleDataRepository(str(sample_data_path))
    agent = RetrievalAgent(repo, EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True))
    output = agent.run(NewsQuery(query="Red Sea shipping disruptions", max_articles=3))
    assert len(output) == 3
    assert output[0].relevance_score >= output[-1].relevance_score
