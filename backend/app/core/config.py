from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE_PATH = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "Multimodal News Intelligence Agent"
    app_env: str = "development"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: Optional[str] = None

    mock_mode: bool = True
    sample_data_path: str = "sample_data/articles.json"
    live_ingestion_enabled: bool = False
    news_api_key: Optional[str] = None
    news_api_base_url: str = "https://newsapi.org/v2"
    news_api_language: str = "en"
    news_api_page_size: int = 30
    ingestion_timeout_seconds: int = 12
    ingestion_extract_full_text: bool = False
    ingestion_article_timeout_seconds: int = 8
    ingestion_full_text_max_articles: int = 6
    ingestion_full_text_max_workers: int = 4
    ingestion_use_newspaper: bool = False
    ingestion_max_runtime_seconds: int = 180
    ingestion_placeholder_image_url: Optional[str] = "https://via.placeholder.com/1280x720?text=No+Image"

    embedding_provider: str = "local"
    embedding_model_name: str = "sentence-transformers/all-mpnet-base-v2"
    vector_db_path: str = "backend/.chroma"
    vector_store_backend: str = "memory"
    vector_store_database_url: Optional[str] = None
    vector_store_table_name: str = "article_embeddings"
    vector_store_dimension: int = 32
    max_articles_default: int = 5

    vision_provider: str = "local"
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"

    synthesis_provider: str = "openai"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: Optional[str] = None

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, env_file_encoding="utf-8", extra="ignore")

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def app_env_normalized(self) -> str:
        return self.app_env.strip().lower() or "development"

    @property
    def is_production(self) -> bool:
        return self.app_env_normalized == "production"

    @property
    def cors_allowed_origins(self) -> list[str]:
        if self.frontend_origins:
            parsed_origins = [
                origin.rstrip("/")
                for origin in (item.strip() for item in self.frontend_origins.split(","))
                if origin
            ]
            if parsed_origins:
                return parsed_origins
        origin = (self.frontend_origin or "").strip() or "http://localhost:5173"
        return [origin.rstrip("/")]

    @property
    def env_file_path(self) -> Path:
        return ENV_FILE_PATH

    @property
    def news_api_key_present(self) -> bool:
        return bool((self.news_api_key or "").strip())

    @property
    def resolved_sample_data_path(self) -> Path:
        path = Path(self.sample_data_path)
        if path.is_absolute():
            return path
        return self.project_root / path

    @property
    def resolved_sample_data_dir(self) -> Path:
        return self.resolved_sample_data_path.parent


@lru_cache
def get_settings() -> Settings:
    return Settings()
