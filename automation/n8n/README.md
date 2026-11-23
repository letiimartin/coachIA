# n8n (automatizaciones)

n8n **orquesta**; la lógica vive en la API. Los workflows sólo llaman a los endpoints `/internal/*` con la
cabecera `X-Internal-API-Key`, y se versionan aquí en JSON.

> [!WARNING]
> **No actives estos workflows contra producción sin autorización de la autora.** Se versionan con
> `active: false` y el CI rechaza cualquier workflow activo o con URLs o claves de producción. Desplegar n8n
> (Railway, Render…) y activar el cron son decisiones pendientes de la autora.

| Fichero | Qué hace |
|---|---|
| `docker-compose.n8n.yml` | n8n local, versión fijada, volumen `n8n_data` y variables desde `.env` |
| `.env.example` | Variables del compose (sin secretos) |
| `workflows/ping.json` | Disparador manual → `GET {API_BASE_URL}/internal/ping`: comprueba la conexión y la clave |
| `workflows/sync-wahoo.json` | Cron cada 3 h (y disparador manual) → `POST {API_BASE_URL}/internal/sync/wahoo` |
| `workflows/budget-alerts.json` | Cron cada hora (y disparador manual) → avisos de gasto del LLM por email (ver abajo) |
| `n8n_workflows.py` | Comprueba los JSON (lo usa el CI) y normaliza las exportaciones de n8n |

## 1. Levantar la API local con una clave de prueba

En `apps/api` (ver su README), con una BD **de pruebas** (por ejemplo `eval "$(scripts/test-db.sh)"` y
`DATABASE_URL=$TEST_DATABASE_URL uv run alembic upgrade head`):

```bash
cd apps/api
export INTERNAL_API_KEY=clave-de-prueba-local          # inventada, sólo para local
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

n8n corre en Docker y llega a la API por `host.docker.internal`. En Docker Desktop (macOS y Windows) basta
con el `--host` por defecto (`127.0.0.1`); **en Linux** la API tiene que escuchar en la interfaz de Docker
(`--host 0.0.0.0`, o la IP de `docker0`, normalmente `172.17.0.1`).

`/internal/sync/wahoo` además necesita `DATABASE_URL`, `TOKEN_ENCRYPTION_KEY` y las variables de Wahoo. Sin
integraciones activas responde `{"integrations": 0, ...}`. Para probar sin llamar a Wahoo, apunta
`WAHOO_API_BASE_URL` a un servidor falso local.

## 2. Levantar n8n

```bash
cp automation/n8n/.env.example automation/n8n/.env
# Rellena N8N_ENCRYPTION_KEY (openssl rand -hex 32). API_BASE_URL apunta por defecto a la API local.
C="docker compose -f automation/n8n/docker-compose.n8n.yml --env-file automation/n8n/.env"
$C up -d
```

El editor queda en <http://localhost:5678> (sólo en localhost). La primera vez pide crear el usuario
propietario local. Para pararlo: `$C down` (los datos siguen en el volumen `n8n_data`; `$C down -v` los borra).

`API_BASE_URL` llega a los workflows como `{{ $env.API_BASE_URL }}`. Por eso el compose pone
`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`: las expresiones pueden leer las variables de entorno del contenedor, así
que no metas en él más secretos que los imprescindibles.

## 3. Crear las credenciales

La clave interna nunca va dentro del JSON del workflow: es una credencial de n8n, cifrada en su volumen.

**Desde el editor:** *Credentials → Add credential → Header Auth*:

- Nombre: `CoachIA API interna`
- Name: `X-Internal-API-Key`
- Value: la clave de prueba (`clave-de-prueba-local`)

Después, abre cada workflow importado y, en su nodo HTTP, elige esa credencial si no aparece seleccionada (los
workflows la referencian con el id `coachiainternal1`; una credencial creada en el editor tiene otro id).

**Desde la CLI** (conserva el id, así que los workflows la encuentran sin tocar nada):

```bash
printf '[{"id":"coachiainternal1","name":"CoachIA API interna","type":"httpHeaderAuth","data":{"name":"X-Internal-API-Key","value":"%s"}}]' \
  "clave-de-prueba-local" | $C exec -T n8n n8n import:credentials --input=/dev/stdin
