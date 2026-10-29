"""App settings, read from environment variables and the .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["groq", "gemini"] = "groq"
    # SecretStr hides the value when printed or logged: it shows '**********'.
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-20b"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    chroma_dir: str = "data/chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()
