# CoachIA

Entrenador digital de ciclismo y trail running, con nutrición en una fase posterior. Combina datos reales del atleta (Wahoo, reloj, diario) con un motor de métricas propio y un coach basado en LLM que trabaja sobre datos estructurados.

Es la evolución de **LetiSmartCoach**. Este repositorio arranca con una historia limpia; el historial del MVP se conserva en el repositorio privado `LetiSmartCoach`. Para la auditoría, la arquitectura objetivo y el roadmap, ver [`docs/00-auditoria-y-arquitectura-coachia.md`](docs/00-auditoria-y-arquitectura-coachia.md).

## Estructura

```
apps/
  api/        Backend FastAPI (núcleo nuevo: métricas, integraciones, coach). Ver apps/api/README.md
  mobile/     App Expo / React Native (iOS, Android y web)
legacy/
  render-backend/  FastAPI desplegado en Render: hoy sólo sirve el callback OAuth de Wahoo
  supabase/        Edge Functions y migraciones del MVP (referencia; el esquema v1 se hará con Alembic)
automation/   Workflows de n8n (próximamente)
data/inbox/   Ficheros locales (FIT, exportaciones). No se versionan
docs/         Documentación y decisiones de arquitectura
```

## Arranque rápido (estado actual)

App móvil (antes, copia las variables `EXPO_PUBLIC_*` de `.env.example` a `apps/mobile/.env`):

```bash
cd apps/mobile && npm install && npx expo start
```

API nueva:

```bash
cd apps/api && uv sync && uv run uvicorn app.main:app --reload
```

Backend legacy (callback de Wahoo):

```bash
cd legacy/render-backend && pip install -r requirements.txt && uvicorn main:app --reload --port 10000
```

## Convenciones
- Ramas: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `refactor/…`.
- Nunca subir secretos. Usa `.env` (ver `.env.example`).
