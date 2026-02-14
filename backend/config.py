from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    postgres_user: str = "knowledge"
    postgres_password: str = "knowledge_pass"
    postgres_db: str = "knowledge_assistant"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Anthropic
    anthropic_api_key: str = ""

    # Embedding
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dimension: int = 1024

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-base"

    # Application
    debug: bool = False
    log_level: str = "INFO"

    # Search
    search_top_k: int = 20
    rerank_top_k: int = 5

    # Paths
    base_dir: Path = Path(__file__).parent.parent


@lru_cache
def get_settings() -> Settings:
    return Settings()