```

La clave se lee de la entrada estándar: no queda en ningún fichero ni en el repositorio.

**SMTP (sólo para `budget-alerts.json`):** *Credentials → Add credential → SMTP*, con el nombre `CoachIA SMTP`
(el workflow la referencia con el id `coachiasmtp00001`) y el servidor de correo que elija la autora. Para
probar en local sin enviar correos de verdad sirve un servidor SMTP falso (por ejemplo Mailpit). Las
direcciones van en `COACH_ALERTS_EMAIL_FROM` y `COACH_ALERTS_EMAIL_TO` de `.env`.

## 4. Importar los workflows

```bash
$C exec -T n8n n8n import:workflow --separate --input=/workflows
```

Se importan inactivos. Para probarlos: ábrelos y pulsa *Execute workflow*, o desde la CLI
(`N8N_RUNNERS_BROKER_PORT` evita el choque con el n8n que ya está en marcha):

```bash
$C exec -T -e N8N_RUNNERS_BROKER_PORT=5690 n8n n8n execute --id coachiaping00001
$C exec -T -e N8N_RUNNERS_BROKER_PORT=5690 n8n n8n execute --id coachiasyncwahoo
$C exec -T -e N8N_RUNNERS_BROKER_PORT=5690 n8n n8n execute --id coachiabudgetalr
```

## 5. Exportar los cambios al repositorio

n8n exporta campos propios de la instancia (proyecto y usuario propietario, fechas, versiones, datos
estáticos). `n8n_workflows.py normalize` los quita, fuerza `active: false`, vacía los datos fijados, escribe
cada workflow en su fichero (por id; si es nuevo, con el nombre en minúsculas) y ejecuta la comprobación:

```bash
$C exec -T -e N8N_LOG_LEVEL=silent n8n n8n export:workflow --all --output=/dev/stdout \
  | python3 automation/n8n/n8n_workflows.py normalize
git diff automation/n8n/workflows
```

Antes de subirlo: `python3 automation/n8n/n8n_workflows.py check` (lo mismo que el CI,
`.github/workflows/automation.yml`). Comprueba que cada JSON es válido y está inactivo, que no lleva datos
fijados ni cabeceras, que las llamadas HTTP usan `{{ $env.API_BASE_URL }}` y la credencial de cabecera, que los
emails toman las direcciones de `$env`, y que no hay URLs que no sean locales, direcciones de correo ni nada con
forma de clave o token.

## Sync de Wahoo: cómo trata cada resultado

`POST /internal/sync/wahoo` sincroniza todas las integraciones activas, empezando por las que llevan más tiempo
sin sincronizar, y devuelve `{integrations, succeeded, failed, rate_limited, created, updated, unchanged}`.

| Resultado | Rama del workflow | Estado de la ejecución |
|---|---|---|
| API caída o error de red | *Error: API no disponible* | error |
| HTTP distinto de 200 (clave incorrecta, 503 sin Wahoo configurado…) | *Error: respuesta de la API* (código, mensaje y `request_id`) | error |
| Fallan usuarios (`failed` sin contar el corte por límite) | *Error: fallos de usuarios* (el detalle está en los logs de la API) | error |
| `rate_limited: true` | *Límite de Wahoo*: el resto se sincroniza en la próxima ejecución | correcto |
| Todo bien | *Sync correcto* | correcto |

Las ejecuciones con error quedan registradas en *Executions* (se guardan una semana). La sincronización es
idempotente: repetirla no duplica actividades. No hay reintentos dentro de la ejecución; el siguiente intento
es la ejecución programada siguiente.

## Avisos de gasto del LLM

El gasto del LLM es cosa del equipo, no de la atleta (#61). Cuando el gasto del mes de una atleta cruza el
**80 %** y el **100 %** del límite mensual (`COACH_MONTHLY_BUDGET_EUR`, 4 € por defecto), se envía un email a los
desarrolladores, **una vez por umbral y mes**. La lógica está en la API; el workflow sólo la orquesta:

1. `GET /internal/coach/budget-alerts` devuelve los avisos pendientes (umbrales cruzados este mes, en la zona
   horaria de la atleta, y aún no enviados). Cada aviso trae su `key`, las cifras (mes, gasto, límite, llamadas
   y desglose por modelo) y el email ya redactado (`subject`, `text`). Nunca lleva contenido de las
   conversaciones ni datos de salud; identifica a la atleta sólo por su id.
2. El workflow envía un email por aviso (credencial SMTP) y, si se envía, lo confirma con
   `POST /internal/coach/budget-alerts/sent` (`{"keys": [...]}`). La API lo registra en `coach_budget_alerts`
   y deja de devolverlo. Sólo registra avisos pendientes: una clave de un umbral aún no cruzado se ignora.

| Resultado | Rama del workflow | Estado de la ejecución |
|---|---|---|
| API caída o HTTP distinto de 200 | *Error: API no disponible* / *Error: respuesta de la API* | error |
| No hay avisos | *Sin avisos* | correcto |
| El email falla | *Error: email no enviado*: no se confirma, se reintenta en la próxima ejecución | error |
| El email sale pero la confirmación falla | *Error: confirmación no registrada*: el aviso puede repetirse | error |
| Todo bien | *Aviso enviado* | correcto |

Al llegar al 100 % el coach deja de llamar al LLM (como antes) y la atleta ve un mensaje neutro, sin cifras.

## Decisiones pendientes (de la autora)
- Dónde se aloja n8n (Railway, Render…) y la frecuencia final del sync (por defecto, cada 3 h).
- Activar los cron contra producción.
- Avisos de gasto: el servidor SMTP (o servicio de envío) y las direcciones de `COACH_ALERTS_EMAIL_*`.
