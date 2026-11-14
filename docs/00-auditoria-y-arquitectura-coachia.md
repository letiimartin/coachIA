# CoachIA — Fase 0: Auditoría de LetiSmartCoach y arquitectura objetivo

> Fecha de la auditoría: 2026-11-14 · Último commit del repo: 2026-02-18 (unos 9 meses parado)
> Alcance: las 7 ramas remotas, el código, las migraciones, la integración con Wahoo y la deuda técnica.

---

## 0. Resumen ejecutivo

- **Qué hay:** un MVP en **Expo / React Native (JavaScript)** que habla **directamente con Supabase** (Auth, Postgres con RLS y Edge Functions en Deno). También hay un **FastAPI en Render** que sólo hace de "rebote" para la Redirect URI de Wahoo. El "Coach" son dos Edge Functions que mandan un prompt único a **DeepSeek**.
- **Lo que funciona de verdad:** login con Supabase, perfil, calendario de eventos (CRUD), intercambio OAuth de Wahoo en el servidor (Edge Function `wahoo-auth`), chat persistido y un generador de plan semanal en JSON.
- **Lo que no funciona o es simulado:** la sincronización de Wahoo en `master` es un **mock**. La versión real está en otra rama y llama a Wahoo desde el cliente. El dashboard muestra **números inventados** (`"8h 30m"`, `420 TSS`, `"Gran Fondo Pirineos"`). Los "mejores esfuerzos" guardan la potencia media en todas las ventanas. No hay refresco de tokens. Las migraciones no reproducen la base de datos.
- **Riesgo crítico:** el **repositorio es público** y su historial contiene **credenciales** (el client secret de Wahoo y un par de tokens OAuth). Hay que rotarlas antes de nada (tarea T0).
- **Veredicto:** se reutiliza el **conocimiento, el flujo OAuth, la Redirect URI, el diseño de pantallas y el modelo conceptual**. El backend y el esquema se rehacen de forma limpia sobre FastAPI + Postgres (Supabase), con migraciones versionadas y un motor de métricas en Python. El volumen de código existente es pequeño (unas 5.400 líneas), así que refactorizar sale más barato que parchear.

---

## 1. Estado de las ramas

| Rama | Último commit | Contenido | Estado |
|---|---|---|---|
| `master` (rama por defecto) | 29-ene-2026 | App Expo, `legacy_backend` FastAPI, migraciones Supabase, Edge Function `wahoo-auth`. **Sync de Wahoo simulado.** | Base estable, la más antigua |
| `mvp/wahoo-auth-fix` | 02-feb-2026 | `master` + Edge Functions `chat-coach` y `generate-training-plan`, `planService`, `WahooCallbackScreen`, `state` web/mobile, callback en Render, arranque sin secretos. **Sync sigue simulado.** | **La más avanzada en backend/IA** |
| `mvp/wahoo/connector` | 02-feb-2026 | Rama antigua + **sync real** (`GET /v1/workouts`) y **exportación** de sesiones a Wahoo (`/v1/plans` + `/v1/workouts`), scopes `plans_read plans_write`. | **La más avanzada en Wahoo**. Diverge de `auth-fix` |
| `mvp/agentB-wahoo-export-plan-workout` | 02-feb-2026 | Idéntica a `mvp/wahoo/connector` (mismo commit) | Redundante |
| `mvp/agentA-wahoo-scopes-and-sync` | 02-feb-2026 | Subconjunto ya fusionado en `connector` | Redundante |
| `main` | 18-feb-2026 | **Historia huérfana** (sin ancestro común): esqueleto `apps/api` con FastAPI y webhook de **Strava**, `data/inbox/` | Intento de reinicio como monorepo |
| `claude/great-shannon-3em7cy` | = `master` | Rama de trabajo de esta sesión | — |

**Conclusiones:**
1. El trabajo útil está **repartido entre dos ramas que nunca se unieron**: `auth-fix` (IA y OAuth) y `connector` (sync y export). Ninguna de las dos tiene ambas cosas.
2. `main` muestra la intención de reorganizar en monorepo (`apps/api`) y de explorar Strava. Esa dirección coincide con la arquitectura propuesta y se aprovecha.
3. Sobran dos ramas `agentA`/`agentB`. Se pueden borrar tras etiquetar el estado legacy.

---

## 2. Arquitectura actual

```
┌───────────────────────────┐        ┌──────────────────────────────────────────┐
│ Expo RN app (JS)          │        │ Supabase (proyecto ofeapnttdjbsyaquslwd)  │
│ - Auth/Perfil/Calendario  │──SDK──▶│ - Auth                                    │
│ - Llama a Wahoo API       │        │ - Postgres + RLS (tablas por usuario)     │
│   DIRECTAMENTE (connector)│        │ - Edge Fn wahoo-auth  (code → tokens)     │
│ - Lee tokens Wahoo de BD  │        │ - Edge Fn chat-coach  (DeepSeek)          │
└──────────┬────────────────┘        │ - Edge Fn generate-training-plan (DeepSeek)│
           │ OAuth redirect          └──────────────────────────────────────────┘
           ▼
┌───────────────────────────┐
│ FastAPI en Render         │  /auth/wahoo/callback → redirige a
│ (legacy_backend)          │  letismartcoach://wahoo-callback?code=… (móvil)
│ + routers antiguos con    │  o  {WEB_BASE_URL}/wahoo-callback?code=… (web)
│   user_id por query param │
└───────────────────────────┘
```

