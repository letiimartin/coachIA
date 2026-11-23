// Generado por scripts/gen-api.mjs a partir de apps/api/openapi.json. No editar a mano.
export interface paths {
    "/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Root */
        get: operations["root__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/auth/wahoo/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Wahoo Callback */
        get: operations["wahoo_callback_auth_wahoo_callback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Readiness */
        get: operations["readiness_health_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/internal/coach/budget-alerts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Budget Alerts
         * @description Avisos de gasto del LLM pendientes (para n8n): umbrales del 80 % y del 100 % del límite
         *     mensual cruzados este mes y aún no enviados. Uno por atleta, mes y umbral.
         *
         *     n8n envía cada aviso por email y después confirma el envío con `POST .../sent`; hasta
         *     entonces el aviso sigue apareciendo aquí.
         */
        get: operations["list_budget_alerts_internal_coach_budget_alerts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/internal/coach/budget-alerts/sent": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Mark Budget Alerts Sent
         * @description Registra como enviados los avisos con esas claves, para no repetirlos.
         *
         *     Sólo se registran avisos pendientes: las claves ya registradas, de otro mes o de un umbral
         *     no cruzado se ignoran (`ignored`).
         */
        post: operations["mark_budget_alerts_sent_internal_coach_budget_alerts_sent_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/internal/ping": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ping
         * @description Permite a n8n comprobar que la API responde y que su clave es correcta.
         */
        get: operations["ping_internal_ping_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/internal/sync/wahoo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Sync Wahoo All
         * @description Sincroniza las actividades de todas las integraciones de Wahoo activas (para n8n).
         *
         *     Si Wahoo aplica el límite de peticiones se detiene (`rate_limited`): el resto de usuarios se
         *     sincroniza en la siguiente ejecución, empezando por los que llevan más tiempo sin hacerlo.
         */
        post: operations["sync_wahoo_all_internal_sync_wahoo_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/availability": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Availability
         * @description Disponibilidad de los 7 días (con valores por defecto en los días sin rellenar).
         */
        get: operations["get_availability_v1_athlete_availability_get"];
        /**
         * Replace Availability
         * @description Sustituye la disponibilidad de la semana entera (hay que enviar los 7 días).
         */
        put: operations["replace_availability_v1_athlete_availability_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/fitness": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Fitness Series
         * @description Carga diaria y CTL/ATL/TSB de cada día del rango `[from, to]` (máximo 366 días).
         */
        get: operations["get_fitness_series_v1_athlete_fitness_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/profile": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Profile
         * @description Perfil del atleta. Si no existe todavía, se crea con los valores por defecto.
         */
        get: operations["get_profile_v1_athlete_profile_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * Update Profile
         * @description Actualiza sólo los campos enviados y devuelve el perfil completo.
         */
        patch: operations["update_profile_v1_athlete_profile_patch"];
        trace?: never;
    };
    "/v1/athlete/threshold-proposals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Proposals
         * @description Propuestas del atleta, de la más reciente a la más antigua.
         */
        get: operations["list_proposals_v1_athlete_threshold_proposals_get"];
        put?: never;
        /**
         * Create Proposal
         * @description Descarga el FIT de la actividad, detecta el test y crea una propuesta **pendiente**.
         *
         *     No cambia ningún umbral. Errores 422 con `code`: `not_cycling`, `fit_unavailable` (sin
         *     fichero), `fit_invalid` (dañado o sin registros), y los criterios que bloquean la
         *     propuesta, con el criterio evaluado (valor medido, umbral, mensaje) en `error.details`:
         *     `no_power_data`, `test_too_short`, `insufficient_data` (demasiados huecos) y
         *     `ftp_out_of_range`. 409 si ya hay una propuesta pendiente de esa actividad.
         */
        post: operations["create_proposal_v1_athlete_threshold_proposals_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/threshold-proposals/{proposal_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Proposal */
        get: operations["get_proposal_v1_athlete_threshold_proposals__proposal_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/threshold-proposals/{proposal_id}/accept": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Accept Proposal
         * @description Acepta la propuesta tal como la mostró la vista previa (`action` y `previous_ftp_w`).
         *
         *     - `create_row`: crea un umbral vigente desde `test_date` con `source = test`, el FTP
         *       propuesto y el resto de valores copiados del umbral vigente ese día.
         *     - `update_ftp`: cambia sólo el `ftp_w` de la fila de `test_date`; conserva el resto.
         *
         *     La fila guarda la propuesta de la que sale su FTP; los registros posteriores no se tocan.
         *     No lanza ningún recálculo histórico: sólo se rellena la carga de las actividades que no la
         *     tienen y se regenera la forma. 409 `preview_outdated` (con la vista previa nueva en
         *     `error.details`) si la acción o el FTP anterior ya no coinciden; 409 `conflict` si la
         *     propuesta no está pendiente.
         */
        post: operations["accept_proposal_v1_athlete_threshold_proposals__proposal_id__accept_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/threshold-proposals/{proposal_id}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Preview Acceptance
         * @description Vista previa de aceptar la propuesta, sin guardar nada.
         *
         *     `action`: `create_row` (no hay umbrales en `test_date`) o `update_ftp` (ya hay una fila en
         *     esa fecha; sólo cambiaría su FTP). Incluye el FTP anterior de esa fecha, el propuesto y la
         *     ventana de vigencia del FTP nuevo; si hay registros posteriores, el aviso
         *     `later_thresholds` y el siguiente registro. 409 si la propuesta no está pendiente.
         */
        get: operations["preview_acceptance_v1_athlete_threshold_proposals__proposal_id__preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/threshold-proposals/{proposal_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reject Proposal
         * @description Rechaza la propuesta. No cambia ningún umbral. 409 si no está pendiente.
         */
        post: operations["reject_proposal_v1_athlete_threshold_proposals__proposal_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/threshold-proposals/dry-run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Dry Run
         * @description Análisis de prueba: descarga el FIT y analiza el test **sin crear ninguna propuesta**.
         *
         *     Devuelve el intervalo detectado, sus métricas, el FTP propuesto y la evaluación de cada
         *     criterio de calidad. Sirve para validar la descarga y la lectura del FIT. Mismos errores
         *     que crear la propuesta, salvo el 409 (no se crea nada).
         */
        post: operations["dry_run_v1_athlete_threshold_proposals_dry_run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/thresholds": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Thresholds
         * @description Historial de umbrales, del más reciente al más antiguo (por `effective_from`).
         */
        get: operations["list_thresholds_v1_athlete_thresholds_get"];
        put?: never;
        /**
         * Create Threshold
         * @description Registra umbrales vigentes desde `effective_from`. 409 si ya hay umbrales en esa fecha.
         */
        post: operations["create_threshold_v1_athlete_thresholds_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/athlete/thresholds/current": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Current Threshold
         * @description Umbral vigente en la fecha y zonas calculadas a partir de él. 404 si no hay ninguno.
         */
        get: operations["get_current_threshold_v1_athlete_thresholds_current_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/calendar/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Events
         * @description Eventos que se solapan con el rango `[from, to]`, ordenados por `start_at`. Sin paginar.
         */
        get: operations["list_events_v1_calendar_events_get"];
        put?: never;
        /** Create Event */
        post: operations["create_event_v1_calendar_events_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/calendar/events/{event_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Delete Event
         * @description Borra el evento (y sus datos de carrera, si los tiene).
         */
        delete: operations["delete_event_v1_calendar_events__event_id__delete"];
        options?: never;
        head?: never;
        /**
         * Update Event
         * @description Actualiza sólo los campos enviados. 409 si el evento resultante no es coherente.
         */
        patch: operations["update_event_v1_calendar_events__event_id__patch"];
        trace?: never;
    };
    "/v1/coach/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Conversations
         * @description Conversaciones de la atleta, de la más reciente a la más antigua.
         */
        get: operations["list_conversations_v1_coach_conversations_get"];
        put?: never;
        /**
         * Create Conversation
         * @description Crea una conversación. La primera es la toma de contacto: el coach lee primero lo que
         *     ya sabe de la atleta y abre la conversación con sus primeras preguntas (`opening`).
         *
         *     503 `coach_unavailable` si es una toma de contacto y no hay proveedor configurado; 502
         *     `coach_llm_error` si el LLM falla al abrirla (la conversación queda creada, vacía).
         */
        post: operations["create_conversation_v1_coach_conversations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/coach/conversations/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Conversation */
        get: operations["get_conversation_v1_coach_conversations__conversation_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/coach/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Messages
         * @description Los últimos `limit` mensajes de la atleta y del coach, en orden. Los resultados de
         *     herramientas se guardan para auditoría, pero no se devuelven.
         */
        get: operations["list_messages_v1_coach_conversations__conversation_id__messages_get"];
        put?: never;
        /**
         * Send Message
         * @description Envía un mensaje y devuelve la respuesta completa del coach.
         *
         *     - Si el mensaje habla de dolor torácico, mareo, desmayo o lesión aguda, la respuesta es
         *       fija, recomienda una valoración médica y no llama al LLM (`origin = safety_filter`).
         *     - Si el presupuesto del mes está agotado, la respuesta es fija (`origin = budget_limit`).
         *     - `memory_proposals`: lo que el coach propone recordar; la atleta lo confirma aparte.
         *
         *     503 `coach_unavailable` si no hay proveedor (salvo el filtro de seguridad, que responde
         *     igual). 502 `coach_llm_error` si el LLM falla: el mensaje no se guarda y se puede
         *     reenviar.
         */
        post: operations["send_message_v1_coach_conversations__conversation_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/coach/memory": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Memory
         * @description Memoria del coach. Con `status=proposed`, lo que el coach ha propuesto y está pendiente
         *     de confirmar.
         */
        get: operations["list_memory_v1_coach_memory_get"];
        put?: never;
        /**
         * Create Memory
         * @description La atleta añade un objetivo o una preferencia: queda confirmado.
         */
        post: operations["create_memory_v1_coach_memory_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/coach/memory/{memory_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /**
         * Delete Memory
         * @description Borra un elemento de memoria: el coach deja de tenerlo en cuenta.
         */
        delete: operations["delete_memory_v1_coach_memory__memory_id__delete"];
        options?: never;
        head?: never;
        /**
         * Update Memory
         * @description Corrige un elemento confirmado. 409 si no está confirmado.
         */
        patch: operations["update_memory_v1_coach_memory__memory_id__patch"];
        trace?: never;
    };
    "/v1/coach/memory/{memory_id}/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Confirm Memory
         * @description Confirma una propuesta del coach, con la corrección si se envía. 409 si no está
         *     pendiente. Cuando no queda nada pendiente en una toma de contacto, queda hecha.
         */
        post: operations["confirm_memory_v1_coach_memory__memory_id__confirm_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/coach/memory/{memory_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Reject Memory
         * @description Descarta una propuesta del coach. 409 si no está pendiente.
         */
        post: operations["reject_memory_v1_coach_memory__memory_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/coach/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Status
         * @description Si el coach está disponible, el estado de la toma de contacto y el presupuesto del mes.
         *
         *     La app sólo usa `budget.state == exhausted` para saber si el coach puede responder; las
         *     cifras no se muestran a la atleta (los avisos de gasto van a los desarrolladores, #61).
         */
        get: operations["get_status_v1_coach_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/integrations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Integrations */
        get: operations["list_integrations_v1_integrations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/integrations/wahoo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Disconnect Wahoo */
        delete: operations["disconnect_wahoo_v1_integrations_wahoo_delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/integrations/wahoo/authorize-url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Wahoo Authorize Url
         * @description URL a la que la app debe enviar al usuario para autorizar CoachIA en Wahoo.
         */
        get: operations["wahoo_authorize_url_v1_integrations_wahoo_authorize_url_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/integrations/wahoo/sync": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Sync Wahoo
         * @description Importa las actividades realizadas en Wahoo. Es idempotente: se puede repetir sin riesgo.
         */
        post: operations["sync_wahoo_v1_integrations_wahoo_sync_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Me */
        get: operations["read_me_v1_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/planned-workouts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Planned Workouts
         * @description Entrenos planificados de cualquier disciplina con fecha en `[from, to]`, por fecha.
         *
         *     Sin paginar: el rango máximo es de 366 días. Cada entreno trae su número de ejercicios, su
         *     duración planificada (null si no se ha definido) y, si está hecho, la real de su actividad.
         *     El detalle de una sesión de fuerza está en `GET /v1/strength/workouts/{id}`.
         */
        get: operations["list_planned_workouts_v1_planned_workouts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/exercises": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Search Exercises
         * @description Catálogo de ejercicios (los del sistema y los propios).
         *
         *     Con `q`, primero los que empiezan por la búsqueda y después el resto, por nombre.
         */
        get: operations["search_exercises_v1_strength_exercises_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/exercises/{exercise_id}/last-log": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Exercise Last Log
         * @description Series del ejercicio (peso y repeticiones o segundos) en la última sesión completada.
         *
         *     Con `before_workout_id`, la última sesión completada **anterior** a ese entreno, sin contarlo:
         *     si está completado, anterior al inicio de su actividad; si no, cualquiera. Si nunca se ha
         *     registrado, `performed_on` es null y `sets` está vacía. 404 si el ejercicio o el entreno no
         *     existen.
         */
        get: operations["exercise_last_log_v1_strength_exercises__exercise_id__last_log_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/exercises/{exercise_id}/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Exercise Progress
         * @description Progresión de un ejercicio: una entrada por sesión completada, por fecha.
         *
         *     Por sesión: series hechas, repeticiones o segundos totales, peso máximo, volumen (suma de
         *     repeticiones × peso) y repeticiones (o segundos) de la mejor serie. Sólo cuentan las
         *     series hechas (`completed`) de sesiones completadas. 404 si el ejercicio no existe.
         */
        get: operations["exercise_progress_v1_strength_exercises__exercise_id__progress_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Performed Exercises
         * @description Ejercicios hechos en sesiones completadas, del último hecho al más antiguo.
         *
         *     Cada uno con su número de sesiones, la primera y la última fecha y el peso máximo de la
         *     última sesión. Vacía si todavía no se ha completado ninguna sesión con series.
         */
        get: operations["performed_exercises_v1_strength_progress_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/weekly": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Strength Weekly
         * @description Resumen semanal de fuerza: sesiones, duración y carga `session_rpe` de cada semana.
         *
         *     Una semana (de lunes a domingo, días locales) por cada lunes desde la semana de `from`
         *     hasta la de `to` (rango máximo de 366 días), con 0 en las semanas sin fuerza. Es una
         *     carga distinta de la de resistencia: no suma en `GET /v1/athlete/fitness`.
         */
        get: operations["strength_weekly_v1_strength_weekly_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/workouts/{workout_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Strength Workout
         * @description Sesión de fuerza: ejercicios planificados, series hechas y, si está completada, su
         *     actividad. 422 `not_strength` si el entreno es de otra disciplina.
         */
        get: operations["get_strength_workout_v1_strength_workouts__workout_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/workouts/{workout_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Complete Workout
         * @description Completa la sesión: crea la actividad de fuerza y marca el entreno como hecho.
         *
         *     La actividad lleva `sport = strength`, `source = manual`, la duración y el `rpe`; su carga
         *     es `session_rpe` (minutos × RPE), que no suma en CTL/ATL/TSB. El `rpe` es opcional: sin él
         *     la sesión queda hecha, pero sin carga. Las series registradas pasan
         *     a la actividad. 409 si el entreno ya está hecho o saltado; 422 `not_strength`.
         */
        post: operations["complete_workout_v1_strength_workouts__workout_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/v1/strength/workouts/{workout_id}/sets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /**
         * Replace Sets
         * @description Registra o edita las series: la lista sustituye a todas las registradas antes.
         *
         *     Se puede usar durante el entreno (enviando la lista acumulada) y después de completarlo.
         *     409 si el entreno está saltado. 422 con `code`: `not_strength`,
         *     `unknown_planned_exercise`, `unknown_exercise`, `mode_mismatch` y `duplicate_set`.
         */
        put: operations["replace_sets_v1_strength_workouts__workout_id__sets_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/webhooks/strava": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Verify Subscription */
        get: operations["verify_subscription_webhooks_strava_get"];
        put?: never;
        /** Receive Event */
        post: operations["receive_event_webhooks_strava_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * AcceptAction
         * @description Qué hace aceptar una propuesta (#45). No se guarda: se calcula en la vista previa.
         * @enum {string}
         */
        AcceptAction: "create_row" | "update_ftp";
        /**
         * AcceptancePreviewOut
         * @description Qué cambiaría al aceptar la propuesta. No guarda nada.
         *
         *     - `create_row`: no hay umbrales en `test_date`; se crearía una fila con `source = test`,
         *       el FTP propuesto y el resto de valores copiados del umbral vigente ese día.
         *     - `update_ftp`: ya hay una fila en `test_date` (`threshold_id`); sólo cambiaría su
         *       `ftp_w`, el resto de valores se conservan.
         *
         *     El FTP nuevo regiría desde `effective_from` (= `test_date`) hasta `effective_until`
         *     (el día anterior al siguiente registro, `next_threshold`), o sin fin si es null. Los
         *     registros posteriores no se tocan nunca.
         * @example {
         *       "action": "update_ftp",
         *       "effective_from": "2026-11-15",
         *       "effective_until": "2026-11-30",
         *       "next_threshold": {
         *         "effective_from": "2026-12-01",
         *         "ftp_w": 235,
         *         "id": "6e3d2c1b-0a9f-4b8c-9d7e-6f5a4b3c2d1e"
         *       },
         *       "previous_ftp_w": 220,
         *       "proposal_id": "3f6c1d2e-8a4b-4c7d-9e1f-2a3b4c5d6e7f",
         *       "proposed_ftp_w": 230,
         *       "threshold_id": "5d2c1b0a-9e8f-4a7b-8c6d-5e4f3a2b1c0d",
         *       "warnings": [
         *         {
         *           "code": "later_thresholds",
         *           "message": "Hay umbrales registrados desde el 2026-12-01: el FTP nuevo sólo regirá hasta el 2026-11-30 y después seguirá vigente el de ese registro (235 W)."
         *         }
         *       ]
         *     }
         */
        AcceptancePreviewOut: {
            action: components["schemas"]["AcceptAction"];
            /**
             * Effective From
             * Format: date
             */
            effective_from: string;
            /**
             * Effective Until
             * @description Último día de vigencia; null = sin fin.
             */
            effective_until: string | null;
            next_threshold: components["schemas"]["NextThresholdOut"] | null;
            /**
             * Previous Ftp W
             * @description FTP de `test_date` antes de aceptar: el de la fila de esa fecha (`update_ftp`) o el vigente ese día (`create_row`). Null si no había.
             */
            previous_ftp_w: number | null;
            /**
             * Proposal Id
             * Format: uuid
             */
            proposal_id: string;
            /** Proposed Ftp W */
            proposed_ftp_w: number;
            /**
             * Threshold Id
             * @description Fila que se actualizaría (`update_ftp`).
             */
            threshold_id: string | null;
            /** Warnings */
            warnings: components["schemas"]["PreviewWarningOut"][];
        };
        /** AuthorizeUrlOut */
        AuthorizeUrlOut: {
            /** Authorize Url */
            authorize_url: string;
        };
        /**
         * AvailabilityDay
         * @description Disponibilidad habitual de un día de la semana (0 = lunes … 6 = domingo).
         */
        AvailabilityDay: {
            /**
             * Is Preferred Rest
             * @default false
             */
            is_preferred_rest: boolean;
            /**
             * Max Minutes
             * @description Minutos disponibles; null = sin límite fijado.
             */
            max_minutes?: number | null;
            /** @default any */
            preferred_time: components["schemas"]["PreferredTime"];
            /** Sports */
            sports?: components["schemas"]["Sport"][];
            /** Weekday */
            weekday: number;
        };
        /**
         * BudgetAlertOut
         * @description Aviso de gasto del LLM para los desarrolladores. Sólo cifras: nunca contenido de las
         *     conversaciones ni datos de salud. `subject` y `text` son el email ya redactado.
         */
        BudgetAlertOut: {
            /** By Model */
            by_model: components["schemas"]["ModelUsageOut"][];
            /** Calls */
            calls: number;
            /**
             * Key
             * @description Identifica el aviso; se envía a `/sent` tras mandarlo.
             */
            key: string;
            /** Limit Eur */
            limit_eur: number;
            /**
             * Month
             * Format: date
             * @description Primer día del mes (zona horaria de la atleta).
             */
            month: string;
            /** Percent */
            percent: number;
            /** Spent Eur */
            spent_eur: number;
            /** Subject */
            subject: string;
            /** Text */
            text: string;
            /**
             * Threshold
             * @description `warning`: umbral de aviso (80 % por defecto). `limit`: 100 %.
             * @enum {string}
             */
            threshold: "warning" | "limit";
            /** Threshold Eur */
            threshold_eur: number;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /** BudgetAlertsOut */
        BudgetAlertsOut: {
            /** Alerts */
            alerts: components["schemas"]["BudgetAlertOut"][];
        };
        /** BudgetAlertsSent */
        BudgetAlertsSent: {
            /** Keys */
            keys: string[];
        };
        /** BudgetAlertsSentOut */
        BudgetAlertsSentOut: {
            /** Ignored */
            ignored: number;
            /** Recorded */
            recorded: number;
        };
        /**
         * BudgetOut
         * @description Presupuesto mensual del LLM (todas las llamadas del mes, en euros).
         *
         *     - `ok`: por debajo del aviso.
         *     - `warning`: se ha pasado el aviso (80 % por defecto). El aviso es para los
         *       desarrolladores (#61, por n8n): la app no lo muestra a la atleta.
         *     - `exhausted`: se ha llegado al límite; el coach responde con un mensaje fijo sin llamar
         *       al LLM hasta el mes siguiente.
         * @example {
         *       "limit_eur": 4,
         *       "month": "2026-11-01",
         *       "spent_eur": 3.31,
         *       "state": "warning",
         *       "warning_eur": 3.2
         *     }
         */
        BudgetOut: {
            /** Limit Eur */
            limit_eur: number;
            /**
             * Month
             * Format: date
             * @description Primer día del mes (zona horaria de la atleta).
             */
            month: string;
            /** Spent Eur */
            spent_eur: number;
            /**
             * State
             * @enum {string}
             */
            state: "ok" | "warning" | "exhausted";
            /** Warning Eur */
            warning_eur: number;
        };
        /**
         * CalendarEventCreate
         * @description Nuevo evento. Las fechas deben llevar zona horaria (ISO 8601 con desfase).
         *
         *     Si `kind` es `race` y no se envía `race`, se crea la carrera con los valores por defecto.
         * @example {
         *       "all_day": false,
         *       "kind": "race",
         *       "race": {
         *         "ascent_m": 2400,
         *         "discipline": "trail_running",
         *         "distance_m": 42000,
         *         "goal": "Terminar por debajo de 6 h.",
         *         "priority": "A",
         *         "source_url": "https://example.com/carrera"
         *       },
         *       "start_at": "2027-04-18T07:00:00+02:00",
         *       "title": "Trail de la Sierra",
         *       "training_impact": "none"
         *     }
         * @example {
         *       "all_day": true,
         *       "end_at": "2026-12-04T23:59:00+01:00",
         *       "kind": "travel",
         *       "notes": "Hotel con gimnasio.",
         *       "start_at": "2026-12-02T00:00:00+01:00",
         *       "title": "Viaje de trabajo a Lisboa",
         *       "training_impact": "reduce"
         *     }
         */
        CalendarEventCreate: {
            /**
             * All Day
             * @default true
             */
            all_day: boolean;
            /** Details */
            details?: {
                [key: string]: unknown;
            };
            /** End At */
            end_at?: string | null;
            kind: components["schemas"]["EventKind"];
            /** Notes */
            notes?: string | null;
            race?: components["schemas"]["RaceCreate"] | null;
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
            /** Title */
            title: string;
            /** @default none */
            training_impact: components["schemas"]["TrainingImpact"];
        };
        /**
         * CalendarEventOut
         * @example {
         *       "all_day": false,
         *       "created_at": "2026-11-17T10:00:00Z",
         *       "details": {},
         *       "id": "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b",
         *       "kind": "race",
         *       "race": {
         *         "ascent_m": 2400,
         *         "discipline": "trail_running",
         *         "distance_m": 42000,
         *         "enrichment_status": "none",
         *         "goal": "Terminar por debajo de 6 h.",
         *         "priority": "A",
         *         "source_url": "https://example.com/carrera"
         *       },
         *       "start_at": "2027-04-18T05:00:00Z",
         *       "title": "Trail de la Sierra",
         *       "training_impact": "none",
         *       "updated_at": "2026-11-17T10:00:00Z"
         *     }
         */
        CalendarEventOut: {
            /** All Day */
            all_day: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Details */
            details: {
                [key: string]: unknown;
            };
            /** End At */
            end_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            kind: components["schemas"]["EventKind"];
            /** Notes */
            notes: string | null;
            /** @description Sólo en eventos de tipo 'race'. */
            race: components["schemas"]["RaceOut"] | null;
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
            /** Title */
            title: string;
            training_impact: components["schemas"]["TrainingImpact"];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * CalendarEventPatch
         * @description Actualización parcial de un evento: sólo se cambian los campos enviados.
         *
         *     - `end_at` y `notes` admiten `null` para borrarlos; el resto de campos no.
         *     - `race` se fusiona con los datos de carrera existentes (ver `RacePatch`).
         *     - Si `kind` deja de ser `race`, se borran los datos de la carrera.
         *     - La coherencia `end_at >= start_at` se comprueba con el evento resultante (409 si no).
         * @example {
         *       "race": {
         *         "priority": "A"
         *       },
         *       "title": "Trail de la Sierra (42K)"
         *     }
         * @example {
         *       "training_impact": "no_training"
         *     }
         */
        CalendarEventPatch: {
            /** All Day */
            all_day?: boolean | null;
            /** Details */
            details?: {
                [key: string]: unknown;
            } | null;
            /** End At */
            end_at?: string | null;
            kind?: components["schemas"]["EventKind"] | null;
            /** Notes */
            notes?: string | null;
            race?: components["schemas"]["RacePatch"] | null;
            /** Start At */
            start_at?: string | null;
            /** Title */
            title?: string | null;
            training_impact?: components["schemas"]["TrainingImpact"] | null;
        };
        /**
         * CoachReplyOut
         * @description Resultado de un mensaje: el de la atleta, la respuesta completa del coach (sin
         *     streaming), lo que el coach propone recordar (pendiente de confirmar) y el presupuesto.
         */
        CoachReplyOut: {
            budget: components["schemas"]["BudgetOut"];
            /** Memory Proposals */
            memory_proposals: components["schemas"]["MemoryOut"][];
            reply: components["schemas"]["MessageOut"];
            /** @description Null cuando el coach abre la conversación. */
            user_message: components["schemas"]["MessageOut"] | null;
        };
        /** CoachStatusOut */
        CoachStatusOut: {
            /**
             * Available
             * @description Hay un proveedor de LLM configurado.
             */
            available: boolean;
            budget: components["schemas"]["BudgetOut"];
            intake: components["schemas"]["IntakeOut"];
            /**
             * Model
             * @description Modelo que conversa.
             */
            model: string;
        };
        /**
         * Comparison
         * @description Condición que cumple el valor medido frente al umbral cuando el criterio se cumple.
         * @enum {string}
         */
        Comparison: "gt" | "ge" | "lt" | "le";
        /**
         * ConversationChannel
         * @enum {string}
         */
        ConversationChannel: "app";
        /**
         * ConversationCreate
         * @description Sin `kind`, la conversación es una toma de contacto si aún no se ha hecho ninguna y,
         *     si no, una conversación normal. `intake` repite la toma de contacto.
         */
        ConversationCreate: {
            kind?: components["schemas"]["ConversationKind"] | null;
        };
        /** ConversationCreatedOut */
        ConversationCreatedOut: {
            conversation: components["schemas"]["ConversationOut"];
            /** @description En la toma de contacto, el primer mensaje del coach. Null en las demás. */
            opening: components["schemas"]["CoachReplyOut"] | null;
        };
        /**
         * ConversationKind
         * @enum {string}
         */
        ConversationKind: "intake" | "chat";
        /** ConversationOut */
        ConversationOut: {
            channel: components["schemas"]["ConversationChannel"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Intake Completed At */
            intake_completed_at: string | null;
            kind: components["schemas"]["ConversationKind"];
            /** Last Message At */
            last_message_at: string | null;
            /**
             * Summary
             * @description Resumen de los mensajes antiguos (lo mantiene el código).
             */
            summary: string | null;
            /** Title */
            title: string | null;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * CurrentThresholdOut
         * @description Umbral vigente en la fecha `on` (la fila más reciente con `effective_from <= on`).
         * @example {
         *       "on": "2026-11-17",
         *       "threshold": {
         *         "created_at": "2026-11-01T19:00:00Z",
         *         "cycling_lthr_bpm": 165,
         *         "effective_from": "2026-11-01",
         *         "ftp_w": 230,
         *         "hr_max_bpm": 186,
         *         "hr_rest_bpm": 48,
         *         "id": "8d5e2f0a-6b1c-4f3e-9a7d-2c4b6e8f0a1b",
         *         "notes": "Test de 20 min en rodillo.",
         *         "running_lthr_bpm": 172,
         *         "source": "test",
         *         "threshold_pace_s_per_km": 285,
         *         "updated_at": "2026-11-01T19:00:00Z",
         *         "vo2max": 52,
         *         "weight_kg": 58.5
         *       },
         *       "zones": {
         *         "hr_cycling": [
         *           {
         *             "code": "Z1",
         *             "high": 133.7,
         *             "low": 0,
         *             "name": "Recuperación",
         *             "number": 1
         *           },
         *           {
         *             "code": "Z2",
         *             "high": 148.5,
         *             "low": 133.7,
         *             "name": "Resistencia aeróbica",
         *             "number": 2
         *           },
         *           {
         *             "code": "Z3",
         *             "high": 155.1,
         *             "low": 148.5,
         *             "name": "Tempo",
         *             "number": 3
         *           },
         *           {
         *             "code": "Z4",
         *             "high": 165,
         *             "low": 155.1,
         *             "name": "Subumbral",
         *             "number": 4
         *           },
         *           {
         *             "code": "Z5a",
         *             "high": 170,
         *             "low": 165,
         *             "name": "Supraumbral",
         *             "number": 5
         *           },
         *           {
         *             "code": "Z5b",
         *             "high": 174.9,
         *             "low": 170,
         *             "name": "Capacidad aeróbica",
         *             "number": 6
         *           },
         *           {
         *             "code": "Z5c",
         *             "low": 174.9,
         *             "name": "Potencia anaeróbica",
         *             "number": 7
         *           }
         *         ],
         *         "hr_running": [
         *           {
         *             "code": "Z1",
         *             "high": 146.2,
         *             "low": 0,
         *             "name": "Recuperación",
         *             "number": 1
         *           },
         *           {
         *             "code": "Z2",
         *             "high": 154.8,
         *             "low": 146.2,
         *             "name": "Resistencia aeróbica",
         *             "number": 2
         *           },
         *           {
         *             "code": "Z3",
         *             "high": 163.4,
         *             "low": 154.8,
         *             "name": "Tempo",
         *             "number": 3
         *           },
         *           {
         *             "code": "Z4",
         *             "high": 172,
         *             "low": 163.4,
         *             "name": "Subumbral",
         *             "number": 4
         *           },
         *           {
         *             "code": "Z5a",
         *             "high": 177.2,
         *             "low": 172,
         *             "name": "Supraumbral",
         *             "number": 5
         *           },
         *           {
         *             "code": "Z5b",
         *             "high": 182.3,
         *             "low": 177.2,
         *             "name": "Capacidad aeróbica",
         *             "number": 6
         *           },
         *           {
         *             "code": "Z5c",
         *             "low": 182.3,
         *             "name": "Potencia anaeróbica",
         *             "number": 7
         *           }
         *         ],
         *         "power": [
         *           {
         *             "code": "Z1",
         *             "high": 126.5,
         *             "low": 0,
         *             "name": "Recuperación activa",
         *             "number": 1
         *           },
         *           {
         *             "code": "Z2",
         *             "high": 172.5,
         *             "low": 126.5,
         *             "name": "Resistencia",
         *             "number": 2
         *           },
         *           {
         *             "code": "Z3",
         *             "high": 207,
         *             "low": 172.5,
         *             "name": "Tempo",
         *             "number": 3
         *           },
         *           {
         *             "code": "Z4",
         *             "high": 241.5,
         *             "low": 207,
         *             "name": "Umbral",
         *             "number": 4
         *           },
         *           {
         *             "code": "Z5",
         *             "high": 276,
         *             "low": 241.5,
         *             "name": "VO2máx",
         *             "number": 5
         *           },
         *           {
         *             "code": "Z6",
         *             "high": 345,
         *             "low": 276,
         *             "name": "Capacidad anaeróbica",
         *             "number": 6
         *           },
         *           {
         *             "code": "Z7",
         *             "low": 345,
         *             "name": "Neuromuscular",
         *             "number": 7
         *           }
         *         ],
         *         "running_pace": [
         *           {
         *             "code": "Z1",
         *             "low": 367.7,
         *             "name": "Recuperación",
         *             "number": 1
         *           },
         *           {
         *             "code": "Z2",
         *             "high": 367.7,
         *             "low": 324.9,
         *             "name": "Aeróbico",
         *             "number": 2
         *           },
         *           {
         *             "code": "Z3",
         *             "high": 324.9,
         *             "low": 302.1,
         *             "name": "Tempo",
         *             "number": 3
         *           },
         *           {
         *             "code": "Z4",
         *             "high": 302.1,
         *             "low": 285,
         *             "name": "Umbral",
         *             "number": 4
         *           },
         *           {
         *             "code": "Z5",
         *             "high": 285,
         *             "low": 0,
         *             "name": "Por encima del umbral",
         *             "number": 5
         *           }
         *         ],
         *         "trail_hr": [
         *           {
         *             "code": "Z1",
         *             "high": 146.2,
         *             "low": 0,
         *             "name": "Recuperación",
         *             "number": 1
         *           },
         *           {
         *             "code": "Z2",
         *             "high": 154.8,
         *             "low": 146.2,
         *             "name": "Aeróbico",
         *             "number": 2
         *           },
         *           {
         *             "code": "Z3",
         *             "high": 163.4,
         *             "low": 154.8,
         *             "name": "Tempo",
         *             "number": 3
         *           },
         *           {
         *             "code": "Z4",
         *             "high": 172,
         *             "low": 163.4,
         *             "name": "Umbral",
         *             "number": 4
         *           },
         *           {
         *             "code": "Z5",
         *             "low": 172,
         *             "name": "Por encima del umbral",
         *             "number": 5
         *           }
         *         ]
         *       }
         *     }
         */
        CurrentThresholdOut: {
            /**
             * On
             * Format: date
             */
            on: string;
            threshold: components["schemas"]["ThresholdOut"];
            zones: components["schemas"]["ZonesOut"];
        };
        /**
         * EnrichmentStatus
         * @description Datos de la carrera completados automáticamente (p. ej. con n8n) y revisión del usuario.
         * @enum {string}
         */
        EnrichmentStatus: "none" | "pending_review" | "confirmed";
        /** ErrorDetail */
        ErrorDetail: {
            /** Code */
            code: string;
            /** Details */
            details?: unknown | null;
            /** Message */
            message: string;
        };
        /**
         * ErrorResponse
         * @description Formato de todas las respuestas de error de la API.
         * @example {
         *       "error": {
         *         "code": "unauthorized",
         *         "message": "Autenticación requerida."
         *       },
         *       "request_id": "6f1c2a8e3b9d4f7a"
         *     }
         */
        ErrorResponse: {
            error: components["schemas"]["ErrorDetail"];
            /** Request Id */
            request_id: string | null;
        };
        /**
         * EventKind
         * @enum {string}
         */
        EventKind: "race" | "social" | "travel" | "health" | "personal" | "unavailable";
        /**
         * ExerciseLastLogOut
         * @description Última sesión **completada** en la que se registró el ejercicio, con sus series.
         *
         *     Si nunca se ha registrado, `performed_on`, `activity_id` y `planned_workout_id` son null
         *     y `sets` está vacía.
         * @example {
         *       "activity_id": "7a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
         *       "exercise": {
         *         "aliases": [
         *           "Sentadilla con barra",
         *           "Back squat"
         *         ],
         *         "id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
         *         "mode": "reps",
         *         "muscle_group": "quadriceps",
         *         "name": "Sentadilla trasera",
         *         "origin": "system",
         *         "slug": "back_squat"
         *       },
         *       "performed_on": "2026-11-12",
         *       "planned_workout_id": "4c2b1a09-8f7e-4d6c-9b5a-3e2d1c0b9a8f",
         *       "sets": [
         *         {
         *           "completed": true,
         *           "reps": 8,
         *           "rir": 2,
         *           "set_number": 1,
         *           "weight_kg": 60
         *         }
         *       ]
         *     }
         */
        ExerciseLastLogOut: {
            /** Activity Id */
            activity_id: string | null;
            exercise: components["schemas"]["ExerciseOut"];
            /**
             * Performed On
             * @description Día local de la sesión.
             */
            performed_on: string | null;
            /** Planned Workout Id */
            planned_workout_id: string | null;
            /**
             * Sets
             * @description Series de ese ejercicio, por `set_number`.
             */
            sets: components["schemas"]["LastSetOut"][];
        };
        /**
         * ExerciseMode
         * @description Cómo se mide cada serie: repeticiones o segundos (isométricos, cargadas…).
         * @enum {string}
         */
        ExerciseMode: "reps" | "seconds";
        /**
         * ExerciseOrigin
         * @enum {string}
         */
        ExerciseOrigin: "system" | "coach" | "user";
        /**
         * ExerciseOut
         * @description Ejercicio del catálogo. `id` es el identificador estable; `slug`, su forma legible.
         * @example {
         *       "aliases": [
         *         "Sentadilla con barra",
         *         "Back squat"
         *       ],
         *       "id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
         *       "mode": "reps",
         *       "muscle_group": "quadriceps",
         *       "name": "Sentadilla trasera",
         *       "origin": "system",
         *       "slug": "back_squat"
         *     }
         */
        ExerciseOut: {
            /** Aliases */
            aliases: string[];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** @description `reps`: cada serie se mide en repeticiones; `seconds`, en segundos. */
            mode: components["schemas"]["ExerciseMode"];
            muscle_group: components["schemas"]["MuscleGroup"];
            /** Name */
            name: string;
            /** @description `system` (catálogo común), `coach` o `user` (propios de la atleta). */
            origin: components["schemas"]["ExerciseOrigin"];
            /** Slug */
            slug: string;
        };
        /**
         * ExerciseProgressOut
         * @description Historial de un ejercicio: una entrada por sesión completada, de la más antigua a la
         *     más reciente. Vacío si nunca se ha hecho.
         * @example {
         *       "exercise": {
         *         "aliases": [
         *           "Sentadilla con barra",
         *           "Back squat"
         *         ],
         *         "id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
         *         "mode": "reps",
         *         "muscle_group": "quadriceps",
         *         "name": "Sentadilla trasera",
         *         "origin": "system",
         *         "slug": "back_squat"
         *       },
         *       "sessions": [
         *         {
         *           "activity_id": "1f0e2d3c-4b5a-4968-8776-655443322110",
         *           "best_set_reps": 8,
         *           "max_weight_kg": 57.5,
         *           "performed_on": "2026-10-29",
         *           "planned_workout_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
         *           "sets": 3,
         *           "total_reps": 24,
         *           "volume_kg": 1360
         *         },
         *         {
         *           "activity_id": "2e1d3c4b-5a69-4877-8665-544332211009",
         *           "best_set_reps": 8,
         *           "max_weight_kg": 60,
         *           "performed_on": "2026-11-05",
         *           "planned_workout_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
         *           "sets": 3,
         *           "total_reps": 24,
         *           "volume_kg": 1420
         *         },
         *         {
         *           "activity_id": "3d2c4b5a-6978-4866-9554-433221100998",
         *           "best_set_reps": 8,
         *           "max_weight_kg": 62.5,
         *           "performed_on": "2026-11-17",
         *           "sets": 3,
         *           "total_reps": 24,
         *           "volume_kg": 1480
         *         }
         *       ]
         *     }
         */
        ExerciseProgressOut: {
            exercise: components["schemas"]["ExerciseOut"];
            /** Sessions */
            sessions: components["schemas"]["ExerciseSessionOut"][];
        };
        /**
         * ExerciseSessionOut
         * @description Lo hecho con un ejercicio en una sesión completada. Sólo cuentan las series hechas.
         *
         *     - `max_weight_kg`: peso máximo de sus series (null si ninguna tiene peso).
         *     - `volume_kg`: suma de repeticiones × peso de cada serie (con series iguales, series ×
         *       repeticiones × peso). Null si ninguna serie tiene peso y repeticiones.
         *     - `best_set_reps`: repeticiones de la mejor serie, la de más peso (a igual peso, la de más
         *       repeticiones; sin peso, la de más repeticiones). Null en ejercicios por segundos.
         *     - `best_set_seconds`: igual, en los ejercicios por segundos.
         */
        ExerciseSessionOut: {
            /**
             * Activity Id
             * Format: uuid
             */
            activity_id: string;
            /** Best Set Reps */
            best_set_reps: number | null;
            /** Best Set Seconds */
            best_set_seconds: number | null;
            /** Max Weight Kg */
            max_weight_kg: number | null;
            /**
             * Performed On
             * Format: date
             * @description Día local de la sesión.
             */
            performed_on: string;
            /** Planned Workout Id */
            planned_workout_id: string | null;
            /**
             * Sets
             * @description Series hechas.
             */
            sets: number;
            /**
             * Total Reps
             * @description Repeticiones de todas las series.
             */
            total_reps: number | null;
            /**
             * Total Seconds
             * @description Segundos de todas las series.
             */
            total_seconds: number | null;
            /** Volume Kg */
            volume_kg: number | null;
        };
        /**
         * FitnessDayOut
         * @description Un día de la serie. Valores redondeados a 1 decimal.
         *
         *     - `load`: carga total del día (suma del TSS/hrTSS/rTSS de sus actividades, sin duplicados).
         *     - `ctl`: forma física (media exponencial de 42 días) al final del día.
         *     - `atl`: fatiga (media exponencial de 7 días) al final del día.
         *     - `tsb`: frescura con la que se empieza el día: CTL − ATL **del día anterior**
         *       (criterio de TrainingPeaks).
         */
        FitnessDayOut: {
            /** Atl */
            atl: number;
            /** Ctl */
            ctl: number;
            /**
             * Day
             * Format: date
             */
            day: string;
            /** Load */
            load: number;
            /** Tsb */
            tsb: number;
        };
        /**
         * FitnessSeriesOut
         * @description Serie diaria continua (un elemento por día del rango, ordenada por fecha).
         *
         *     Antes de la primera actividad todo vale 0. Los días sin actividad tienen `load` 0, y los
         *     días posteriores al último recálculo continúan la serie como descanso.
         * @example {
         *       "days": [
         *         {
         *           "atl": 62.9,
         *           "ctl": 55.6,
         *           "day": "2026-11-10",
         *           "load": 80,
         *           "tsb": -5
         *         },
         *         {
         *           "atl": 53.9,
         *           "ctl": 54.3,
         *           "day": "2026-11-11",
         *           "load": 0,
         *           "tsb": -7.3
         *         },
         *         {
         *           "atl": 63.3,
         *           "ctl": 55.8,
         *           "day": "2026-11-12",
         *           "load": 120,
         *           "tsb": 0.4
         *         }
         *       ],
         *       "from": "2026-11-10",
         *       "to": "2026-11-12"
         *     }
         */
        FitnessSeriesOut: {
            /** Days */
            days: components["schemas"]["FitnessDayOut"][];
            /**
             * From
             * Format: date
             */
            from: string;
            /**
             * To
             * Format: date
             */
            to: string;
        };
        /** HealthResponse */
        HealthResponse: {
            /**
             * Status
             * @constant
             */
            status: "ok";
            /** Version */
            version: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * IntakeOut
         * @description Toma de contacto: `not_started`, `in_progress` (la última sin terminar, también si se
         *     repite) o `completed`. `completed_at`: la última vez que se terminó.
         */
        IntakeOut: {
            /** Completed At */
            completed_at: string | null;
            /**
             * Conversation Id
             * @description La última toma de contacto.
             */
            conversation_id: string | null;
            /**
             * State
             * @enum {string}
             */
            state: "not_started" | "in_progress" | "completed";
        };
        /**
         * IntegrationOut
         * @description Estado de una integración. Nunca incluye tokens.
         */
        IntegrationOut: {
            /**
             * Connected At
             * Format: date-time
             */
            connected_at: string;
            /** Last Error */
            last_error: string | null;
            /** Last Sync At */
            last_sync_at: string | null;
            provider: components["schemas"]["Provider"];
            /** Scopes */
            scopes: string[];
            status: components["schemas"]["IntegrationStatus"];
            /** Token Expires At */
            token_expires_at: string | null;
        };
        /**
         * IntegrationStatus
         * @enum {string}
         */
        IntegrationStatus: "active" | "revoked" | "error";
        /**
         * InternalSyncOut
         * @description Resultado agregado de sincronizar todas las integraciones activas.
         */
        InternalSyncOut: {
            /** Created */
            created: number;
            /** Failed */
            failed: number;
            /** Integrations */
            integrations: number;
            /** Rate Limited */
            rate_limited: boolean;
            /** Succeeded */
            succeeded: number;
            /** Unchanged */
            unchanged: number;
            /** Updated */
            updated: number;
        };
        /** LastSetOut */
        LastSetOut: {
            /** Completed */
            completed: boolean;
            /** Reps */
            reps: number | null;
            /** Rir */
            rir: number | null;
            /** Rpe */
            rpe: number | null;
            /** Seconds */
            seconds: number | null;
            /** Set Number */
            set_number: number;
            /** Weight Kg */
            weight_kg: number | null;
        };
        /**
         * LoadMethod
         * @description Cómo se calculó la carga.
         *
         *     `power`, `heart_rate`, `pace` y `rpe` son TSS (o una estimación de TSS) de resistencia y
         *     suman en CTL/ATL. `session_rpe` es la carga de fuerza (minutos × RPE de la sesión, Foster):
         *     no es TSS y no suma nunca en `daily_load`.
         * @enum {string}
         */
        LoadMethod: "power" | "heart_rate" | "pace" | "rpe" | "session_rpe";
        /**
         * MemoryConfirm
         * @description Confirma una propuesta, opcionalmente corregida.
         */
        MemoryConfirm: {
            /** Content */
            content?: string | null;
            kind?: components["schemas"]["MemoryKind"] | null;
        };
        /** MemoryCreate */
        MemoryCreate: {
            /** Content */
            content: string;
            kind: components["schemas"]["MemoryKind"];
        };
        /**
         * MemoryKind
         * @enum {string}
         */
        MemoryKind: "goal" | "preference" | "other";
        /**
         * MemoryOut
         * @description Elemento de memoria. `source`: `coach` (propuesto por el coach) o `athlete` (añadido por
         *     ella). `status`: `proposed` (pendiente de confirmar), `confirmed`, `rejected` o
         *     `superseded` (el coach lo sustituyó por otra propuesta). El origen es la conversación y
         *     el mensaje del coach que lo propuso; `confirmed_at`, cuándo lo confirmó la atleta.
         */
        MemoryOut: {
            /** Confirmed At */
            confirmed_at: string | null;
            /** Content */
            content: string;
            /** Conversation Id */
            conversation_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            kind: components["schemas"]["MemoryKind"];
            source: components["schemas"]["MemorySource"];
            /** Source Message Id */
            source_message_id: string | null;
            status: components["schemas"]["MemoryStatus"];
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * MemoryPatch
         * @description Corrige un elemento confirmado (sólo los campos enviados).
         */
        MemoryPatch: {
            /** Content */
            content?: string | null;
            kind?: components["schemas"]["MemoryKind"] | null;
        };
        /**
         * MemorySource
         * @enum {string}
         */
        MemorySource: "coach" | "athlete";
        /**
         * MemoryStatus
         * @enum {string}
         */
        MemoryStatus: "proposed" | "confirmed" | "rejected" | "superseded";
        /** MeResponse */
        MeResponse: {
            /** Email */
            email: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
        };
        /**
         * MessageCreate
         * @example {
         *       "content": "¿Qué hago hoy? Tengo una hora."
         *     }
         */
        MessageCreate: {
            /** Content */
            content: string;
        };
        /**
         * MessageOrigin
         * @description De dónde sale un mensaje que no escribe la atleta.
         * @enum {string}
         */
        MessageOrigin: "llm" | "safety_filter" | "budget_limit" | "tool";
        /**
         * MessageOut
         * @description Mensaje de la atleta (`user`) o del coach (`assistant`).
         *
         *     `origin` (sólo en `assistant`): `llm`, `safety_filter` (respuesta fija del filtro de
         *     seguridad, sin LLM) o `budget_limit` (respuesta fija por presupuesto agotado).
         */
        MessageOut: {
            /** Content */
            content: string;
            /** Cost Eur */
            cost_eur: number | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Model */
            model: string | null;
            origin: components["schemas"]["MessageOrigin"] | null;
            role: components["schemas"]["MessageRole"];
            /** Seq */
            seq: number;
            /** Tokens In */
            tokens_in: number | null;
            /** Tokens Out */
            tokens_out: number | null;
        };
        /**
         * MessageRole
         * @enum {string}
         */
        MessageRole: "user" | "assistant" | "tool" | "system";
        /** ModelUsageOut */
        ModelUsageOut: {
            /** Calls */
            calls: number;
            /** Cost Eur */
            cost_eur: number;
            /** Model */
            model: string;
        };
        /**
         * MuscleGroup
         * @description Grupo muscular principal del ejercicio.
         * @enum {string}
         */
        MuscleGroup: "quadriceps" | "hamstrings" | "glutes" | "hips" | "calves" | "core" | "chest" | "back" | "shoulders" | "arms" | "full_body";
        /**
         * NextThresholdOut
         * @description Siguiente registro de umbrales después de `test_date`. No se toca al aceptar.
         */
        NextThresholdOut: {
            /**
             * Effective From
             * Format: date
             */
            effective_from: string;
            /**
             * Ftp W
             * @description FTP que seguirá vigente desde `effective_from`.
             */
            ftp_w: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
        };
        /**
         * PerformedExerciseOut
         * @description Un ejercicio con series hechas en sesiones completadas.
         *
         *     `last_max_weight_kg` es el peso máximo de la última sesión (null si no se usó peso).
         * @example {
         *       "exercise": {
         *         "aliases": [
         *           "Sentadilla con barra",
         *           "Back squat"
         *         ],
         *         "id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
         *         "mode": "reps",
         *         "muscle_group": "quadriceps",
         *         "name": "Sentadilla trasera",
         *         "origin": "system",
         *         "slug": "back_squat"
         *       },
         *       "first_performed_on": "2026-10-29",
         *       "last_max_weight_kg": 62.5,
         *       "last_performed_on": "2026-11-17",
         *       "sessions": 3
         *     }
         */
        PerformedExerciseOut: {
            exercise: components["schemas"]["ExerciseOut"];
            /**
             * First Performed On
             * Format: date
             */
            first_performed_on: string;
            /** Last Max Weight Kg */
            last_max_weight_kg: number | null;
            /**
             * Last Performed On
             * Format: date
             */
            last_performed_on: string;
            /**
             * Sessions
             * @description Sesiones completadas con el ejercicio.
             */
            sessions: number;
        };
        /** PingResponse */
        PingResponse: {
            /**
             * Status
             * @constant
             */
            status: "ok";
        };
        /**
         * PlannedStrengthExerciseOut
         * @description Ejercicio de la sesión. Exactamente uno de `target_reps` y `target_seconds`, según el
         *     `mode` del ejercicio. Peso, RPE y RIR objetivo son opcionales.
         */
        PlannedStrengthExerciseOut: {
            exercise: components["schemas"]["ExerciseOut"];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Notes */
            notes: string | null;
            /**
             * Position
             * @description Orden en la sesión (desde 1).
             */
            position: number;
            /** Sets */
            sets: number;
            /** Target Reps */
            target_reps: number | null;
            /** Target Rir */
            target_rir: number | null;
            /** Target Rpe */
            target_rpe: number | null;
            /** Target Seconds */
            target_seconds: number | null;
            /** Target Weight Kg */
            target_weight_kg: number | null;
        };
        /**
         * PlannedWorkoutOut
         * @description Entreno planificado de cualquier disciplina. La fuerza es el primer tipo.
         *
         *     - `planned`: pendiente.
         *     - `done`: hecho; `activity_id` es la actividad que lo cumplió (null si se borró).
         *     - `skipped`: no se hizo.
         *
         *     `exercise_count`, `planned_duration_s` y `actual_duration_s` resumen la sesión sin pedir su
         *     detalle. La duración real es la de la actividad que lo cumplió.
         * @example {
         *       "coach_reason": "Semana de base: fuerza máxima con poco volumen para no afectar al rodaje.",
         *       "created_at": "2026-11-18T10:00:00Z",
         *       "exercise_count": 1,
         *       "id": "4c2b1a09-8f7e-4d6c-9b5a-3e2d1c0b9a8f",
         *       "planned_duration_s": 3000,
         *       "scheduled_on": "2026-11-19",
         *       "sport": "strength",
         *       "status": "planned",
         *       "title": "Fuerza de piernas",
         *       "updated_at": "2026-11-18T10:00:00Z"
         *     }
         */
        PlannedWorkoutOut: {
            /** Activity Id */
            activity_id: string | null;
            /**
             * Actual Duration S
             * @description Duración real en segundos, de su actividad. Null si no está hecho o la actividad no la tiene.
             */
            actual_duration_s: number | null;
            /**
             * Coach Reason
             * @description Por qué lo propone el coach.
             */
            coach_reason: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Exercise Count
             * @description Número de ejercicios planificados (0 si no es de fuerza).
             */
            exercise_count: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Planned Duration S
             * @description Duración planificada en segundos. Null si no se ha definido (no se estima).
             */
            planned_duration_s: number | null;
            /**
             * Scheduled On
             * Format: date
             * @description Día local para el que está planificado.
             */
            scheduled_on: string;
            sport: components["schemas"]["Sport"];
            status: components["schemas"]["PlannedWorkoutStatus"];
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * PlannedWorkoutStatus
         * @enum {string}
         */
        PlannedWorkoutStatus: "planned" | "done" | "skipped";
        /**
         * PreferredTime
         * @enum {string}
         */
        PreferredTime: "morning" | "midday" | "afternoon" | "evening" | "any";
        /**
         * PreviewWarningCode
         * @enum {string}
         */
        PreviewWarningCode: "later_thresholds";
        /** PreviewWarningOut */
        PreviewWarningOut: {
            /** @description `later_thresholds`: hay umbrales registrados después de `test_date`; el FTP nuevo sólo rige hasta `effective_until`. */
            code: components["schemas"]["PreviewWarningCode"];
            /** Message */
            message: string;
        };
        /**
         * ProfileOut
         * @description Perfil del atleta autenticado. Se crea automáticamente la primera vez que se pide.
         * @example {
         *       "birth_date": "1990-05-14",
         *       "created_at": "2026-11-01T09:00:00Z",
         *       "display_name": "Leti",
         *       "height_cm": 168,
         *       "preferences": {
         *         "language": "es",
         *         "units": "metric"
         *       },
         *       "sex": "female",
         *       "sports": [
         *         "cycling",
         *         "trail_running"
         *       ],
         *       "timezone": "Europe/Madrid",
         *       "updated_at": "2026-11-15T18:30:00Z",
         *       "user_id": "11111111-2222-3333-4444-555555555555"
         *     }
         */
        ProfileOut: {
            /** Birth Date */
            birth_date: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Display Name */
            display_name: string | null;
            /** Height Cm */
            height_cm: number | null;
            /** Preferences */
            preferences: {
                [key: string]: unknown;
            };
            sex: components["schemas"]["Sex"] | null;
            /** Sports */
            sports: components["schemas"]["Sport"][];
            /** Timezone */
            timezone: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
        };
        /**
         * ProfilePatch
         * @description Actualización parcial: sólo se cambian los campos enviados.
         *
         *     `null` borra el valor en los campos opcionales; `timezone`, `sports` y `preferences` no
         *     admiten `null`. `preferences` se sustituye entero (no se fusiona).
         * @example {
         *       "display_name": "Leti",
         *       "height_cm": 168,
         *       "sports": [
         *         "cycling",
         *         "trail_running"
         *       ]
         *     }
         * @example {
         *       "timezone": "Atlantic/Canary"
         *     }
         */
        ProfilePatch: {
            /** Birth Date */
            birth_date?: string | null;
            /** Display Name */
            display_name?: string | null;
            /** Height Cm */
            height_cm?: number | null;
            /** Preferences */
            preferences?: {
                [key: string]: unknown;
            } | null;
            sex?: components["schemas"]["Sex"] | null;
            /** Sports */
            sports?: components["schemas"]["Sport"][] | null;
            /** Timezone */
            timezone?: string | null;
        };
        /**
         * ProposalMetricsOut
         * @description Métricas del bloque detectado. Offsets en segundos desde el primer registro del FIT.
         *
         *     La FC (`avg_hr_bpm`, `max_hr_bpm`) es sólo informativa: con este test no se propone FC
         *     umbral. `variability_index` = potencia normalizada / potencia media del bloque.
         */
        ProposalMetricsOut: {
            /** Avg Hr Bpm */
            avg_hr_bpm: number | null;
            /** Avg Power W */
            avg_power_w: number;
            /** Duration S */
            duration_s: number;
            /** End Offset S */
            end_offset_s: number;
            /** Max Hr Bpm */
            max_hr_bpm: number | null;
            /** Normalized Power W */
            normalized_power_w: number;
            /** Start Offset S */
            start_offset_s: number;
            /**
             * Valid Data Pct
             * @description Porcentaje del bloque con dato de potencia.
             */
            valid_data_pct: number;
            /** Variability Index */
            variability_index: number;
            /**
             * Warmup S
             * @description Segundos registrados antes del bloque.
             */
            warmup_s: number;
        };
        /**
         * ProposalStatus
         * @enum {string}
         */
        ProposalStatus: "pending" | "accepted" | "rejected";
        /**
         * Provider
         * @enum {string}
         */
        Provider: "wahoo" | "strava" | "suunto" | "garmin";
        /**
         * QualityCheckOut
         * @description Evaluación de un criterio de calidad del test.
         *
         *     El criterio se cumple (`passed`) si `measured <comparison> threshold`. Si no se cumple y
         *     es `blocking`, no se puede proponer el umbral (error 422 con este mismo objeto en
         *     `error.details`); si no es `blocking`, sólo avisa.
         */
        QualityCheckOut: {
            /**
             * Blocking
             * @description Si no se cumple, impide la propuesta (si no, avisa).
             */
            blocking: boolean;
            /** @description Bloquean: `test_too_short` (duración de la actividad), `no_power_data` (potencia media del bloque), `insufficient_data` (% de datos válidos del bloque). Avisan: `data_gaps` (hueco sin potencia más largo del bloque), `pauses` (tramo a 0 W más largo del bloque), `high_variability` (NP / potencia media), `no_warmup` (segundos antes del bloque). */
            code: components["schemas"]["QualityCriterion"];
            /** @description Condición para cumplirlo: `measured` gt/ge/lt/le `threshold`. */
            comparison: components["schemas"]["Comparison"];
            /**
             * Measured
             * @description Valor medido.
             */
            measured: number;
            /**
             * Message
             * @description Explicación legible.
             */
            message: string;
            /** Passed */
            passed: boolean;
            /**
             * Threshold
             * @description Umbral del criterio.
             */
            threshold: number;
            /**
             * Unit
             * @description `s`, `W`, `%` o vacío (adimensional).
             */
            unit: string;
        };
        /**
         * QualityCriterion
         * @description Criterios de calidad del test. Los tres primeros bloquean la propuesta.
         * @enum {string}
         */
        QualityCriterion: "test_too_short" | "no_power_data" | "insufficient_data" | "data_gaps" | "pauses" | "high_variability" | "no_warmup";
        /**
         * RaceCreate
         * @description Datos de la carrera. Todos opcionales: se pueden completar más tarde.
         * @example {
         *       "ascent_m": 2400,
         *       "discipline": "trail_running",
         *       "distance_m": 42000,
         *       "goal": "Terminar por debajo de 6 h.",
         *       "priority": "A",
         *       "source_url": "https://example.com/carrera"
         *     }
         */
        RaceCreate: {
            /** Ascent M */
            ascent_m?: number | null;
            discipline?: components["schemas"]["RaceDiscipline"] | null;
            /** Distance M */
            distance_m?: number | null;
            /** Goal */
            goal?: string | null;
            /** @default B */
            priority: components["schemas"]["RacePriority"];
            /** Source Url */
            source_url?: string | null;
        };
        /**
         * RaceDiscipline
         * @enum {string}
         */
        RaceDiscipline: "road_cycling" | "gravel" | "mtb" | "trail_running" | "road_running" | "other";
        /** RaceOut */
        RaceOut: {
            /** Ascent M */
            ascent_m: number | null;
            discipline: components["schemas"]["RaceDiscipline"] | null;
            /** Distance M */
            distance_m: number | null;
            enrichment_status: components["schemas"]["EnrichmentStatus"];
            /** Goal */
            goal: string | null;
            priority: components["schemas"]["RacePriority"];
            /** Source Url */
            source_url: string | null;
        };
        /**
         * RacePatch
         * @description Actualización parcial de la carrera. `null` borra el valor (salvo `priority` y
         *     `enrichment_status`, que no lo admiten).
         *
         *     `enrichment_status` permite al atleta confirmar (`confirmed`) los datos completados
         *     automáticamente (`pending_review`).
         * @example {
         *       "enrichment_status": "confirmed",
         *       "priority": "B"
         *     }
         */
        RacePatch: {
            /** Ascent M */
            ascent_m?: number | null;
            discipline?: components["schemas"]["RaceDiscipline"] | null;
            /** Distance M */
            distance_m?: number | null;
            enrichment_status?: components["schemas"]["EnrichmentStatus"] | null;
            /** Goal */
            goal?: string | null;
            priority?: components["schemas"]["RacePriority"] | null;
            /** Source Url */
            source_url?: string | null;
        };
        /**
         * RacePriority
         * @enum {string}
         */
        RacePriority: "A" | "B" | "C";
        /** ReadinessResponse */
        ReadinessResponse: {
            /** Checks */
            checks: {
                [key: string]: "ok" | "error" | "not_configured";
            };
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "degraded";
        };
        /** ReceivedResponse */
        ReceivedResponse: {
            /** Received */
            received: boolean;
        };
        /** RootResponse */
        RootResponse: {
            /** Health */
            health: string;
            /** Name */
            name: string;
            /** Version */
            version: string;
        };
        /**
         * Sex
         * @enum {string}
         */
        Sex: "female" | "male" | "other";
        /**
         * Sport
         * @enum {string}
         */
        Sport: "cycling" | "running" | "trail_running" | "hiking" | "strength" | "swimming" | "other";
        /** StravaEvent */
        StravaEvent: {
            /**
             * Aspect Type
             * @enum {string}
             */
            aspect_type: "create" | "update" | "delete";
            /** Event Time */
            event_time: number;
            /** Object Id */
            object_id: number;
            /**
             * Object Type
             * @enum {string}
             */
            object_type: "activity" | "athlete";
            /** Owner Id */
            owner_id: number;
            /** Subscription Id */
            subscription_id: number;
            /** Updates */
            updates?: {
                [key: string]: unknown;
            };
        };
        /**
         * StrengthActivityOut
         * @description Actividad creada al completar la sesión, con su carga `session_rpe` (minutos × RPE).
         *
         *     Esa carga es de fuerza: no es TSS y no suma nunca en CTL/ATL/TSB. Si la sesión se completó
         *     sin RPE, `rpe`, `load` y `load_method` son null: no hay carga.
         */
        StrengthActivityOut: {
            /** Elapsed S */
            elapsed_s: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Load */
            load: number | null;
            load_method: components["schemas"]["LoadMethod"] | null;
            /** Rpe */
            rpe: number | null;
            /**
             * Start At
             * Format: date-time
             */
            start_at: string;
        };
        /**
         * StrengthSetIn
         * @description Una serie hecha.
         *
         *     - `planned_exercise_id`: el ejercicio planificado que cumple; null para una serie extra.
         *     - `exercise_id`: el ejercicio hecho. Si se omite, el del ejercicio planificado. Puede ser
         *       otro (p. ej. una sustitución).
         *     - Exactamente uno de `reps` y `seconds`, según el `mode` del ejercicio.
         *     - `set_number` no se repite para el mismo ejercicio planificado (o el mismo ejercicio extra).
         */
        StrengthSetIn: {
            /**
             * Completed
             * @default true
             */
            completed: boolean;
            /** Exercise Id */
            exercise_id?: string | null;
            /** Planned Exercise Id */
            planned_exercise_id?: string | null;
            /** Reps */
            reps?: number | null;
            /** Rir */
            rir?: number | null;
            /** Rpe */
            rpe?: number | null;
            /** Seconds */
            seconds?: number | null;
            /** Set Number */
            set_number: number;
            /** Weight Kg */
            weight_kg?: number | null;
        };
        /**
         * StrengthSetLogOut
         * @description Serie hecha. `planned_exercise_id` es el ejercicio planificado que cumple (null si es
         *     una serie extra). `activity_id` es null hasta que se completa la sesión.
         */
        StrengthSetLogOut: {
            /** Activity Id */
            activity_id: string | null;
            /** Completed */
            completed: boolean;
            /**
             * Exercise Id
             * Format: uuid
             */
            exercise_id: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Planned Exercise Id */
            planned_exercise_id: string | null;
            /** Reps */
            reps: number | null;
            /** Rir */
            rir: number | null;
            /** Rpe */
            rpe: number | null;
            /** Seconds */
            seconds: number | null;
            /** Set Number */
            set_number: number;
            /** Weight Kg */
            weight_kg: number | null;
        };
        /**
         * StrengthSetsPut
         * @description Todas las series de la sesión: sustituyen a las registradas antes.
         *
         *     Sirve para registrar durante el entreno (se envía la lista acumulada) y para editar después
         *     de completarlo. Una lista vacía borra las series.
         * @example {
         *       "sets": [
         *         {
         *           "planned_exercise_id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
         *           "reps": 8,
         *           "rir": 2,
         *           "set_number": 1,
         *           "weight_kg": 60
         *         },
         *         {
         *           "completed": false,
         *           "planned_exercise_id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
         *           "reps": 6,
         *           "set_number": 2,
         *           "weight_kg": 60
         *         }
         *       ]
         *     }
         */
        StrengthSetsPut: {
            /** Sets */
            sets: components["schemas"]["StrengthSetIn"][];
        };
        /**
         * StrengthWeeklyOut
         * @description Una semana por cada lunes desde la semana de `from` hasta la de `to`, por fecha.
         *
         *     Las semanas sin fuerza aparecen con todo a 0. La última semana es la que contiene `to`
         *     (con `to` = hoy, la semana en curso).
         * @example {
         *       "from": "2026-10-26",
         *       "to": "2026-11-19",
         *       "weeks": [
         *         {
         *           "duration_s": 2700,
         *           "load": 270,
         *           "sessions": 1,
         *           "sessions_without_load": 0,
         *           "week_start": "2026-10-26"
         *         },
         *         {
         *           "duration_s": 5400,
         *           "load": 495,
         *           "sessions": 2,
         *           "sessions_without_load": 0,
         *           "week_start": "2026-11-02"
         *         },
         *         {
         *           "duration_s": 0,
         *           "load": 0,
         *           "sessions": 0,
         *           "sessions_without_load": 0,
         *           "week_start": "2026-11-09"
         *         },
         *         {
         *           "duration_s": 5100,
         *           "load": 330,
         *           "sessions": 2,
         *           "sessions_without_load": 1,
         *           "week_start": "2026-11-16"
         *         }
         *       ]
         *     }
         */
        StrengthWeeklyOut: {
            /**
             * From
             * Format: date
             */
            from: string;
            /**
             * To
             * Format: date
             */
            to: string;
            /** Weeks */
            weeks: components["schemas"]["StrengthWeekOut"][];
        };
        /**
         * StrengthWeekOut
         * @description Una semana (de lunes a domingo, días locales del atleta).
         *
         *     - `sessions`: actividades de fuerza de la semana (sin duplicados).
         *     - `duration_s`: suma de su duración.
         *     - `load`: suma de su carga `session_rpe` (minutos × RPE, Foster), redondeada a 1 decimal.
         *       Es la carga de fuerza: **no** es TSS y no suma en CTL/ATL/TSB.
         *     - `sessions_without_load`: sesiones sin RPE, que cuentan en `sessions` y `duration_s`
         *       pero no en `load`.
         */
        StrengthWeekOut: {
            /** Duration S */
            duration_s: number;
            /** Load */
            load: number;
            /** Sessions */
            sessions: number;
            /** Sessions Without Load */
            sessions_without_load: number;
            /**
             * Week Start
             * Format: date
             * @description Lunes de la semana.
             */
            week_start: string;
        };
        /**
         * StrengthWorkoutComplete
         * @description Completa la sesión: crea la actividad de fuerza (`source = manual`) con su carga
         *     `session_rpe` = minutos × `rpe`.
         *
         *     `rpe` es opcional: sin él, la sesión queda hecha con todas sus series, pero la actividad no
         *     tiene RPE ni carga (no se usa un RPE por defecto ni una carga 0).
         * @example {
         *       "duration_s": 3000,
         *       "rpe": 7,
         *       "started_at": "2026-11-19T18:30:00+01:00"
         *     }
         */
        StrengthWorkoutComplete: {
            /**
             * Duration S
             * @description Duración en segundos.
             */
            duration_s: number;
            /**
             * Rpe
             * @description RPE de la sesión (1-10). Null u omitido: sin carga.
             */
            rpe?: number | null;
            /**
             * Started At
             * Format: date-time
             * @description Inicio de la sesión, con zona horaria.
             */
            started_at: string;
        };
        /**
         * StrengthWorkoutOut
         * @description Detalle de una sesión de fuerza: ejercicios planificados, series hechas y actividad.
         * @example {
         *       "coach_reason": "Semana de base: fuerza máxima con poco volumen para no afectar al rodaje.",
         *       "created_at": "2026-11-18T10:00:00Z",
         *       "exercise_count": 1,
         *       "exercises": [
         *         {
         *           "exercise": {
         *             "aliases": [
         *               "Sentadilla con barra",
         *               "Back squat"
         *             ],
         *             "id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
         *             "mode": "reps",
         *             "muscle_group": "quadriceps",
         *             "name": "Sentadilla trasera",
         *             "origin": "system",
         *             "slug": "back_squat"
         *           },
         *           "id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
         *           "position": 1,
         *           "sets": 3,
         *           "target_reps": 8,
         *           "target_rir": 2,
         *           "target_weight_kg": 60
         *         }
         *       ],
         *       "id": "4c2b1a09-8f7e-4d6c-9b5a-3e2d1c0b9a8f",
         *       "planned_duration_s": 3000,
         *       "scheduled_on": "2026-11-19",
         *       "set_logs": [
         *         {
         *           "completed": true,
         *           "exercise_id": "0b7c3f9e-1d2a-4e5b-8c6d-7e8f9a0b1c2d",
         *           "id": "1f2e3d4c-5b6a-4978-8a7b-6c5d4e3f2a1b",
         *           "planned_exercise_id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
         *           "reps": 8,
         *           "rir": 2,
         *           "set_number": 1,
         *           "weight_kg": 60
         *         }
         *       ],
         *       "sport": "strength",
         *       "status": "planned",
         *       "title": "Fuerza de piernas",
         *       "updated_at": "2026-11-18T10:00:00Z"
         *     }
         */
        StrengthWorkoutOut: {
            /** @description Null hasta completar la sesión. */
            activity: components["schemas"]["StrengthActivityOut"] | null;
            /** Activity Id */
            activity_id: string | null;
            /**
             * Actual Duration S
             * @description Duración real en segundos, de su actividad. Null si no está hecho o la actividad no la tiene.
             */
            actual_duration_s: number | null;
            /**
             * Coach Reason
             * @description Por qué lo propone el coach.
             */
            coach_reason: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Exercise Count
             * @description Número de ejercicios planificados (0 si no es de fuerza).
             */
            exercise_count: number;
            /**
             * Exercises
             * @description Por `position`.
             */
            exercises: components["schemas"]["PlannedStrengthExerciseOut"][];
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Planned Duration S
             * @description Duración planificada en segundos. Null si no se ha definido (no se estima).
             */
            planned_duration_s: number | null;
            /**
             * Scheduled On
             * Format: date
             * @description Día local para el que está planificado.
             */
            scheduled_on: string;
            /**
             * Set Logs
             * @description Series hechas, por ejercicio planificado (las extras al final) y número.
             */
            set_logs: components["schemas"]["StrengthSetLogOut"][];
            sport: components["schemas"]["Sport"];
            status: components["schemas"]["PlannedWorkoutStatus"];
            /** Title */
            title: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * SyncOut
         * @description Resultado de una sincronización: actividades creadas, actualizadas y sin cambios.
         */
        SyncOut: {
            /** Created */
            created: number;
            /** Unchanged */
            unchanged: number;
            /** Updated */
            updated: number;
        };
        /**
         * ThresholdCreate
         * @description Nuevo juego de umbrales vigente desde `effective_from` (una fila por fecha).
         *
         *     Es una foto completa: los valores que no se envían quedan vacíos para esa fecha. La app
         *     debería precargar el formulario con el umbral vigente. Debe incluir al menos un umbral.
         *
         *     El LTHR va por disciplina: `cycling_lthr_bpm` (carga por FC de ciclismo) y
         *     `running_lthr_bpm` (zonas y carga de trail). `legacy_lthr_bpm` es de sólo lectura.
         * @example {
         *       "cycling_lthr_bpm": 165,
         *       "effective_from": "2026-11-01",
         *       "ftp_w": 230,
         *       "hr_max_bpm": 186,
         *       "hr_rest_bpm": 48,
         *       "notes": "Test de 20 min en rodillo.",
         *       "running_lthr_bpm": 172,
         *       "source": "test",
         *       "threshold_pace_s_per_km": 285,
         *       "vo2max": 52,
         *       "weight_kg": 58.5
         *     }
         */
        ThresholdCreate: {
            /** Cycling Lthr Bpm */
            cycling_lthr_bpm?: number | null;
            /**
             * Effective From
             * Format: date
             */
            effective_from: string;
            /** Ftp W */
            ftp_w?: number | null;
            /** Hr Max Bpm */
            hr_max_bpm?: number | null;
            /** Hr Rest Bpm */
            hr_rest_bpm?: number | null;
            /** Notes */
            notes?: string | null;
            /** Running Lthr Bpm */
            running_lthr_bpm?: number | null;
            /** @default manual */
            source: components["schemas"]["ThresholdSource"];
            /** Threshold Pace S Per Km */
            threshold_pace_s_per_km?: number | null;
            /** Vo2Max */
            vo2max?: number | null;
            /** Weight Kg */
            weight_kg?: number | null;
        };
        /**
         * ThresholdOut
         * @example {
         *       "created_at": "2026-11-01T19:00:00Z",
         *       "cycling_lthr_bpm": 165,
         *       "effective_from": "2026-11-01",
         *       "ftp_w": 230,
         *       "hr_max_bpm": 186,
         *       "hr_rest_bpm": 48,
         *       "id": "8d5e2f0a-6b1c-4f3e-9a7d-2c4b6e8f0a1b",
         *       "notes": "Test de 20 min en rodillo.",
         *       "running_lthr_bpm": 172,
         *       "source": "test",
         *       "threshold_pace_s_per_km": 285,
         *       "updated_at": "2026-11-01T19:00:00Z",
         *       "vo2max": 52,
         *       "weight_kg": 58.5
         *     }
         */
        ThresholdOut: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Cycling Lthr Bpm */
            cycling_lthr_bpm: number | null;
            /**
             * Effective From
             * Format: date
             */
            effective_from: string;
            /**
             * Ftp Proposal Id
             * @description Propuesta de test de la que sale `ftp_w`, si se aceptó una. Puede ir con `source = manual` si el test sólo actualizó el FTP de una fila existente.
             */
            readonly ftp_proposal_id: string | null;
            /** Ftp W */
            ftp_w: number | null;
            /** Hr Max Bpm */
            hr_max_bpm: number | null;
            /** Hr Rest Bpm */
            hr_rest_bpm: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Legacy Lthr Bpm
             * @description LTHR único anterior a la separación por disciplina. Sólo lectura: ningún cálculo lo usa; está para decidir a qué disciplina pertenecía.
             */
            readonly legacy_lthr_bpm: number | null;
            /** Notes */
            notes: string | null;
            /** Running Lthr Bpm */
            running_lthr_bpm: number | null;
            source: components["schemas"]["ThresholdSource"];
            /** Threshold Pace S Per Km */
            threshold_pace_s_per_km: number | null;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Vo2Max */
            vo2max: number | null;
            /** Weight Kg */
            weight_kg: number | null;
        };
        /**
         * ThresholdProposalAccept
         * @description Confirma lo que mostró la vista previa. Si ya no coincide, 409 con la vista nueva.
         * @example {
         *       "action": "update_ftp",
         *       "previous_ftp_w": 220
         *     }
         */
        ThresholdProposalAccept: {
            action: components["schemas"]["AcceptAction"];
            /**
             * Previous Ftp W
             * @description `previous_ftp_w` de la vista previa (null si no había FTP).
             */
            previous_ftp_w: number | null;
        };
        /**
         * ThresholdProposalCreate
         * @description Analiza el test hecho en una actividad de ciclismo y crea una propuesta pendiente.
         * @example {
         *       "activity_id": "7a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
         *       "protocol": "ftp_20min"
         *     }
         */
        ThresholdProposalCreate: {
            /**
             * Activity Id
             * Format: uuid
             */
            activity_id: string;
            /** @default ftp_20min */
            protocol: components["schemas"]["ThresholdProtocol"];
        };
        /**
         * ThresholdProposalOut
         * @description Propuesta de umbral salida de un test. Es sólo una propuesta hasta que se acepta.
         *
         *     - `pending`: no cambia ningún umbral.
         *     - `accepted`: `threshold_id` es el umbral con el FTP del test. Si no había umbrales en
         *       `test_date`, una fila nueva con `source = test` y el resto de valores copiados del umbral
         *       vigente ese día; si ya había una fila en esa fecha, la misma fila con sólo `ftp_w`
         *       cambiado.
         *     - `rejected`: no se tocó nada.
         * @example {
         *       "activity_id": "7a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
         *       "created_at": "2026-11-15T10:00:00Z",
         *       "id": "3f6c1d2e-8a4b-4c7d-9e1f-2a3b4c5d6e7f",
         *       "interval_end_at": "2026-11-15T08:35:00Z",
         *       "interval_start_at": "2026-11-15T08:15:00Z",
         *       "metrics": {
         *         "avg_hr_bpm": 168.4,
         *         "avg_power_w": 242.3,
         *         "duration_s": 1200,
         *         "end_offset_s": 2100,
         *         "max_hr_bpm": 179,
         *         "normalized_power_w": 245.1,
         *         "start_offset_s": 900,
         *         "valid_data_pct": 100,
         *         "variability_index": 1.012,
         *         "warmup_s": 900
         *       },
         *       "proposed_ftp_w": 230,
         *       "protocol": "ftp_20min",
         *       "status": "pending",
         *       "test_date": "2026-11-15",
         *       "updated_at": "2026-11-15T10:00:00Z",
         *       "warnings": [
         *         {
         *           "blocking": false,
         *           "code": "no_warmup",
         *           "comparison": "ge",
         *           "measured": 300,
         *           "message": "El bloque empieza a los 5 min: no hay un calentamiento previo de al menos 10 min.",
         *           "passed": false,
         *           "threshold": 600,
         *           "unit": "s"
         *         }
         *       ]
         *     }
         */
        ThresholdProposalOut: {
            /** @description Historial: qué hizo la aceptación (null si no está aceptada). */
            accepted_action: components["schemas"]["AcceptAction"] | null;
            /**
             * Activity Id
             * Format: uuid
             */
            activity_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Decided At */
            decided_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Interval End At
             * Format: date-time
             */
            interval_end_at: string;
            /**
             * Interval Start At
             * Format: date-time
             */
            interval_start_at: string;
            metrics: components["schemas"]["ProposalMetricsOut"];
            /**
             * Previous Ftp W
             * @description Historial: FTP de `test_date` justo antes de aceptar (el de la fila con `update_ftp`, el vigente ese día con `create_row`). Null si no había o si la propuesta no está aceptada.
             */
            previous_ftp_w: number | null;
            /**
             * Proposed Ftp W
             * @description FTP propuesto: 95 % de la potencia media del bloque.
             */
            proposed_ftp_w: number;
            protocol: components["schemas"]["ThresholdProtocol"];
            status: components["schemas"]["ProposalStatus"];
            /**
             * Test Date
             * Format: date
             * @description Día local de la actividad: `effective_from` del umbral si se acepta.
             */
            test_date: string;
            /**
             * Threshold Id
             * @description Umbral creado o actualizado al aceptar la propuesta.
             */
            threshold_id: string | null;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Warnings
             * @description Criterios que no bloquean y no se cumplen (avisos).
             */
            warnings: components["schemas"]["QualityCheckOut"][];
        };
        /**
         * ThresholdProtocol
         * @enum {string}
         */
        ThresholdProtocol: "ftp_20min";
        /**
         * ThresholdSource
         * @enum {string}
         */
        ThresholdSource: "manual" | "test" | "estimated";
        /**
         * ThresholdTestAnalysisOut
         * @description Análisis de prueba (`dry-run`): lo que saldría del test, **sin crear ninguna propuesta**.
         *
         *     `checks` tiene todos los criterios de calidad evaluados; `warnings`, los que avisan y no se
         *     cumplen (los mismos que tendría la propuesta).
         */
        ThresholdTestAnalysisOut: {
            /**
             * Activity Id
             * Format: uuid
             */
            activity_id: string;
            /** Checks */
            checks: components["schemas"]["QualityCheckOut"][];
            /**
             * Interval End At
             * Format: date-time
             */
            interval_end_at: string;
            /**
             * Interval Start At
             * Format: date-time
             */
            interval_start_at: string;
            metrics: components["schemas"]["ProposalMetricsOut"];
            /** Proposed Ftp W */
            proposed_ftp_w: number;
            protocol: components["schemas"]["ThresholdProtocol"];
            /**
             * Test Date
             * Format: date
             * @description Día local de la actividad.
             */
            test_date: string;
            /** Warnings */
            warnings: components["schemas"]["QualityCheckOut"][];
        };
        /**
         * TrainingImpact
         * @description Cómo debe tratar el coach el evento al planificar.
         * @enum {string}
         */
        TrainingImpact: "none" | "reduce" | "no_training" | "move";
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /**
         * WeekAvailability
         * @description Los 7 días de la semana, ordenados de lunes (0) a domingo (6).
         *
         *     En `GET` siempre vienen los 7 (con valores por defecto si el atleta no los ha rellenado).
         *     En `PUT` hay que enviar los 7 y se sustituye la semana entera.
         * @example {
         *       "days": [
         *         {
         *           "is_preferred_rest": true,
         *           "max_minutes": 0,
         *           "preferred_time": "any",
         *           "sports": [],
         *           "weekday": 0
         *         },
         *         {
         *           "is_preferred_rest": false,
         *           "max_minutes": 60,
         *           "preferred_time": "morning",
         *           "sports": [
         *             "running"
         *           ],
         *           "weekday": 1
         *         },
         *         {
         *           "is_preferred_rest": false,
         *           "max_minutes": 90,
         *           "preferred_time": "evening",
         *           "sports": [
         *             "cycling"
         *           ],
         *           "weekday": 2
         *         },
         *         {
         *           "is_preferred_rest": false,
         *           "max_minutes": 60,
         *           "preferred_time": "morning",
         *           "sports": [
         *             "running",
         *             "strength"
         *           ],
         *           "weekday": 3
         *         },
         *         {
         *           "is_preferred_rest": false,
         *           "max_minutes": 45,
         *           "preferred_time": "evening",
         *           "sports": [
         *             "cycling"
         *           ],
         *           "weekday": 4
         *         },
         *         {
         *           "is_preferred_rest": false,
         *           "max_minutes": 240,
         *           "preferred_time": "morning",
         *           "sports": [
         *             "cycling"
         *           ],
         *           "weekday": 5
         *         },
         *         {
         *           "is_preferred_rest": false,
         *           "max_minutes": 180,
         *           "preferred_time": "morning",
         *           "sports": [
         *             "trail_running"
         *           ],
         *           "weekday": 6
         *         }
         *       ]
         *     }
         */
        WeekAvailability: {
            /** Days */
            days: components["schemas"]["AvailabilityDay"][];
        };
        /**
         * ZoneOut
         * @description Zona `[low, high)` tal como la calcula `app.metrics.zones.Zone`.
         *
         *     Unidades: vatios en las zonas de potencia, ppm en las de FC y s/km en las de ritmo.
         *     `high` null: sin límite. En las de ritmo un número mayor es más lento: `low` es el límite
         *     rápido (incluido) y `high` el lento (excluido), así que la Z1 no tiene `high`.
         */
        ZoneOut: {
            /**
             * Code
             * @description Código: Z1…Z7 (potencia), Z1…Z5c (FC de 7 zonas) o Z1…Z5 (5 zonas).
             */
            code: string;
            /** High */
            high: number | null;
            /** Low */
            low: number;
            /** Name */
            name: string;
            /**
             * Number
             * @description Posición de la zona (1 = la más suave).
             */
            number: number;
        };
        /**
         * ZonesOut
         * @description Zonas calculadas a partir del umbral vigente. Null si falta el umbral correspondiente.
         *
         *     Referencia de cada disciplina: `power` (ciclismo), `running_pace` (carrera) y `trail_hr`
         *     (trail).
         *
         *     - `power`: 7 zonas de Coggan sobre `ftp_w` (W).
         *     - `running_pace`: 5 zonas de ritmo de Friel sobre `threshold_pace_s_per_km` (s/km; la app
         *       lo muestra en min/km).
         *     - `trail_hr`: 5 zonas de FC de Friel sobre `running_lthr_bpm` (ppm).
         *     - `hr_cycling`: 7 zonas de Friel sobre `cycling_lthr_bpm` (ppm). Las usa la carga por FC de
         *       ciclismo; la app no las muestra.
         *     - `hr_running`: 7 zonas de Friel (tabla de carrera) sobre `running_lthr_bpm` (ppm).
         */
        ZonesOut: {
            /** Hr Cycling */
            hr_cycling: components["schemas"]["ZoneOut"][] | null;
            /** Hr Running */
            hr_running: components["schemas"]["ZoneOut"][] | null;
            /** Power */
            power: components["schemas"]["ZoneOut"][] | null;
            /** Running Pace */
            running_pace: components["schemas"]["ZoneOut"][] | null;
            /** Trail Hr */
            trail_hr: components["schemas"]["ZoneOut"][] | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    root__get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RootResponse"];
                };
            };
        };
    };
    wahoo_callback_auth_wahoo_callback_get: {
        parameters: {
            query?: {
                code?: string | null;
                error?: string | null;
                state?: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            302: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    readiness_health_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadinessResponse"];
                };
            };
        };
    };
    list_budget_alerts_internal_coach_budget_alerts_get: {
        parameters: {
            query?: never;
            header?: {
                "x-internal-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BudgetAlertsOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_budget_alerts_sent_internal_coach_budget_alerts_sent_post: {
        parameters: {
            query?: never;
            header?: {
                "x-internal-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BudgetAlertsSent"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BudgetAlertsSentOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    ping_internal_ping_get: {
        parameters: {
            query?: never;
            header?: {
                "x-internal-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PingResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_wahoo_all_internal_sync_wahoo_post: {
        parameters: {
            query?: never;
            header?: {
                "x-internal-api-key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InternalSyncOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_availability_v1_athlete_availability_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WeekAvailability"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    replace_availability_v1_athlete_availability_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WeekAvailability"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WeekAvailability"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_fitness_series_v1_athlete_fitness_get: {
        parameters: {
            query: {
                /** @description Primer día del rango (incluido). */
                from: string;
                /** @description Último día del rango (incluido). */
                to: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FitnessSeriesOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_profile_v1_athlete_profile_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_profile_v1_athlete_profile_patch: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProfilePatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProfileOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_proposals_v1_athlete_threshold_proposals_get: {
        parameters: {
            query?: {
                /** @description Filtra por estado. */
                status?: components["schemas"]["ProposalStatus"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdProposalOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_proposal_v1_athlete_threshold_proposals_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ThresholdProposalCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdProposalOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Datos no válidos o que no permiten completar la operación. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Límite de peticiones de un servicio externo. */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Un servicio externo no ha respondido correctamente. */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Servicio no configurado. */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_proposal_v1_athlete_threshold_proposals__proposal_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdProposalOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    accept_proposal_v1_athlete_threshold_proposals__proposal_id__accept_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ThresholdProposalAccept"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdProposalOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    preview_acceptance_v1_athlete_threshold_proposals__proposal_id__preview_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AcceptancePreviewOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reject_proposal_v1_athlete_threshold_proposals__proposal_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                proposal_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdProposalOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    dry_run_v1_athlete_threshold_proposals_dry_run_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ThresholdProposalCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdTestAnalysisOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Datos no válidos o que no permiten completar la operación. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Límite de peticiones de un servicio externo. */
            429: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Un servicio externo no ha respondido correctamente. */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Servicio no configurado. */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_thresholds_v1_athlete_thresholds_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_threshold_v1_athlete_thresholds_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ThresholdCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ThresholdOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_current_threshold_v1_athlete_thresholds_current_get: {
        parameters: {
            query?: {
                /** @description Fecha de referencia. Por defecto, hoy en la zona horaria del atleta. */
                on?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurrentThresholdOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_events_v1_calendar_events_get: {
        parameters: {
            query: {
                /** @description Primer día del rango (incluido). */
                from: string;
                /** @description Último día del rango (incluido). */
                to: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CalendarEventOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_event_v1_calendar_events_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CalendarEventCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CalendarEventOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_event_v1_calendar_events__event_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_event_v1_calendar_events__event_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                event_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CalendarEventPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CalendarEventOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_conversations_v1_coach_conversations_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_conversation_v1_coach_conversations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConversationCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationCreatedOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Un servicio externo no ha respondido correctamente. */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Servicio no configurado. */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_conversation_v1_coach_conversations__conversation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_messages_v1_coach_conversations__conversation_id__messages_get: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessageOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    send_message_v1_coach_conversations__conversation_id__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CoachReplyOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Un servicio externo no ha respondido correctamente. */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Servicio no configurado. */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_memory_v1_coach_memory_get: {
        parameters: {
            query?: {
                /** @description Por defecto, sólo la memoria confirmada. */
                status?: components["schemas"]["MemoryStatus"] | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    create_memory_v1_coach_memory_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemoryCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    delete_memory_v1_coach_memory__memory_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                memory_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    update_memory_v1_coach_memory__memory_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                memory_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemoryPatch"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    confirm_memory_v1_coach_memory__memory_id__confirm_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                memory_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MemoryConfirm"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reject_memory_v1_coach_memory__memory_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                memory_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_status_v1_coach_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CoachStatusOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_integrations_v1_integrations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["IntegrationOut"][];
                };
            };
        };
    };
    disconnect_wahoo_v1_integrations_wahoo_delete: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    wahoo_authorize_url_v1_integrations_wahoo_authorize_url_get: {
        parameters: {
            query?: {
                platform?: "mobile" | "web";
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthorizeUrlOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    sync_wahoo_v1_integrations_wahoo_sync_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SyncOut"];
                };
            };
        };
    };
    read_me_v1_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MeResponse"];
                };
            };
        };
    };
    list_planned_workouts_v1_planned_workouts_get: {
        parameters: {
            query: {
                /** @description Primer día del rango (incluido). */
                from: string;
                /** @description Último día del rango (incluido). */
                to: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlannedWorkoutOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    search_exercises_v1_strength_exercises_get: {
        parameters: {
            query?: {
                limit?: number;
                /** @description Texto en el nombre o un alias, sin distinguir mayúsculas ni acentos. */
                q?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExerciseOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    exercise_last_log_v1_strength_exercises__exercise_id__last_log_get: {
        parameters: {
            query?: {
                /** @description Entreno que se está viendo: devuelve la última sesión completada anterior a él (sin contarlo). */
                before_workout_id?: string | null;
            };
            header?: never;
            path: {
                exercise_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExerciseLastLogOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    exercise_progress_v1_strength_exercises__exercise_id__progress_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                exercise_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExerciseProgressOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    performed_exercises_v1_strength_progress_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PerformedExerciseOut"][];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    strength_weekly_v1_strength_weekly_get: {
        parameters: {
            query: {
                /** @description Primer día del rango (incluido). */
                from: string;
                /** @description Último día del rango (incluido). */
                to: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StrengthWeeklyOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    get_strength_workout_v1_strength_workouts__workout_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workout_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StrengthWorkoutOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Datos no válidos o que no permiten completar la operación. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    complete_workout_v1_strength_workouts__workout_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workout_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StrengthWorkoutComplete"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StrengthWorkoutOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Datos no válidos o que no permiten completar la operación. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    replace_sets_v1_strength_workouts__workout_id__sets_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workout_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StrengthSetsPut"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StrengthWorkoutOut"];
                };
            };
            /** @description Falta el JWT o no es válido. */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Recurso no encontrado. */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflicto con el estado actual. */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Datos no válidos o que no permiten completar la operación. */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Endpoint declarado en el contrato pero todavía sin implementar. */
            501: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    verify_subscription_webhooks_strava_get: {
        parameters: {
            query: {
                "hub.challenge": string;
                "hub.mode": string;
                "hub.verify_token": string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    receive_event_webhooks_strava_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StravaEvent"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReceivedResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
