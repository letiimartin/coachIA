"""Coach v1 (#55): conversación con contexto, memoria confirmada y control del coste.

El LLM razona sobre resúmenes que calcula el código y nunca calcula métricas ni inventa datos.
En esta fase lee los datos y conversa: no cambia el plan.

- `safety`: filtro determinista de banderas rojas, antes del LLM.
- `budget`: coste de cada llamada y límite mensual.
- `tools`: herramientas de sólo lectura (y dos de registro acotadas) sobre los servicios.
- `memory`: resumen de la conversación y memoria confirmada.
- `engine`: el bucle de una respuesta (LLM ↔ herramientas), sin BD.
- `orchestrator`: el flujo completo de un mensaje, con persistencia.
- `llm/`: la interfaz `LLMProvider` y sus implementaciones.
"""
