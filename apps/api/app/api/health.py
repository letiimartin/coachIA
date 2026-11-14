"""Health checks: /health (vivo) y /health/ready (dependencias listas)."""

import logging
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import __version__
from app.api.deps import DatabaseDep

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

CheckStatus = Literal["ok", "error", "not_configured"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, CheckStatus]


class RootResponse(BaseModel):
    name: str
    version: str
    health: str


@router.get("/")
def root() -> RootResponse:
    return RootResponse(name="CoachIA API", version=__version__, health="/health")


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness(database: DatabaseDep) -> JSONResponse:
    db_status: CheckStatus
    if not database.configured:
        db_status = "not_configured"
    else:
        try:
            database.ping()
            db_status = "ok"
        except Exception:
            logger.exception("La base de datos no responde")
            db_status = "error"

    body = ReadinessResponse(
        status="degraded" if db_status == "error" else "ok", checks={"database": db_status}
    )
    return JSONResponse(body.model_dump(), status_code=503 if db_status == "error" else 200)
