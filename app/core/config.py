from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "IDEAS SaaS API"
    environment: str = "dev"
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ideas_saas",
        alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    nicegui_storage_secret: str = Field(default="change-me-storage", alias="NICEGUI_STORAGE_SECRET")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4o", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    rag_allow_external_fallback: bool = Field(default=True, alias="RAG_ALLOW_EXTERNAL_FALLBACK")
    rag_external_max_sources: int = Field(default=3, alias="RAG_EXTERNAL_MAX_SOURCES")
    rag_external_timeout_seconds: float = Field(default=8.0, alias="RAG_EXTERNAL_TIMEOUT_SECONDS")


settings = Settings()
