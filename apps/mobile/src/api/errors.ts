import type { ErrorResponse } from './types';

/** Error de la API con el formato del contrato: `{"error": {code, message}, "request_id"}`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, requestId: string | null = null, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

function isErrorResponse(body: unknown): body is ErrorResponse {
  if (typeof body !== 'object' || body === null || !('error' in body)) return false;
  const error = (body as { error: unknown }).error;
  return typeof error === 'object' && error !== null && 'code' in error && 'message' in error;
}

/** Mensajes de validación (422) legibles: "campo: mensaje". */
function validationMessages(details: unknown): string[] {
  if (!Array.isArray(details)) return [];
  return details
    .map((d) => {
      if (typeof d !== 'object' || d === null) return null;
      const { loc, msg } = d as { loc?: unknown; msg?: unknown };
      if (typeof msg !== 'string') return null;
      const field = Array.isArray(loc) ? loc.filter((p) => p !== 'body').join('.') : '';
      return field ? `${field}: ${msg}` : msg;
    })
    .filter((m): m is string => m !== null);
}

/** Convierte una respuesta no correcta en ApiError. */
export function toApiError(status: number, body: unknown): ApiError {
  if (isErrorResponse(body)) {
    const { code, message, details } = body.error;
    return new ApiError(status, code, message, body.request_id ?? null, details);
  }
  // Por si llega un 422 con el formato por defecto de FastAPI (`{"detail": [...]}`).
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    return new ApiError(status, 'validation_error', 'Datos de entrada no válidos.', null, detail);
  }
  return new ApiError(status, 'http_error', `Error inesperado del servidor (HTTP ${status}).`);
}

/** Texto para mostrar al usuario a partir de cualquier error. */
export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    const extra = error.code === 'validation_error' ? validationMessages(error.details) : [];
    const lines = [error.message, ...extra];
    if (error.requestId) lines.push(`Ref.: ${error.requestId}`);
    return lines.join('\n');
  }
  if (error instanceof Error) return error.message;
  return 'Error desconocido.';
}
