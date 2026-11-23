# Evaluación del coach (#55)

Set versionado de 20 casos para comparar modelos. El coach conversa con `claude-haiku-5-5`
(decisión de la autora en #55); la evaluación sirve para decidir en la fase 4 (#57) si el
entrenador que prepara las propuestas de adaptación usa otro modelo. **El CI no lo ejecuta**
(sólo comprueba, con un proveedor simulado, que el set es válido y que el script funciona).

- `cases.json`: los casos. Cada uno lleva el contexto simulado que devuelven las herramientas
  (`base_context` más los cambios del caso), la conversación previa y lo que se espera de la
  respuesta (`expect`). Hay dos modos:
  - `chat` (y `intake_opening`): el coach conversa con el prompt real de `app/coach/prompts`.
  - `planner`: el entrenador prepara una propuesta estructurada (`planner.md`), como en la fase 4.
- `coach_eval.py` (en `evals/`): ejecuta los casos contra los modelos candidatos con el bucle real
  del coach (`app.coach.engine`) y herramientas simuladas, y escribe un informe en `results/` con
  la calidad por criterio, los tokens, el coste con los precios oficiales y la proyección mensual.

## Criterios automáticos

| Criterio | Qué comprueba |
|---|---|
| `safety_filter` | El filtro determinista salta (o no) como se espera. Si salta, no se llama al LLM. |
| `tools` | Ha consultado las herramientas necesarias antes de responder. |
| `max_questions` | No hace más preguntas de las permitidas (cuenta los `?`). |
| `include` | Menciona lo esperado (cada grupo: al menos una de las expresiones). |
| `exclude` | No dice lo que no debe (p. ej. volver a preguntar por qué no hizo un entreno). |
| `no_invented_numbers` | Toda cifra con decimales o ≥ 30 que da aparece en los datos o en la conversación. |
| `json` / `action` | (planner) JSON válido con los campos pedidos y una acción aceptable. |

Además, cada caso tiene una `rubric` para revisar a mano las respuestas, que el informe incluye
completas.

## Ejecutarlo

Necesita la clave de Anthropic en `ANTHROPIC_API_KEY` (no está en el repositorio ni en el CI).

```bash
cd apps/api
ANTHROPIC_API_KEY=... uv run python -m evals.coach_eval \
  --models claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5
# Sin clave, para comprobar el set y el informe con respuestas simuladas:
uv run python -m evals.coach_eval --dry-run
```

Opciones: `--cases id1,id2` (subconjunto), `--repeat N` (repeticiones por caso), `--effort low|medium|high`,
`--out RUTA`. Coste orientativo de una pasada completa (20 casos, 3 modelos): unos céntimos con
Haiku 5.5 y algo menos de 1 USD en total con Sonnet 5.5 y Opus 5.5.

## Precios

Los precios oficiales están en `app/core/config.py` (`DEFAULT_LLM_PRICES`), con el enlace y la
fecha de consulta: https://platform.claude.com/docs/en/about-claude/pricing, 19/11/2026
(USD por millón de tokens).

| Modelo | Entrada | Escritura caché 5 min | Lectura caché | Salida |
|---|---|---|---|---|
| `claude-haiku-5-5` (prompt ≤ 100k) | 0,10 | 0,125 | 0,01 | 0,50 |
| `claude-sonnet-5-5` | 2 | 2,50 | 0,10 | 10 |
| `claude-opus-5-5` | 4 | 5 | 0,20 | 20 |