**Flujo OAuth actual (el que hay que conservar):**
1. La app abre `https://api.wahooligan.com/oauth/authorize?client_id=…&redirect_uri=…&scope=…&state=web|mobile`.
2. Wahoo redirige a la **Redirect URI registrada**, que muy probablemente es el endpoint de Render `/auth/wahoo/callback` (**pendiente de confirmar en el portal de Wahoo**).
3. Render reenvía el `code` a la app (por deep link o por web).
4. La app invoca la Edge Function `wahoo-auth`, que hace el intercambio con el `client_secret` en el servidor y guarda los tokens con RLS.

---

## 3. Tecnologías utilizadas

| Capa | Tecnología | Comentario |
|---|---|---|
| App | Expo SDK 54, React Native 0.81, React 19, React Navigation 7, lucide-react-native | Moderno. Sin TypeScript, lint ni tests |
| Datos | Supabase JS 2.91, AsyncStorage | El cliente accede a todas las tablas (lo frena RLS) |
| Serverless | Supabase Edge Functions (Deno) | `wahoo-auth` usa `std@0.168` y `supabase-js@2.0.0` (muy antiguos) |
| Backend | FastAPI + `supabase-py` + `openai` SDK (apuntando a DeepSeek) + httpx | Sin dependencias fijadas ni tests. En la práctica sólo se usa el callback |
| BD | Postgres (Supabase) + RLS "owner only" | 10 migraciones que se contradicen entre sí |
| LLM | DeepSeek `deepseek-chat`, JSON mode | Un único prompt con todo el contexto volcado como JSON |
| Hosting | Render (FastAPI), Supabase cloud, ngrok para pruebas web | URL de ngrok fija en el código |

---

## 4. Qué se reutiliza

| Elemento | Cómo se reutiliza |
|---|---|
| **App de Wahoo (client_id) y Redirect URI registrada** | Se mantiene la misma ruta (`/auth/wahoo/callback`) en el nuevo FastAPI, así que no hay que tocar la configuración aprobada. Sólo se **rota el secret**. |
| Patrón OAuth "intercambio en servidor + `state`" | Se conserva, pero la API firma el `state` (nonce + user_id) contra CSRF. |
| Mapeo `workout_type_id` → deporte y lógica de sync (`connector`) | Pasa a `integrations/wahoo/mapper.py` en el backend, con tests. |
| Prototipo de exportación a Wahoo Plans (`wahooExportService.js`) | Se convierte en `exporters/wahoo_plan.py`. Antes hay que **verificar el formato contra la documentación oficial**. |
| Pantallas Expo (Calendario semana/mes con swipe, Perfil, Chat, Detalle, tarjetas) | Se migran a TypeScript con expo-router. El diseño oscuro con acento cian es una buena base. |
| Modelo conceptual (perfil / calendario con tipos / sesiones planificadas / workouts reales / feedback / best efforts / mensajes) | Base del modelo de datos v1 (sección 8). |
| Persistencia del chat y contexto por usuario | Pasa a `coach_conversations` / `coach_messages`. |
| Esqueleto `apps/api` de la rama `main` | Punto de partida del monorepo. |

## 5. Qué hay que refactorizar o rehacer

| Elemento | Problema | Decisión |
|---|---|---|
| Esquema de BD y migraciones | No son reproducibles (sección 6) | **Esquema v1 limpio** con Alembic. Si no hay datos reales que conservar, se usa un proyecto o BD nueva |
| Llamadas a Wahoo desde el cliente | Exponen el token, fallan en web por CORS, no refrescan el token | Todo Wahoo pasa a la **API** |
| Edge Functions del coach | Prompt único, rol "triathlon coach", sin validación, sin tools, el LLM estima el TSS | **Coach Orchestrator** en FastAPI (sección 6.3) |
| `legacy_backend` routers | Aceptan `user_id` por query sin autenticación | Se eliminan y se sustituyen por endpoints con JWT de Supabase |
| Dashboard | Métricas inventadas | Se alimenta del motor de métricas |
| `analytics_service.calculate_best_efforts` | Mock | Curva de potencia y ritmo real a partir del FIT |
| `calendarService.updateStatus` | Usa `export_status` para marcar hecho/no hecho | Separar `status` (planificado/completado/saltado) de `export` |
| JS sin tipos | Errores de esquema en tiempo de ejecución | TypeScript + tipos generados desde OpenAPI |

---

## 6. Problemas y deuda técnica

