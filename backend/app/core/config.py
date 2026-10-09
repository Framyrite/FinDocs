"""Typed settings loaded from the environment and backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Settings shared by the application."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="FINDOCS_",
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
    )

    app_name: str = Field(default="FinDocs Backend", min_length=1)
    debug: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read and validate configuration once per process."""
    return Settings()
