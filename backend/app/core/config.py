from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multimodal News Intelligence Agent"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    mock_mode: bool = True
    sample_data_path: str = "sample_data/articles.json"

    embedding_provider: str = "local"
    embedding_model_name: str = "sentence-transformers/all-mpnet-base-v2"
    vector_db_path: str = "backend/.chroma"
    max_articles_default: int = 5

    vision_provider: str = "local"
    clip_model_name: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"

    synthesis_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
