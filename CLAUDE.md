# CoachIA (evolución de LetiSmartCoach)

Contexto, auditoría y arquitectura objetivo: `docs/00-auditoria-y-arquitectura-coachia.md`.

## Convenciones
- Idioma de documentación y comunicación: español. Código e identificadores: inglés.
- Ramas con nombres convencionales de equipo humano: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `refactor/…`
  (por ejemplo, `feat/wahoo-sync-backend`). Nunca prefijos de herramientas (`claude/…`) ni nombres aleatorios.
- Nunca subir secretos (client secrets, tokens, claves de servicio). El repositorio es público.
- Commits a nombre de la autora: `git config user.name "Leticia Martin Cabrera"` y
  `git config user.email "50109256+letiimartin@users.noreply.github.com"` en cada clon nuevo.
- API (`apps/api`): antes de cada commit, `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`.
- El LLM no calcula métricas deportivas: zonas, TSS y carga se calculan en código y con tests.
- Presupuesto de LLM: unos 50 €/año. Contexto compacto vía tools y registro del coste por llamada.
