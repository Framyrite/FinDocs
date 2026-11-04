import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("FINDOCS_APP_NAME", raising=False)
    monkeypatch.delenv("FINDOCS_DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "FinDocs Backend"
    assert settings.debug is False


def test_settings_from_environment(monkeypatch):
    monkeypatch.setenv("FINDOCS_APP_NAME", "Custom FinDocs")
    monkeypatch.setenv("FINDOCS_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Custom FinDocs"
    assert settings.debug is True


def test_settings_from_dotenv(tmp_path, monkeypatch):
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


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'FINDOCS_APP_NAME="From dotenv"\n',
        encoding="utf-8",
    )

    monkeypatch.setenv("FINDOCS_APP_NAME", "From environment")

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "From environment"


def test_settings_rejects_empty_app_name(monkeypatch):
    monkeypatch.setenv("FINDOCS_APP_NAME", "   ")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_invalid_debug(monkeypatch):
    monkeypatch.setenv("FINDOCS_DEBUG", "not-a-boolean")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_create_app_does_not_cache_settings(monkeypatch):
    monkeypatch.setenv("FINDOCS_APP_NAME", "First application")
    first_app = create_app()

    monkeypatch.setenv("FINDOCS_APP_NAME", "Second application")
    second_app = create_app()

    assert first_app.title == "First application"
    assert second_app.title == "Second application"
    assert first_app is not second_app


def test_create_app_respects_explicit_settings(monkeypatch):
    monkeypatch.setenv("FINDOCS_APP_NAME", "From environment")

    settings = Settings(
        _env_file=None,
        app_name="Explicit settings",
        debug=True,
    )

    application = create_app(settings=settings)

    assert application.title == "Explicit settings"
    assert application.debug is True
