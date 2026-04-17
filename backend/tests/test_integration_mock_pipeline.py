import asyncio
from pathlib import Path

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.vision_agent import VisionAgent
from app.core.dependencies import get_orchestrator
from app.models.schemas import NewsQuery
from app.services.embedding_service import EmbeddingService
from app.services.orchestrator import NewsPipelineOrchestrator
from app.services.sample_data import SampleDataRepository


def test_e2e_mock_pipeline_flow():
    orchestrator = get_orchestrator()
    result = asyncio.run(orchestrator.run(NewsQuery(query="semiconductor export controls", max_articles=4)))
    assert len(result.ranked_articles) == 4
    assert len(result.visual_insights) == 4
    assert "Executive" not in result.final_report.executive_summary or len(result.final_report.executive_summary) > 10


class _PersistentLikeVectorStore:
    def __init__(self):
        self.cleared = False
        self.ids: list[str] = []
        self.embeddings: dict[str, list[float]] = {}

    def upsert(self, item_id, embedding):
        if item_id not in self.ids:
            self.ids.append(item_id)
        self.embeddings[item_id] = list(embedding)

    def search(self, query_embedding, top_k):
        ordered = self.ids[:top_k]
        return [(item_id, 0.88) for item_id in ordered]

    def clear(self):
        self.cleared = True
        self.ids.clear()
        self.embeddings.clear()


def test_e2e_pipeline_flow_with_persistent_store_like_backend():
    sample_data_path = Path(__file__).resolve().parents[2] / "sample_data" / "articles.json"
    repository = SampleDataRepository(str(sample_data_path))
    vector_store = _PersistentLikeVectorStore()
    retrieval = RetrievalAgent(
        repository=repository,
        embedding_service=EmbeddingService("sentence-transformers/all-mpnet-base-v2", mock_mode=True),
        vector_store=vector_store,
    )
    orchestrator = NewsPipelineOrchestrator(
        retrieval_agent=retrieval,
        vision_agent=VisionAgent(mock_mode=True),
        synthesis_agent=SynthesisAgent(use_mock=True),
    )

    result = asyncio.run(orchestrator.run(NewsQuery(query="trade disruption", max_articles=3)))

    assert vector_store.cleared is True
    assert len(vector_store.embeddings) > 0
    assert len(result.ranked_articles) == 3
    assert len(result.visual_insights) == 3
    assert len(result.final_report.sources) == 3
