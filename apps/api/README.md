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

### Postgres local para los tests de BD
Sin `TEST_DATABASE_URL`, los tests de BD se omiten. `scripts/test-db.sh` levanta un Postgres desechable
(binarios locales, sin Docker) en `localhost:5433` con la BD `coachia_test` e imprime la variable:

```bash
eval "$(scripts/test-db.sh)"   # idempotente: si ya está en marcha, sólo vuelve a imprimir la URL
uv run pytest                  # ahora incluye los tests de BD
scripts/test-db.sh stop        # pararlo
```

Busca los binarios en `/usr/lib/postgresql/*/bin` o en el `PATH` (o en `PG_BIN`). Si se ejecuta como root,
usa el usuario `postgres`. El clúster vive en `${TMPDIR:-/tmp}/coachia-test-db` (`TEST_DB_DIR`); el puerto
se cambia con `TEST_DB_PORT`. Para empezar de cero, páralo y borra ese directorio.

## Endpoints actuales

| Ruta | Auth | Descripción |
|---|---|---|
| `GET /health` | — | El proceso está vivo (health check de Render) |
| `GET /health/ready` | — | Dependencias listas (BD). 503 si la BD no responde |
| `GET /v1/me` | JWT de Supabase | Usuario autenticado |
| `GET /v1/integrations` | JWT de Supabase | Estado de las integraciones (nunca devuelve tokens) |
| `GET /v1/integrations/wahoo/authorize-url?platform=mobile\|web` | JWT de Supabase | URL para autorizar en Wahoo, con `state` firmado |
| `DELETE /v1/integrations/wahoo` | JWT de Supabase | Desconecta Wahoo y borra los tokens |
| `POST /v1/athlete/threshold-proposals` | JWT de Supabase | Test de FTP de 20 min: descarga el FIT de una actividad de Wahoo, detecta el bloque y crea una **propuesta** pendiente (no cambia ningún umbral). Los 422 explican el criterio que falla |
| `POST /v1/athlete/threshold-proposals/dry-run` | JWT de Supabase | Análisis de prueba: intervalo, métricas, FTP propuesto y evaluación de cada criterio de calidad, **sin crear la propuesta** |
| `GET /v1/athlete/threshold-proposals[?status=]`, `GET …/{id}` | JWT de Supabase | Propuestas de umbral del atleta |
| `GET /v1/athlete/threshold-proposals/{id}/preview` | JWT de Supabase | Vista previa de aceptar: `create_row` o `update_ftp`, FTP anterior y propuesto, ventana de vigencia y aviso `later_thresholds` |
| `POST /v1/athlete/threshold-proposals/{id}/accept` | JWT de Supabase | Confirma la vista previa (`action`, `previous_ftp_w`; 409 `preview_outdated` si cambió): crea un umbral `source = test` o cambia sólo el FTP de la fila de esa fecha. Los registros posteriores no se tocan; sin recálculo histórico |
| `POST /v1/athlete/threshold-proposals/{id}/reject` | JWT de Supabase | Rechaza la propuesta; no toca nada más |
| `GET /auth/wahoo/callback` | `state` firmado | Redirect URI de Wahoo: canjea el código y vuelve a la app con `?provider=wahoo&status=connected\|error` |
| `GET /internal/ping` | `X-Internal-API-Key` | Comprobación para n8n (workflows en [`automation/n8n`](../../automation/n8n/README.md)) |
| `POST /internal/sync/wahoo` | `X-Internal-API-Key` | Sincroniza todas las integraciones de Wahoo activas (n8n, cada 3 h). Idempotente; con el límite de Wahoo responde `rate_limited: true` y el resto sigue en la próxima ejecución |
| `GET/POST /webhooks/strava` | token de verificación | Suscripción y eventos de Strava |

**Sincronización de Wahoo** (manual con `POST /v1/integrations/wahoo/sync` y automática con `/internal/sync/wahoo`): la primera, sin cursor, sólo importa los workouts que empezaron en los últimos `WAHOO_INITIAL_SYNC_DAYS` días (183 por defecto, unos 6 meses). Las siguientes son incrementales desde el último inicio importado, con un margen de 7 días. Cambiar la ventana no borra actividades ya importadas.

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
Tablas: `athlete_profiles` (1:1 con `auth.users`), `athlete_thresholds` (umbrales con fecha de vigencia), `availability_slots`, `integrations`, `activities`, `calendar_events`, `races` `daily_load` (carga diaria y CTL/ATL/TSB, derivada: la regenera `services.fitness.recompute_from`) y `threshold_proposals` (propuestas de umbral salidas de un test, pendientes hasta que la atleta las acepta o rechaza). Las zonas no se guardan: se calculan a partir del umbral vigente.

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

Variables de entorno: `ENVIRONMENT=production`, `DATABASE_URL` (cadena del *pooler* de Supabase), `SUPABASE_URL`, `INTERNAL_API_KEY`, `TOKEN_ENCRYPTION_KEY`, `OAUTH_STATE_SECRET`, `WAHOO_CLIENT_ID` y `WAHOO_CLIENT_SECRET` (app de **producción** de Wahoo). Opcional: `WAHOO_INITIAL_SYNC_DAYS` (ventana de la primera importación, 183 días por defecto).
