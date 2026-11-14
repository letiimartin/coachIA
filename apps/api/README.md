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
| `GET /v1/integrations` | JWT de Supabase | Estado de las integraciones (nunca devuelve tokens) |
| `GET /v1/integrations/wahoo/authorize-url?platform=mobile\|web` | JWT de Supabase | URL para autorizar en Wahoo, con `state` firmado |
| `DELETE /v1/integrations/wahoo` | JWT de Supabase | Desconecta Wahoo y borra los tokens |
| `GET /auth/wahoo/callback` | `state` firmado | Redirect URI de Wahoo: canjea el código y vuelve a la app con `?provider=wahoo&status=connected\|error` |
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

## Esquema v1 (núcleo)
Tablas: `athlete_profiles` (1:1 con `auth.users`), `athlete_thresholds` (umbrales con fecha de vigencia), `availability_slots`, `integrations`, `activities`, `calendar_events` y `races`. Las zonas no se guardan: se calculan a partir del umbral vigente.

- RLS está activado en todas las tablas y sin políticas, así que el Data API de Supabase no las expone. La API se conecta como propietaria.
- Tests de integración: `TEST_DATABASE_URL=postgresql://... uv run pytest`. Usa una BD **desechable**: el test borra los esquemas `public` y `auth`.
- Aplicar en Supabase sin conexión directa: `uv run alembic upgrade head --sql`, y el SQL se ejecuta con la Management API.

## Despliegue en Render (servicio `letismartcoach`)
Hay que mantener el servicio actual para conservar la Redirect URI registrada en Wahoo (`https://letismartcoach.onrender.com/auth/wahoo/callback`).

| Ajuste | Valor |
|---|---|
| Repositorio / rama | `letiimartin/coachIA` / `main` |
| Root Directory | `apps/api` |
| Build Command | `pip install uv && uv sync --frozen --no-dev` |
| Start Command | `uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Variables de entorno: `ENVIRONMENT=production`, `DATABASE_URL` (cadena del *pooler* de Supabase), `SUPABASE_URL`, `INTERNAL_API_KEY`, `TOKEN_ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `WAHOO_CLIENT_ID` y `WAHOO_CLIENT_SECRET` (app de **producción** de Wahoo).
