# Backend legacy (Render)

Servicio `letismartcoach` en Render. Su única función en uso es **`GET /auth/wahoo/callback`**, la Redirect URI registrada en las apps de Wahoo (sandbox y producción). Recibe el `code` y redirige a la app (deep link `letismartcoach://wahoo-callback` o web).

## ⚠️ Antes de fusionar la reestructuración en la rama que despliega Render
Este código estaba antes en `legacy_backend/`, con un `requirements.txt` en la raíz. Tras moverlo, hay que revisar en el panel de Render (Settings) del servicio:

| Ajuste | Valor |
|---|---|
| Branch | la rama que despliega (comprobar si es `master`) |
| Root Directory | `legacy/render-backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

Los routers `athlete`, `calendar`, `coach` y `session` aceptan `user_id` por query sin autenticación. **No deben exponerse con una clave `service_role`.** Se eliminarán cuando `apps/api` asuma el callback (tarea T4).
