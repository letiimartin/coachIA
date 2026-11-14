"""Logging y contexto de petición (request id + duración)."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

logger = logging.getLogger("app.request")

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    response.headers["X-Request-ID"] = request_id
    # Sólo la ruta: la query string puede llevar códigos OAuth u otros datos sensibles.
    logger.info(
        "%s %s -> %s (%.1f ms) [%s]",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response
