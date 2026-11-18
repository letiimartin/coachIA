"""Piezas comunes de los schemas de la API: formato de error y respuestas documentadas."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Formato de todas las respuestas de error de la API."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": {"code": "unauthorized", "message": "Autenticación requerida."},
                    "request_id": "6f1c2a8e3b9d4f7a",
                }
            ]
        }
    )

    error: ErrorDetail
    request_id: str | None


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Documenta en OpenAPI las respuestas de error indicadas (siempre incluye 401 y 501)."""
    descriptions = {
        401: "Falta el JWT o no es válido.",
        404: "Recurso no encontrado.",
        409: "Conflicto con el estado actual.",
        422: "Datos no válidos o que no permiten completar la operación.",
        429: "Límite de peticiones de un servicio externo.",
        502: "Un servicio externo no ha respondido correctamente.",
        503: "Servicio no configurado.",
        501: "Endpoint declarado en el contrato pero todavía sin implementar.",
    }
    codes = sorted({401, 501, *status_codes})
    return {
        code: {"model": ErrorResponse, "description": descriptions.get(code, "Error.")}
        for code in codes
    }
