import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()


def _resolve_log_level(level_name: str) -> int:
    level = getattr(logging, level_name.upper(), logging.INFO)
    return level if isinstance(level, int) else logging.INFO


logging.basicConfig(
    level=_resolve_log_level(settings.log_level),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials="*" not in settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
async def log_startup_configuration() -> None:
    logger.info(
        "Runtime settings | app_env=%s host=%s port=%s env_file=%s env_exists=%s cors_origins=%s mock_mode=%s live_ingestion_enabled=%s news_api_key_present=%s vector_store_dimension=%s ingestion_extract_full_text=%s ingestion_full_text_max_articles=%s ingestion_full_text_max_workers=%s ingestion_max_runtime_seconds=%s",
        settings.app_env_normalized,
        settings.app_host,
        settings.app_port,
        settings.env_file_path,
        settings.env_file_path.exists(),
        settings.cors_allowed_origins,
        settings.mock_mode,
        settings.live_ingestion_enabled,
        settings.news_api_key_present,
        settings.vector_store_dimension,
        settings.ingestion_extract_full_text,
        settings.ingestion_full_text_max_articles,
        settings.ingestion_full_text_max_workers,
        settings.ingestion_max_runtime_seconds,
    )
    if settings.is_production and any("localhost" in origin for origin in settings.cors_allowed_origins):
        logger.warning(
            "APP_ENV=production but CORS origins still include localhost values: %s. "
            "Set FRONTEND_ORIGIN or FRONTEND_ORIGINS for your deployed domain.",
            settings.cors_allowed_origins,
        )

sample_data_dir = Path(settings.resolved_sample_data_dir)
if sample_data_dir.exists():
    app.mount("/sample_data", StaticFiles(directory=str(sample_data_dir)), name="sample_data")
else:
    logging.warning("Sample data directory not found: %s", sample_data_dir)
