"""Endpoints internos para automatizaciones (n8n). Protegidos con la cabecera X-Internal-API-Key."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import require_internal_api_key

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_api_key)]
)


class PingResponse(BaseModel):
    status: Literal["ok"]


@router.get("/ping")
def ping() -> PingResponse:
    """Permite a n8n comprobar que la API responde y que su clave es correcta."""
    return PingResponse(status="ok")
