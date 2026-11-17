# CoachIA

Entrenador digital de ciclismo y trail running (evolución de LetiSmartCoach). El LLM trabaja sobre
datos estructurados y cálculos deterministas; nunca calcula métricas ni inventa datos.
Documentación histórica: `docs/00-auditoria-y-arquitectura-coachia.md`, sólo para consultar el porqué.

## Mapa
- `apps/api`: backend FastAPI (Python 3.12, uv, SQLAlchemy 2, Alembic). Desplegado en Render (`letismartcoach`).
- `apps/mobile`: app Expo / React Native (iOS, Android y web). Pendiente de migrar a TypeScript.
- `legacy/`: código del MVP, sólo como referencia. No se modifica.
- Base de datos: Supabase `coachia` (`oyvephnvtecwythnikea`). Auth con JWT de Supabase (JWKS).

## Comandos (`apps/api`)
- Calidad: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`
- Tests de BD: `TEST_DATABASE_URL=postgresql://... uv run pytest`. Usa una BD desechable: el test borra los esquemas.
- Migración nueva: `uv run alembic revision --autogenerate -m "..."`. En Supabase se aplica en SQL
  (`uv run alembic upgrade <rev>:head --sql`) con la Management API, y **sólo con autorización de la autora**.

## Cómo trabajamos
- Cada tarea es **un issue, una sesión, una rama y un PR**. Ramas `feat/…`, `fix/…`, `chore/…`, `docs/…`,
  `refactor/…`, nunca `claude/…`. El PR incluye `Closes #N`.
- El estado del proyecto está en GitHub: issues (milestone = fase) y PRs. No se mantienen documentos de estado.
- Antes de abrir el PR: comandos de calidad en verde. El CI es la validación obligatoria.
- Al abrir el PR, la sesión se suscribe a él y corrige el CI hasta dejarlo en verde.
- **Nunca** fusionar PRs ni tocar producción, credenciales o paneles externos sin autorización explícita de la autora.
  Los cambios de arquitectura o de producto se proponen en el issue o el PR, no se deciden en solitario.
- **Migraciones:** sólo una rama abierta a la vez puede añadir migraciones; el CI exige una única cabeza de Alembic.
- **Contratos de API:** si backend y app se desarrollan en paralelo, primero se fusiona el contrato
  (schemas y endpoints) y ambos trabajan contra él.
- Commits a nombre de la autora (`git config user.name "Leticia Martin Cabrera"`,
  `git config user.email "50109256+letiimartin@users.noreply.github.com"`).
- Nunca subir secretos: el repositorio es público.
- Orquestación de bloques de trabajo: skill `orquestar`.

## Decisiones clave
- Monolito modular FastAPI. Toda la lógica, el cálculo y los tokens están en la API; la app sólo habla con la API.
- Postgres en Supabase con RLS en todas las tablas, sin políticas y sin privilegios para `anon`/`authenticated`.
- Todo cuelga de `athlete_profiles` (1:1 con `auth.users`, borrado en cascada).
- Los umbrales tienen fecha de vigencia (`athlete_thresholds`). Las zonas se calculan, no se guardan.
- Tokens OAuth cifrados con Fernet. El `state` de OAuth va firmado. Callback de Wahoo: `/auth/wahoo/callback`.
- Enums como texto con CHECK. Los cambios de esquema siempre con Alembic.
- Fuentes: Wahoo para el ciclismo; Suunto (vía Strava o FIT) para la carrera. Hay que deduplicar las actividades.
- LLM: unos 50 €/año. Contexto compacto vía tools y registro del coste por llamada. Un modelo económico por defecto.
- Errores con formato `{"error": {code, message}, "request_id"}`. Nunca se registran tokens ni query strings.
