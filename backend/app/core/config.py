"""Typed settings loaded from the environment and backend/.env."""

from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
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

    data_dir: Path = DEFAULT_DATA_DIR
    max_txt_size_mb: int = Field(default=10, ge=1)
    max_documents: int = Field(default=100, ge=1)

    llm_provider: Literal["mock", "ollama"] = "mock"

    ollama_base_url: HttpUrl = Field(
        default="http://127.0.0.1:11434",
        validate_default=True,
    )

    llm_model: str = Field(
        default="qwen3.5:4b-q4_K_M",
        min_length=1,
    )

    llm_timeout_seconds: float = Field(
        default=120,
        gt=0,
    )

    llm_temperature: float = Field(
        default=0,
        ge=0,
        le=2,
    )

    llm_max_output_tokens: int = Field(
        default=512,
        gt=0,
    )

    llm_context_tokens: int = Field(
        default=4096,
        gt=0,
    )

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url(cls, value: HttpUrl) -> HttpUrl:
        if value.username is not None or value.password is not None:
            raise ValueError("Ollama URL must not contain credentials")
        return value
