"""Application entry point. Run with: uvicorn app.main:app"""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Ecom Research System",
        description="Internal ecommerce product research and decision system.",
        version="0.1.0",
    )
    register_error_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
