"""Punto de entrada de la API de CoachIA.

Arranque local:  uv run uvicorn app.main:app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health, internal
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, request_context_middleware
from app.core.security import TokenVerifier
from app.db.session import Database
from app.integrations.strava.router import router as strava_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    app.state.database.dispose()


def create_app(
    settings: Settings | None = None,
    *,
    token_verifier: TokenVerifier | None = None,
    database: Database | None = None,
) -> FastAPI:
    """Crea la aplicación. Los parámetros permiten inyectar dependencias en los tests."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    is_production = settings.environment == "production"
    app = FastAPI(
        title="CoachIA API",
        version=__version__,
        docs_url=None if is_production else "/docs",
        redoc_url=None,
        openapi_url=None if is_production else "/openapi.json",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.token_verifier = token_verifier or TokenVerifier(settings)
    app.state.database = database or Database.from_settings(settings)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
    app.middleware("http")(request_context_middleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(api_v1_router)
    app.include_router(internal.router)
    app.include_router(strava_router)
    return app


app = create_app()
