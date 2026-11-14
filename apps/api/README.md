# CoachIA API

Backend FastAPI de CoachIA: integraciones (Wahoo, Strava…), motor de métricas y coach.
Arquitectura y decisiones: [`docs/00-auditoria-y-arquitectura-coachia.md`](../../docs/00-auditoria-y-arquitectura-coachia.md).

## Requisitos
- Python 3.12 o superior
- [uv](https://docs.astral.sh/uv/)

## Uso

```bash
cd apps/api
uv sync                                   # instala dependencias (incluidas las de desarrollo)
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs
```

La configuración se lee de variables de entorno o de `.env` (en la raíz o en `apps/api`); ver `.env.example`.

## Calidad

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

## Endpoints actuales

| Ruta | Auth | Descripción |
|---|---|---|
| `GET /health` | — | El proceso está vivo (health check de Render) |
| `GET /health/ready` | — | Dependencias listas (BD). 503 si la BD no responde |
| `GET /v1/me` | JWT de Supabase | Usuario autenticado |
| `GET /internal/ping` | `X-Internal-API-Key` | Comprobación para n8n |
| `GET/POST /webhooks/strava` | token de verificación | Suscripción y eventos de Strava |

Todos los errores tienen el formato `{"error": {"code", "message", "details?"}, "request_id"}`. Todas las respuestas llevan la cabecera `X-Request-ID`.

## Autenticación
La app inicia sesión con Supabase Auth y envía `Authorization: Bearer <access_token>`. La API comprueba la firma, la caducidad, la audiencia (`authenticated`) y el emisor (`SUPABASE_URL/auth/v1`):
- **Proyectos nuevos** (ES256/RS256): con las claves públicas del endpoint JWKS. No necesita secretos.
- **Proyectos con el secreto heredado** (HS256): con `SUPABASE_JWT_SECRET`.

## Migraciones (Alembic)

```bash
uv run alembic revision --autogenerate -m "descripcion"   # requiere DATABASE_URL
uv run alembic upgrade head                               # aplicar (online)
uv run alembic upgrade head --sql > migracion.sql         # generar SQL sin conectarse (offline)
```
