"""Typed settings loaded from the environment and backend/.env."""

from pathlib import Path

from pydantic import Field
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