### 6.1 Seguridad (prioridad máxima)
1. **Credenciales en el historial de un repo público:** el client secret de Wahoo (escrito en código cliente y en Python) y un fichero de tokens OAuth de Wahoo. Borrarlos del último commit no basta porque el historial es público. → **Rotar el secret y revocar los tokens (T0).**
2. Los tokens de Wahoo se guardan **en texto plano** en columnas `*_enc` y RLS deja que el propio cliente los lea. La app los usa directamente.
3. `legacy_backend/*_router.py`: endpoints `?user_id=…` sin autenticación. Si se despliegan con una clave `service_role`, cualquiera puede leer o escribir datos de cualquier usuario.
4. Las Edge Functions devuelven `error.stack` al cliente, y el CORS es `*` en todas partes.
5. URL y anon key de Supabase escritas en el código. La anon key es pública por diseño, pero debe ir en variables de entorno. Hay URLs de ngrok fijadas.
6. No hay validación de `state` en el callback: sólo distingue web o móvil, no protege contra CSRF.

### 6.2 Datos y esquema
- No hay ninguna migración que **cree la tabla `profiles`**, aunque se use.
- `20260127140500_phase4_wahoo.sql` hace `create table workouts / planned_sessions / wahoo_tokens` **sin `IF NOT EXISTS`** y con columnas distintas a `legacy_backend/supabase_schema.sql`. Ejemplos: `external_id` frente a `provider_activity_id`, `access_token` frente a `access_token_enc`, `summary_json` frente a `metrics_json`.
- Deportes incoherentes: `'ciclismo','running','fuerza','otro'` en un sitio, `'cycling','trail_running','both'` en otro y `'Bike','Run','Swim'` en el prompt.
- `coach_messages.role` sólo admite `('athlete','coach','system')`, pero la Edge Function inserta `'user'/'assistant'`. O falla, o la BD real ya no coincide con las migraciones.
- `generate-training-plan` selecciona columnas que no existen (`tss`, `perceived_exertion`, `notes`) y no inserta `title`, que es `NOT NULL`.
- El filtro de calendario `.lte('end_dt', weekEnd)` **excluye los eventos sin `end_dt`**, que son todos los que crea la app.
- Restricciones duplicadas (`calendar_events_dates_check` y `chk_end_after_start`) y políticas RLS creadas tres veces con nombres distintos.
- Varias migraciones existen sólo para "apagar fuegos" (`fix_summary_json`, `fix_workouts_complete`, `safe_fix…`): la BD se modificaba a mano.

### 6.3 IA / Coach
- El contexto se **vuelca entero en el prompt** (perfil, últimos 10 entrenos con el JSON en bruto, todos los eventos): caro, ruidoso y sin control.
- El LLM **inventa el TSS y los rangos** y responde como "elite **triathlon** coach" con natación.
- El JSON no se valida con un esquema y no hay reglas deportivas: progresión de carga, días duros seguidos, taper, disponibilidad.
- No hay protocolo de seguridad médica.
- No se guarda **por qué** el coach decidió algo, así que no se puede auditar ni aprender de ello.

### 6.4 Calidad
- 0 tests, sin CI, sin lint, sin TypeScript y dependencias Python sin fijar.
- Restos de sesiones con agentes de IA: comentarios como *"I need to match the replacement content…"*, `return` duplicado, imports inexistentes (`dbo` en `CoachChatScreen`), `mocks.js` y la nota "keep as is".
- El `.gitignore` excluye `*.md` en algunas ramas, así que no hay documentación versionada. También hay ficheros de entorno local versionados: `.vscode/launch.json` (debugger de R) y `expo_log.txt`.
- `toWahooDayCode` usa la zona horaria local y `Math.abs`/`ceil`, lo que puede dar desfases de ±1 día.

---

## 7. Arquitectura objetivo

### 7.1 Decisiones principales

| Decisión | Elección | Por qué | Alternativa descartada |
|---|---|---|---|
| Backend | **FastAPI (Python 3.12)**, monolito modular | El ecosistema de ciencia deportiva está en Python: `fitparse`/`fitdecode`, numpy/pandas para la curva de potencia, CTL/ATL y la normalización. Es tipado con Pydantic y genera OpenAPI. Ya hay FastAPI en Render (Redirect URI) | Edge Functions en Deno: mal entorno para el cálculo numérico y difíciles de testear. Microservicios: sobreingeniería |
| BD | **Postgres en Supabase** | Ya se usa, tiene plan gratuito, y trae Auth y Storage (para los FIT) | Postgres autogestionado: más operación |
| Auth | **Supabase Auth** (la API verifica el JWT) | Ya está integrado en la app, con login social disponible | Auth propio |
| ORM y migraciones | **SQLAlchemy 2 + Alembic** | Una única fuente de verdad del esquema, lo que resuelve el problema de las migraciones | Migraciones SQL a mano en Supabase (es lo que causó el problema) |
| Acceso a datos desde la app | **Sólo a través de la API** (RLS queda como defensa adicional) | Las reglas, el cálculo y los tokens viven en el servidor | Supabase directo desde el cliente: la lógica se dispersa |
| Frontend | **Expo (React Native + web) con TypeScript y expo-router** | Mobile-first real, reutiliza las pantallas y sirve iOS, Android y web desde una sola base. La integración futura con HealthKit o Health Connect necesita app nativa | Next.js: excelente en web, pero obliga a una segunda app para salud móvil |
| LLM | **Capa `LLMProvider` agnóstica** con tool calling. Modelo elegido con un **set de evaluación propio** | Evita el bloqueo con un proveedor. Se puede usar un modelo barato para clasificar y uno mejor para planificar | Atarse a un solo SDK |
| Tareas en segundo plano | **n8n (cron/webhooks) + endpoints internos idempotentes** y `BackgroundTasks` de FastAPI | Suficiente para un usuario. Además cubre el objetivo de portfolio | Celery/Redis: innecesario por ahora |
| Hosting | Supabase (BD/Auth/Storage) · **Render** (API, con la Redirect URI ya registrada) · **n8n** en Railway o Render (Docker) · Expo EAS (builds) + web estática | Coste bajo o nulo al principio | AWS: demasiada operación para un MVP |

