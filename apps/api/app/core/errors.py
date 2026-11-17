"""Errores de la aplicación y formato uniforme de respuesta de error.

Todas las respuestas de error tienen la forma:
    {"error": {"code": "...", "message": "...", "details": ...}, "request_id": "..."}
Nunca se devuelven trazas ni detalles internos al cliente.
"""

import logging
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Error interno del servidor."

    def __init__(self, message: str | None = None, *, headers: dict[str, str] | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.headers = headers


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Autenticación requerida o no válida."

    def __init__(self, message: str | None = None):
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "No tienes permiso para esta operación."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Recurso no encontrado."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "La operación no es posible en el estado actual."


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"
    message = "Demasiadas peticiones. Inténtalo más tarde."


class BadGatewayError(AppError):
    status_code = 502
    code = "bad_gateway"
    message = "Un servicio externo no ha respondido correctamente."


class NotImplementedApiError(AppError):
    """Endpoint declarado en el contrato pero todavía sin implementar."""

    status_code = 501
    code = "not_implemented"
    message = "Endpoint todavía no implementado."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    message = "Servicio no disponible."


_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    429: "too_many_requests",
}


def _body(request: Request, code: str, message: str, details: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error, "request_id": getattr(request.state, "request_id", None)}


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return JSONResponse(
        _body(request, error.code, error.message),
        status_code=error.status_code,
        headers=error.headers,
    )


async def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(StarletteHTTPException, exc)
    code = _HTTP_CODES.get(error.status_code, "http_error")
    message = error.detail if isinstance(error.detail, str) else code
    return JSONResponse(
        _body(request, code, message), status_code=error.status_code, headers=error.headers
    )


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = cast(RequestValidationError, exc)
    details = jsonable_encoder(
        [
            {"loc": list(err.get("loc", ())), "msg": err.get("msg"), "type": err.get("type")}
            for err in error.errors()
        ]
    )
    return JSONResponse(
        _body(request, "validation_error", "Datos de entrada no válidos.", details),
        status_code=422,
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(_body(request, AppError.code, AppError.message), status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
