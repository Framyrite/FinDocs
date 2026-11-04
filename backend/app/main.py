"""Application creation and module wiring."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import Settings
from app.llm.adapter import LLMAdapter
from app.llm.mock import MockLLM


def create_app(
    settings: Settings | None = None,
    llm_adapter: LLMAdapter | None = None,
) -> FastAPI:
    config = Settings() if settings is None else settings
    adapter = MockLLM() if llm_adapter is None else llm_adapter

    application = FastAPI(title=config.app_name, debug=config.debug)
    application.state.llm_adapter = adapter
    application.include_router(health_router)
    return application


app = create_app()