### 7.2 Diagrama objetivo

```
                    ┌──────────────── Canales ────────────────┐
                    │ App Expo (iOS/Android/Web) · Telegram*   │   *vía n8n
                    └───────────────┬──────────────────────────┘
                                    │ HTTPS + JWT Supabase
┌───────────────────────────────────▼──────────────────────────────────────────┐
│ FastAPI (monolito modular)                                                   │
│  api/v1: athlete · calendar · activities · workouts · plans · journal ·      │
│          health · metrics · coach · integrations · internal (API key n8n)    │
│                                                                              │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐ ┌──────────────────────┐ │
│  │Integrations │ │ Metrics      │ │ Planning/Rules│ │ Coach Orchestrator   │ │
│  │ wahoo/      │ │ zones, TSS,  │ │ validador,    │ │ intents → tools →    │ │
│  │ (strava,    │ │ CTL/ATL/TSB, │ │ periodización,│ │ estado → LLM → valid.│ │
│  │  garmin…)   │ │ power curve, │ │ disponibilidad│ │ → propuesta → explic.│ │
│  │ FIT parser  │ │ readiness    │ │ seguridad     │ │ (LLMProvider)        │ │
│  └─────┬───────┘ └──────┬───────┘ └──────┬────────┘ └─────────┬────────────┘ │
│        └────────────────┴───── services / repositories ───────┘              │
│  Exporters: ZWO · FIT workout · Wahoo Plan JSON                              │
└──────────────┬──────────────────────────────────────────────┬───────────────┘
               │ SQLAlchemy                                    │ Storage (FIT)
        ┌──────▼──────────┐                             ┌──────▼──────┐
        │ Postgres        │                             │ Supabase    │
        │ (Supabase)      │                             │ Storage     │
        └─────────────────┘                             └─────────────┘
   n8n ──cron/webhooks──▶ /internal/* (sync diario, briefing matinal, revisión semanal,
                                       enriquecer carreras, ingesta de salud, voz→diario)
```

### 7.3 Coach IA: agente controlado

```
Mensaje ("hoy estoy muy cansada")
  1. Safety gate (determinista + clasificador): ¿dolor torácico, mareo, lesión aguda?
       → respuesta fija recomendando valoración médica; no se toca el plan
  2. Intent router (LLM barato, salida JSON): consulta | reporte_estado | cambio_plan | pregunta_porqué | otro
  3. Context builder: llama a TOOLS de solo lectura según el intent (nunca SQL libre)
       get_athlete_profile · get_training_zones · get_today · get_recent_activities(días)
       get_training_load (CTL/ATL/TSB/ACWR/ramp) · get_calendar(rango) · get_current_plan(rango)
       get_recent_journal(días) · get_health_metrics(días) · get_next_goal_race
  4. Athlete state (CÓDIGO): readiness_score, fatiga, días hasta la carrera A, fase (base/build/peak/taper),
       semáforos (TSB < −30, ACWR > 1.5, sueño < 6 h, dolor reportado…)
  5. LLM decide → devuelve una PROPUESTA estructurada (JSON validado con Pydantic):
       {action: keep|reduce_intensity|reduce_volume|swap_recovery|move|remove|create,
        changes:[{workout_id, …}], rationale, confidence}
  6. Validador determinista: carga semanal máx., no dos días duros seguidos, disponibilidad,
       taper, límites de rampa, estructura de bloques válida y TSS recalculado por código
       → si falla, se reintenta con el error (máx. 2) o se cae a una regla segura
  7. Aplicación: al principio como PROPUESTA que el usuario acepta con un toque;
       más adelante, auto-aplicar los cambios de bajo riesgo
  8. Explicación en lenguaje natural + registro en coach_decisions (auditoría y dataset)
```

**Qué resuelve cada parte:**

| Problema | Código | Reglas | BD | LLM |
|---|---|---|---|---|
| Zonas, TSS, CTL/ATL/TSB, best efforts | ✅ | | ✅ | ❌ |
| Readiness a partir de sueño, HRV o diario | ✅ (puntuación) | ✅ | ✅ | interpreta el texto libre |
| Qué sesión toca hoy y cómo adaptarla | | ✅ límites | ✅ | ✅ decide dentro de los límites |
| Estructura de bloques del workout | ✅ valida y calcula la carga | ✅ | ✅ | ✅ propone |
| Detección de banderas rojas médicas | ✅ palabras clave | ✅ | | ✅ clasificador de apoyo |
| Explicar, motivar, conversar | | | | ✅ |
| Macros y calorías | ✅ fórmulas | ✅ guías | ✅ | ✅ menús y redacción |

