from functools import lru_cache
import logging

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.vision_agent import VisionAgent
from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.openai_client import OpenAIClient
from app.services.ollama_client import OllamaClient
from app.services.orchestrator import NewsPipelineOrchestrator
from app.services.sample_data import SampleDataRepository

logger = logging.getLogger(__name__)


@lru_cache
def get_orchestrator() -> NewsPipelineOrchestrator:
    settings = get_settings()
    repository = SampleDataRepository(str(settings.resolved_sample_data_path))
    embedding_service = EmbeddingService(settings.embedding_model_name, mock_mode=settings.mock_mode)
    retrieval = RetrievalAgent(repository, embedding_service)
    vision = VisionAgent(mock_mode=settings.mock_mode)
    llm_client = None
    if not settings.mock_mode:
        provider = settings.synthesis_provider.strip().lower()
        if provider == "openai":
            if settings.openai_api_key:
                llm_client = OpenAIClient(
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    base_url=settings.openai_base_url,
                )
            else:
                logger.warning("SYNTHESIS_PROVIDER=openai but OPENAI_API_KEY is missing. Falling back to mock synthesis.")
        elif provider == "ollama":
            llm_client = OllamaClient(settings.ollama_base_url, settings.ollama_model)
        else:
            logger.warning("Unknown SYNTHESIS_PROVIDER '%s'. Falling back to mock synthesis.", settings.synthesis_provider)
    synthesis = SynthesisAgent(use_mock=settings.mock_mode, llm_client=llm_client)
    return NewsPipelineOrchestrator(retrieval, vision, synthesis)
