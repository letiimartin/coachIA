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
        /** PingResponse */
        PingResponse: {
            /**
             * Status
             * @constant
             */
            status: "ok";
        };
        /**
         * PreferredTime
         * @enum {string}
         */
        PreferredTime: "morning" | "midday" | "afternoon" | "evening" | "any";
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
         * Provider
         * @enum {string}
         */
        Provider: "wahoo" | "strava" | "suunto" | "garmin";
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
         * ThresholdSource
         * @enum {string}
         */
        ThresholdSource: "manual" | "test" | "estimated";
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