### 7.4 "Entrenar un modelo propio": recomendación
**Todavía no.** Con un solo atleta y pocos meses de datos, un fine-tuning aprendería poco y añadiría coste y complejidad. La calidad de los entrenamientos se consigue antes con:
1. Una **biblioteca de workouts** parametrizados por zona y objetivo (VO2max, umbral, sweet spot, tempo, Z2, fuerza-resistencia, cuestas de trail…).
2. **Plantillas de periodización** (base, build, peak, taper y recuperación tras carrera) con reglas.
3. **RAG** sobre una pequeña base de conocimiento curada: principios de entrenamiento, notas propias, guías de nutrición deportiva.
4. Registro en `coach_decisions` de *qué se propuso, qué se hizo y cómo te sentiste*: es el **dataset** que permitirá más adelante evaluar, hacer fine-tuning o entrenar un recomendador pequeño (por ejemplo, para predecir la RPE o el cumplimiento).

### 7.5 n8n: dónde aporta valor sin ensuciar el núcleo
Regla: **n8n orquesta y conecta canales; la lógica del coach y las métricas viven en la API** (testeables y versionadas). n8n llama a `/internal/*` con una API key de servicio y los workflows se exportan en JSON a `automation/n8n/`.

| Workflow | Disparador | Qué hace |
|---|---|---|
| Sync Wahoo programado | Cron cada 2-3 h (el webhook de Wahoo está desactivado en la app de producción) | `POST /internal/sync/wahoo` |
| Check-in matinal | Cron 07:30 por Telegram | Pregunta horas de sueño, HRV del Suunto y sensaciones, y hace `POST /health` + `POST /journal` |
| Briefing matinal | Cron 07:00 | `GET /internal/coach/daily-brief`, que envía "qué toca hoy y por qué" por Telegram o email |
| Chat por Telegram | Telegram Trigger | Reenvía a `/coach/chat` y devuelve la respuesta. Hablar con el coach desde cualquier sitio |
| Nota de voz al diario | Audio de Telegram | Transcripción y `POST /journal` (el LLM extrae RPE, fatiga, dolor y estrés) |
| Revisión semanal | Cron domingo | Informe de cumplimiento y carga, y propuesta de la semana siguiente |
| Enriquecer carrera | Webhook al crear un evento "Quebrantahuesos" | Búsqueda web, extracción de distancia y desnivel, `PATCH /races/{id}` (con estado `pending_review`) |
| Ingesta de salud | Webhook (por ejemplo, un atajo de iOS que envía datos de Salud) | `POST /internal/health/ingest` |

---

## 8. Estructura de carpetas recomendada (monorepo)

```
coachia/                              (este repo, renombrable más adelante)
├── apps/
│   ├── api/                          FastAPI
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/                 config (pydantic-settings), security (JWT Supabase, API keys),
│   │   │   │                         crypto (cifrado de tokens), logging, errors
│   │   │   ├── db/                   session.py, base.py
│   │   │   ├── models/               SQLAlchemy (un módulo por agregado)
│   │   │   ├── schemas/              Pydantic (DTOs API) + workout_structure.py (esquema versionado)
│   │   │   ├── api/v1/               routers finos, sin lógica
│   │   │   ├── services/             casos de uso (calendar, activities, plans, journal…)
│   │   │   ├── integrations/
│   │   │   │   └── wahoo/            oauth.py · client.py · mapper.py · sync.py · webhooks.py
│   │   │   ├── metrics/              zones.py · load.py (TSS/hrTSS/rTSS, CTL/ATL/TSB) ·
│   │   │   │                         power_curve.py · best_efforts.py · fit_parser.py · readiness.py
│   │   │   ├── planning/             rules.py · validator.py · periodization.py · library/
│   │   │   ├── coach/                orchestrator.py · tools.py · context.py · safety.py ·
│   │   │   │                         prompts/ · llm/ (provider.py + adaptadores)
│   │   │   ├── exporters/            zwo.py · fit_workout.py · wahoo_plan.py
│   │   │   └── nutrition/            (fase posterior) targets.py · fueling.py
│   │   ├── alembic/
│   │   ├── tests/                    unit (metrics, planning, mappers) · integration · fixtures/ (FIT, JSON Wahoo)
│   │   └── pyproject.toml            (uv o poetry, dependencias fijadas, ruff, mypy, pytest)
│   └── mobile/                       Expo + TypeScript + expo-router
│       ├── app/                      (tabs)/today · calendar · coach · activities · performance · journal · athlete
│       ├── src/api/                  cliente generado desde OpenAPI
│       ├── src/components/ · src/features/ · src/theme/
│       └── app.config.ts             (variables EXPO_PUBLIC_*)
├── automation/n8n/                   workflows/*.json · README.md · docker-compose.n8n.yml
├── docs/                             00-auditoria… · adr/ (decisiones de arquitectura) · api.md
├── infra/                            render.yaml · docker-compose.yml (Postgres local para tests)
├── .github/workflows/                ci.yml (lint + tests api + typecheck mobile)
└── .env.example                      (sin valores reales)
```

---

## 9. Modelo de datos inicial (v1)

