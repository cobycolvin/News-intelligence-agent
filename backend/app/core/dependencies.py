from functools import lru_cache

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.vision_agent import VisionAgent
from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient
from app.services.orchestrator import NewsPipelineOrchestrator
from app.services.sample_data import SampleDataRepository


@lru_cache
def get_orchestrator() -> NewsPipelineOrchestrator:
    settings = get_settings()
    repository = SampleDataRepository(settings.sample_data_path)
    embedding_service = EmbeddingService(settings.embedding_model_name, mock_mode=settings.mock_mode)
    retrieval = RetrievalAgent(repository, embedding_service)
    vision = VisionAgent(mock_mode=settings.mock_mode)
    ollama_client = None if settings.mock_mode else OllamaClient(settings.ollama_base_url, settings.ollama_model)
    synthesis = SynthesisAgent(use_mock=settings.mock_mode, ollama_client=ollama_client)
    return NewsPipelineOrchestrator(retrieval, vision, synthesis)
