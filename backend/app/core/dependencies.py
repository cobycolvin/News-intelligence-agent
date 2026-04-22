from functools import lru_cache
import logging

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.vision_agent import VisionAgent
from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_tasks import IngestionTaskStore
from app.services.news_ingestion_service import NewsIngestionService
from app.services.openai_client import OpenAIClient
from app.services.openai_vision_client import OpenAIVisionClient
from app.services.ollama_client import OllamaClient
from app.services.orchestrator import NewsPipelineOrchestrator
from app.services.sample_data import SampleDataRepository
from app.services.vector_store import create_vector_store

logger = logging.getLogger(__name__)


@lru_cache
def get_ingestion_task_store() -> IngestionTaskStore:
    return IngestionTaskStore()


@lru_cache
def get_orchestrator() -> NewsPipelineOrchestrator:
    settings = get_settings()
    news_api_key = (settings.news_api_key or "").strip() or None
    repository = SampleDataRepository(str(settings.resolved_sample_data_path))
    embedding_service = EmbeddingService(settings.embedding_model_name, mock_mode=settings.mock_mode)
    vector_store = create_vector_store(
        backend=settings.vector_store_backend,
        database_url=settings.vector_store_database_url,
        table_name=settings.vector_store_table_name,
        dimension=settings.vector_store_dimension,
    )
    ingestion_service = None
    if settings.live_ingestion_enabled and news_api_key:
        ingestion_service = NewsIngestionService(
            api_key=news_api_key,
            base_url=settings.news_api_base_url,
            language=settings.news_api_language,
            page_size=settings.news_api_page_size,
            timeout_seconds=settings.ingestion_timeout_seconds,
            extract_full_text=settings.ingestion_extract_full_text,
            article_timeout_seconds=settings.ingestion_article_timeout_seconds,
            full_text_max_articles=settings.ingestion_full_text_max_articles,
            full_text_max_workers=settings.ingestion_full_text_max_workers,
            use_newspaper=settings.ingestion_use_newspaper,
            max_runtime_seconds=settings.ingestion_max_runtime_seconds,
            placeholder_image_url=settings.ingestion_placeholder_image_url,
        )
    elif settings.live_ingestion_enabled:
        logger.warning("LIVE_INGESTION_ENABLED=true but NEWS_API_KEY is missing or empty. /api/ingest will return 503.")
    elif news_api_key:
        logger.info("NEWS_API_KEY is set but LIVE_INGESTION_ENABLED=false. Live ingestion remains disabled.")
    retrieval = RetrievalAgent(
        repository,
        embedding_service,
        ingestion_service=ingestion_service,
        live_ingestion_enabled=settings.live_ingestion_enabled,
        vector_store=vector_store,
    )
    vision_llm_client = None
    vision_provider = settings.vision_provider.strip().lower()
    if not settings.mock_mode and vision_provider == "openai":
        if settings.openai_api_key:
            vision_llm_client = OpenAIVisionClient(
                api_key=settings.openai_api_key,
                model=settings.openai_vision_model or settings.openai_model,
                base_url=settings.openai_base_url,
                project_root=settings.project_root,
            )
        else:
            logger.warning("VISION_PROVIDER=openai but OPENAI_API_KEY is missing. Falling back to heuristic vision.")
    elif vision_provider not in {"local", "openai"}:
        logger.warning("Unknown VISION_PROVIDER '%s'. Falling back to heuristic vision.", settings.vision_provider)

    vision = VisionAgent(mock_mode=settings.mock_mode, llm_client=vision_llm_client)
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