Principios: **los datos brutos se guardan y los derivados se recalculan**. Se usa **JSONB sólo donde la estructura es un árbol que se lee y escribe entero** (bloques de workout, datos crudos del proveedor). Los umbrales tienen **historial**, porque el TSS de marzo debe calcularse con el FTP de marzo. Todas las tablas llevan `user_id`, `created_at` y `updated_at`.

```
users (auth.users de Supabase)
└─ athlete_profile          1:1  display_name, birth_date, sex, height_cm, timezone, units,
                                 sports[] , zone_model (coggan|friel|custom), preferences jsonb
   athlete_thresholds       1:N  effective_from, ftp_w, lthr_bpm, hr_max, hr_rest, threshold_pace_s_km,
                                 vo2max, weight_kg, source (manual|test|estimated)
                                 → las zonas se CALCULAN a partir del umbral vigente (sin tabla propia;
                                   zone_overrides jsonb si hay zonas personalizadas)
   availability             1:N  weekday, max_minutes, sports[], preferred_time, is_rest_preferred

integrations                1:N  provider (wahoo|strava|garmin|oura…), external_user_id, scopes[],
                                 access_token_enc, refresh_token_enc (cifrados en la aplicación),
                                 expires_at, status, last_sync_at, sync_cursor
                                 UNIQUE(user_id, provider)

activities                  1:N  provider, external_id, sport, sub_sport, title, start_at, timezone,
                                 elapsed_s, moving_s, distance_m, ascent_m, calories,
                                 avg_hr, max_hr, avg_power, np_power, avg_cadence, avg_speed,
                                 load (tss), load_method (power|hr|pace|rpe), intensity_factor,
                                 planned_workout_id (FK, nullable), raw jsonb, fit_path
                                 UNIQUE(user_id, provider, external_id)
activity_streams            1:1  activity_id, storage_path (parquet/npz en Storage), sample_rate,
                                 channels[] (power, hr, cadence, speed, altitude, latlng)
activity_efforts            1:N  activity_id, metric (power|pace|hr), window_s | distance_m, value
                                 → los récords (90 días, año, histórico) son una consulta o vista

daily_load                  1:N  date, sport (all|bike|run), load, ctl, atl, tsb, ramp
                                 UNIQUE(user_id, date, sport)  — recalculable de forma idempotente

calendar_events             1:N  kind (race|social|travel|health|personal|unavailable), title,
                                 start_at, end_at, all_day, training_impact
                                 (none|reduce|no_training|move), notes, details jsonb
races                       1:1  event_id, discipline, distance_m, ascent_m, priority (A|B|C),
                                 goal, enrichment_status (none|pending_review|confirmed), source_url

training_plans              1:N  goal_race_id, start_date, end_date, status, phases jsonb, rationale
planned_workouts            1:N  plan_id (nullable), date, sport, title, objective, description,
                                 structure jsonb (WorkoutStructure v1, validado con Pydantic),
                                 planned_duration_s, planned_load (calculada por código),
                                 status (planned|completed|partial|skipped|moved|replaced),
                                 source (coach|user|template), version, replaced_by_id,
                                 coach_decision_id
workout_exports             1:N  planned_workout_id, provider, status, external_ids jsonb, error,
                                 exported_at

journal_entries             1:N  date, activity_id?, rpe, fatigue, soreness, motivation, stress,
                                 sleep_quality, pain jsonb [{zona, intensidad}], text,
                                 audio_path, transcript, extracted jsonb (lo que extrae el LLM, revisable)
health_metrics              1:N  date, metric (sleep_s|hrv_rmssd|rhr|weight|readiness|cycle_phase…),
                                 value, unit, source  UNIQUE(user_id, date, metric, source)

coach_conversations         1:N  channel (app|telegram), title
coach_messages              1:N  conversation_id, role (user|assistant|tool|system), content,
                                 tool_calls jsonb, tokens_in/out, model
coach_decisions             1:N  trigger, intent, state_snapshot jsonb, tools_used[], proposal jsonb,
                                 validation jsonb, applied (bool), user_response, outcome jsonb
                                 ← auditoría + dataset para mejorar el coach

(fase 7) nutrition_targets_daily  date, kcal, carbs_g, protein_g, fat_g, method, based_on_load
```

**WorkoutStructure v1** (JSONB validado; árbol con repeticiones):
```json
{
  "version": 1,
  "steps": [
    {"type": "warmup",   "duration": {"seconds": 900},  "target": {"type": "power_pct_ftp", "min": 0.55, "max": 0.75}},
    {"type": "repeat",   "count": 4, "steps": [
      {"type": "work",     "duration": {"seconds": 240}, "target": {"type": "power_pct_ftp", "min": 1.10, "max": 1.15}, "cadence": {"min": 90, "max": 100}},
      {"type": "recovery", "duration": {"seconds": 240}, "target": {"type": "power_pct_ftp", "min": 0.40, "max": 0.55}}
    ]},
    {"type": "cooldown", "duration": {"seconds": 600},  "target": {"type": "zone", "zone": "Z1"}}
  ]
}
```
Tipos de objetivo: `power_pct_ftp | power_w | hr_pct_lthr | hr_bpm | pace_s_km | zone | rpe`. Tipos de duración: `seconds | meters | open`. Los objetivos se guardan **relativos** (al FTP o al LTHR) y se convierten a absolutos al exportar. La carga (TSS) planificada la calcula el código a partir de este árbol.

