# CoachIA (evolución de LetiSmartCoach)

Contexto, auditoría y arquitectura objetivo: `docs/00-auditoria-y-arquitectura-coachia.md`.

## Convenciones
- Idioma de documentación y comunicación: español. Código e identificadores: inglés.
- Ramas con nombres convencionales de equipo humano: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `refactor/…`
  (por ejemplo, `feat/wahoo-sync-backend`). Nunca prefijos de herramientas (`claude/…`) ni nombres aleatorios.
- Nunca subir secretos (client secrets, tokens, claves de servicio). El repositorio es público.
- El LLM no calcula métricas deportivas: zonas, TSS y carga se calculan en código y con tests.
- Presupuesto de LLM: unos 50 €/año. Contexto compacto vía tools y registro del coste por llamada.
