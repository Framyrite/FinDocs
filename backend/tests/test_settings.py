"""Regression tests for settings validation, configuration sources, and isolation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check documented defaults without reading the developer's local .env."""
    monkeypatch.delenv("FINDOCS_APP_NAME", raising=False)
    monkeypatch.delenv("FINDOCS_DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "FinDocs Backend"
    assert settings.debug is False


def test_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure FINDOCS_ variables are read and boolean strings are parsed correctly."""
    monkeypatch.setenv("FINDOCS_APP_NAME", "Custom FinDocs")
    monkeypatch.setenv("FINDOCS_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Custom FinDocs"
    assert settings.debug is True


def test_settings_from_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Load configuration from an isolated temporary .env file."""
    monkeypatch.delenv("FINDOCS_APP_NAME", raising=False)
    monkeypatch.delenv("FINDOCS_DEBUG", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        'FINDOCS_APP_NAME="From dotenv"\nFINDOCS_DEBUG=true\n',
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "From dotenv"
    assert settings.debug is True


def test_environment_overrides_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify process environment variables take priority over .env values."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        'FINDOCS_APP_NAME="From dotenv"\n',
        encoding="utf-8",
    )

    monkeypatch.setenv("FINDOCS_APP_NAME", "From environment")

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "From environment"


def test_settings_rejects_empty_app_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject whitespace-only names after automatic whitespace stripping."""
    monkeypatch.setenv("FINDOCS_APP_NAME", "   ")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_invalid_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise a validation error instead of silently falling back to False."""
    monkeypatch.setenv("FINDOCS_DEBUG", "not-a-boolean")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_create_app_does_not_cache_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each application creation reads the current environment independently."""
    monkeypatch.setenv("FINDOCS_APP_NAME", "First application")
    first_app = create_app()

    monkeypatch.setenv("FINDOCS_APP_NAME", "Second application")
    second_app = create_app()

    assert first_app.title == "First application"
    assert second_app.title == "Second application"
    assert first_app is not second_app


def test_create_app_respects_explicit_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure injected settings override environment values during app creation."""
    monkeypatch.setenv("FINDOCS_APP_NAME", "From environment")

    settings = Settings(
        _env_file=None,
        app_name="Explicit settings",
        debug=True,
    )

    application = create_app(settings=settings)

    assert application.title == "Explicit settings"
    assert application.debug is True


def test_document_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the backend data directory and documented document limits."""
    for name in (
        "FINDOCS_DATA_DIR",
        "FINDOCS_MAX_TXT_SIZE_MB",
        "FINDOCS_MAX_DOCUMENTS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.data_dir == Path(__file__).resolve().parents[1] / "data"
    assert settings.max_txt_size_mb == 10
    assert settings.max_documents == 100


def test_document_settings_from_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow overriding the storage directory and document limits."""
    data_dir = tmp_path / "custom-data"

    monkeypatch.setenv("FINDOCS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("FINDOCS_MAX_TXT_SIZE_MB", "5")
    monkeypatch.setenv("FINDOCS_MAX_DOCUMENTS", "20")

    settings = Settings(_env_file=None)

    assert settings.data_dir == data_dir
    assert settings.max_txt_size_mb == 5
    assert settings.max_documents == 20


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("FINDOCS_MAX_TXT_SIZE_MB", "0"),
        ("FINDOCS_MAX_DOCUMENTS", "0"),
        ("FINDOCS_MAX_DOCUMENTS", "not-a-number"),
    ],
)
def test_document_settings_reject_invalid_limits(
    name: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject zero, negative, and nonnumeric document limits."""
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