---

## 10. Roadmap (fases ajustadas)

| Fase | Objetivo | Entregable demostrable |
|---|---|---|
| **0. Sanear** (≈1 semana) | Seguridad, consolidar ramas, monorepo, CI | Repo limpio, secretos rotados, `apps/api` y `apps/mobile` arrancando |
| **1. Core + Wahoo real** | Auth JWT, perfil y umbrales, calendario, Wahoo OAuth y sync en el backend, FIT a Storage | Conecto Wahoo y veo mi histórico real en la app |
| **1.5 n8n básico** | n8n desplegado, sync programado, briefing por Telegram | Recibo cada mañana un resumen real |
| **2. Métricas** | Zonas, TSS/hrTSS/rTSS, CTL/ATL/TSB, curva de potencia y best efforts (salen del mismo parseo FIT), dashboard real | Dashboard con números reales y PMC |
| **3. Coach v1 (lectura)** | Orchestrator, tools de lectura, safety gate, chat con contexto, "¿qué hago hoy?" | Hablo con el coach sin darle contexto a mano |
| **4. Plan y replanificación** | Biblioteca de workouts, generador semanal, validador, propuestas aceptables, diario | "Mañana sólo tengo 1 hora" cambia el calendario de forma coherente |
| **5. Workouts ejecutables** | Exportación ZWO y FIT, Wahoo Plans (tras verificar la API) | La sesión aparece en mi ELEMNT |
| **6. Salud y diario avanzado** | Voz al diario (n8n), sueño, HRV y ciclo (fuentes por validar), readiness | El coach ajusta la sesión según mi sueño y lo que le cuento |
| **7. Nutrición** | Objetivos diarios según la carga planificada, avituallamiento en carrera, menús | Carbohidratos del día según el entreno |

Hay dos cambios respecto a tu propuesta: los **best efforts suben a la fase 2** (salen gratis del mismo parseo del FIT) y **n8n entra pronto** (1.5) porque aporta valor de uso real y de portfolio desde el principio.

---

## 11. Primer conjunto de tareas

**T0. Seguridad (lo haces tú; es urgente)**
1. Portal de desarrolladores de Wahoo: **regenerar el client secret** de la app cuyo Client ID está en el código (ver 12.1).
2. En tu cuenta de Wahoo, **revocar el acceso** de la app para invalidar los tokens que se filtraron.
3. Decidir entre poner el repo en **privado** o purgar el historial (`git filter-repo`). Rotar es obligatorio en cualquier caso.
4. Confirmar que el proyecto Supabase pausado es `ofeapnttdjbsyaquslwd` y crear un proyecto nuevo y limpio para el esquema v1 (ver 12.2).

**T1. Consolidar ramas**
- Etiquetar `legacy/v0-auth-fix` y `legacy/v0-connector`. Borrar `agentA` y `agentB`.
- Usar `main` como tronco del monorepo (ya tiene `apps/api`) y moverlo a rama por defecto. Mover `mobile_app` a `apps/mobile` (partiendo de `auth-fix` con el código de sync y export de `connector`).

**T2. Esqueleto de la API**: `pyproject` (fastapi, sqlalchemy 2, alembic, pydantic-settings, httpx, fitdecode, numpy, pytest, ruff, mypy), `core/config`, verificación del JWT de Supabase, `/health`, CI en GitHub Actions.

**T3. Esquema v1**: modelos SQLAlchemy de la sección 9 (al menos profile, thresholds, integrations, activities, calendar_events y races) + migración Alembic inicial + RLS como defensa adicional.

**T4. Wahoo en el backend**: `GET /integrations/wahoo/authorize` (con `state` firmado), `GET /auth/wahoo/callback` (**misma ruta que la actual en Render**), cifrado de tokens, refresco automático, sync paginado e idempotente, descarga del FIT. Tests con respuestas grabadas. *Primero hay que verificar en la documentación oficial los endpoints, scopes, paginación, workout summary y webhooks: no se ha podido consultar desde esta sesión.*

**T5. Métricas v0**: `metrics/zones.py` (Coggan y Friel), `metrics/load.py` (TSS por potencia, hrTSS como alternativa y CTL/ATL/TSB con constantes de 42 y 7 días), con tests unitarios de valores conocidos.

**T6. App**: TypeScript + expo-router, quitar las llamadas directas a Wahoo y a las tablas, cliente API, variables de entorno, eliminar los números inventados del dashboard.

**T7. n8n**: `docker-compose.n8n.yml`, workflow "Sync Wahoo cada 3 h", endpoint `/internal/sync/wahoo` protegido con API key.

---

## 12. Decisiones tomadas tras la auditoría

### 12.1 Wahoo: hay dos apps registradas

| App | Callback URLs registradas | Uso en CoachIA |
|---|---|---|
| **Producción** | `https://letismartcoach.onrender.com/auth/wahoo/callback`, `https://9e873d7ca2f2.ngrok-free.app/auth/wahoo/callback` | **Uso real.** La nueva API se despliega en el **mismo servicio de Render** (`letismartcoach`) y mantiene la ruta `/auth/wahoo/callback`, así que no hay que tocar nada aprobado. |
| **Sandbox** | `exp://192.168.68.73:8081/--/wahoo-callback`, `https://187525c767f3.ngrok-free.app/auth/wahoo/callback`, `https://letismartcoach.onrender.com/auth/wahoo/callback` | Desarrollo local. Conviene usar un **dominio estático de ngrok** en lugar de URLs aleatorias. |

- Según el portal, una app sandbox **no se puede convertir** en producción, pero ya tenemos las dos.
- **Webhook Enabled: false** en producción. En las fases 1 y 1.5 el sync se hace por **polling programado desde n8n**. Activar el webhook queda como mejora futura, y hay que verificar antes el formato del payload en la documentación.
- Cambio de flujo: el **intercambio de `code` por tokens lo hace el propio callback en la API**, que después redirige a la app con `?wahoo=connected` o un error. El `code` ya no viaja hasta el cliente.
- Rotar el secret de la app cuyo Client ID empieza por `NNWFuab…`, que es el que está en el código. Si hay dudas, rotar el de ambas.

### 12.2 Supabase
- En la organización *letiimartin's Org* (plan Free) hay un proyecto **pausado** en `eu-central-1`. Para confirmar que es el de la app, el identificador que aparece en la URL del panel (`/dashboard/project/<ref>`) debe ser `ofeapnttdjbsyaquslwd`.
- Decisión: **BD limpia** con el esquema v1 de Alembic. Los datos antiguos eran en su mayoría simulados. Si se puede restaurar el proyecto, sólo se revisa por si hubiera algo aprovechable.
- Los proyectos Free se pausan por inactividad. El sync programado de n8n mantiene el proyecto activo.

### 12.3 Presupuesto de LLM: 50 €/año (unos 4 €/mes)
Es **ajustado pero viable** para un único usuario, siempre que el diseño ayude:
- El código hace todos los cálculos y el LLM sólo razona sobre **resúmenes compactos** que devuelven las tools, nunca sobre JSON crudo.
- **Modelo económico** para el chat, el router de intenciones y la extracción del diario. El **modelo de más calidad** se reserva para la planificación semanal (unas 4 llamadas al mes).
- Prompt caching del system prompt y de las definiciones de tools.
- **Guardia de presupuesto en código**: se registran los tokens y el coste por mensaje en `coach_messages` y hay un límite mensual duro con degradación a respuestas por reglas. Además, límite de gasto en la consola del proveedor.
- Estimación orientativa: unas 15 llamadas al día de ~8k tokens de entrada son ~4 M de tokens de entrada al mes. Con modelos de gama económica (unos 0,15–0,30 $/M de entrada) sale por 1–3 $/mes. Con modelos de gama media o alta no cabe para el chat diario. **Hay que verificar los precios oficiales al elegir.**

### 12.4 Reloj: Suunto Race S
- Fuente principal de **carrera y trail** (y probablemente de sueño, HRV y FC en reposo). El Wahoo queda como fuente principal de **ciclismo**.
- La **Suunto Cloud API** existe (OAuth2, workouts en FIT y actividad diaria), pero va por un **programa de partners orientado a empresas**. Según su FAQ, **no expone sueño**, y no hay confirmación de que exponga HRV. → Solicitarla es opcional y no bloquea nada.
- Plan pragmático:
  1. Actividades de Suunto mediante **sincronización de Suunto con Strava** y la API de Strava, o subida manual del FIT. Hay que revisar las condiciones de la API de Strava sobre el uso de datos con IA.
  2. Sueño, HRV y FC en reposo, de menos a más esfuerzo:
     - **check-in matinal** (app o Telegram con n8n): "horas de sueño, HRV de Suunto, cómo estás";
     - **Health Connect** (Android) o **HealthKit** (iOS) desde la app Expo con *development build*, si la app de Suunto escribe esos datos allí (**por verificar**).
- **Deduplicación** obligatoria: la misma salida puede llegar desde el Wahoo y desde el reloj. Se resuelve con una regla por solapamiento de horario y se da prioridad a la fuente con potencia.

### 12.5 Repositorio nuevo (opción B)
- El desarrollo continúa en **`letiimartin/coachIA`**, que empieza con un único commit inicial y **sin el historial** que contenía credenciales.
- `LetiSmartCoach` pasa a **privado o archivado** y conserva el historial completo del MVP (ramas `mvp/*`, `master`, `main`).
- Supabase: proyecto nuevo **`coachia`** (`oyvephnvtecwythnikea`). El proyecto antiguo pausado no se usa.
- Las rutas `legacy_backend/`, `mobile_app/` y `supabase/` que se citan en las secciones 1-6 corresponden ahora a `legacy/render-backend/`, `apps/mobile/` y `legacy/supabase/`.

### 12.6 Convenciones del repositorio
- Ramas con nombres convencionales: `feat/…`, `fix/…`, `chore/…`, `docs/…`, `refactor/…` (por ejemplo `feat/wahoo-sync-backend`). Nada de prefijos de herramientas ni nombres aleatorios.
