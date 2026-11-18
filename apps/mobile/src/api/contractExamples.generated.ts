// Generado por scripts/gen-api.mjs a partir de apps/api/openapi.json. No editar a mano.
/* eslint-disable */
// Los ejemplos se exportan sin tipar: algunos omiten campos nulos (p. ej. `high` en la última zona),
// así que la capa de mock los normaliza antes de usarlos.
export const contractExamples: Record<string, unknown[]> = {
  "CalendarEventCreate": [
    {
      "all_day": false,
      "kind": "race",
      "race": {
        "ascent_m": 2400,
        "discipline": "trail_running",
        "distance_m": 42000,
        "goal": "Terminar por debajo de 6 h.",
        "priority": "A",
        "source_url": "https://example.com/carrera"
      },
      "start_at": "2027-04-18T07:00:00+02:00",
      "title": "Trail de la Sierra",
      "training_impact": "none"
    },
    {
      "all_day": true,
      "end_at": "2026-12-04T23:59:00+01:00",
      "kind": "travel",
      "notes": "Hotel con gimnasio.",
      "start_at": "2026-12-02T00:00:00+01:00",
      "title": "Viaje de trabajo a Lisboa",
      "training_impact": "reduce"
    }
  ],
  "CalendarEventOut": [
    {
      "all_day": false,
      "created_at": "2026-11-17T10:00:00Z",
      "details": {},
      "id": "3f2a1b4c-5d6e-4f70-8a9b-0c1d2e3f4a5b",
      "kind": "race",
      "race": {
        "ascent_m": 2400,
        "discipline": "trail_running",
        "distance_m": 42000,
        "enrichment_status": "none",
        "goal": "Terminar por debajo de 6 h.",
        "priority": "A",
        "source_url": "https://example.com/carrera"
      },
      "start_at": "2027-04-18T05:00:00Z",
      "title": "Trail de la Sierra",
      "training_impact": "none",
      "updated_at": "2026-11-17T10:00:00Z"
    }
  ],
  "CalendarEventPatch": [
    {
      "race": {
        "priority": "A"
      },
      "title": "Trail de la Sierra (42K)"
    },
    {
      "training_impact": "no_training"
    }
  ],
  "CurrentThresholdOut": [
    {
      "on": "2026-11-17",
      "threshold": {
        "created_at": "2026-11-01T19:00:00Z",
        "cycling_lthr_bpm": 165,
        "effective_from": "2026-11-01",
        "ftp_w": 230,
        "hr_max_bpm": 186,
        "hr_rest_bpm": 48,
        "id": "8d5e2f0a-6b1c-4f3e-9a7d-2c4b6e8f0a1b",
        "notes": "Test de 20 min en rodillo.",
        "running_lthr_bpm": 172,
        "source": "test",
        "threshold_pace_s_per_km": 285,
        "updated_at": "2026-11-01T19:00:00Z",
        "vo2max": 52,
        "weight_kg": 58.5
      },
      "zones": {
        "hr_cycling": [
          {
            "code": "Z1",
            "high": 133.7,
            "low": 0,
            "name": "Recuperación",
            "number": 1
          },
          {
            "code": "Z2",
            "high": 148.5,
            "low": 133.7,
            "name": "Resistencia aeróbica",
            "number": 2
          },
          {
            "code": "Z3",
            "high": 155.1,
            "low": 148.5,
            "name": "Tempo",
            "number": 3
          },
          {
            "code": "Z4",
            "high": 165,
            "low": 155.1,
            "name": "Subumbral",
            "number": 4
          },
          {
            "code": "Z5a",
            "high": 170,
            "low": 165,
            "name": "Supraumbral",
            "number": 5
          },
          {
            "code": "Z5b",
            "high": 174.9,
            "low": 170,
            "name": "Capacidad aeróbica",
            "number": 6
          },
          {
            "code": "Z5c",
            "low": 174.9,
            "name": "Potencia anaeróbica",
            "number": 7
          }
        ],
        "hr_running": [
          {
            "code": "Z1",
            "high": 146.2,
            "low": 0,
            "name": "Recuperación",
            "number": 1
          },
          {
            "code": "Z2",
            "high": 154.8,
            "low": 146.2,
            "name": "Resistencia aeróbica",
            "number": 2
          },
          {
            "code": "Z3",
            "high": 163.4,
            "low": 154.8,
            "name": "Tempo",
            "number": 3
          },
          {
            "code": "Z4",
            "high": 172,
            "low": 163.4,
            "name": "Subumbral",
            "number": 4
          },
          {
            "code": "Z5a",
            "high": 177.2,
            "low": 172,
            "name": "Supraumbral",
            "number": 5
          },
          {
            "code": "Z5b",
            "high": 182.3,
            "low": 177.2,
            "name": "Capacidad aeróbica",
            "number": 6
          },
          {
            "code": "Z5c",
            "low": 182.3,
            "name": "Potencia anaeróbica",
            "number": 7
          }
        ],
        "power": [
          {
            "code": "Z1",
            "high": 126.5,
            "low": 0,
            "name": "Recuperación activa",
            "number": 1
          },
          {
            "code": "Z2",
            "high": 172.5,
            "low": 126.5,
            "name": "Resistencia",
            "number": 2
          },
          {
            "code": "Z3",
            "high": 207,
            "low": 172.5,
            "name": "Tempo",
            "number": 3
          },
          {
            "code": "Z4",
            "high": 241.5,
            "low": 207,
            "name": "Umbral",
            "number": 4
          },
          {
            "code": "Z5",
            "high": 276,
            "low": 241.5,
            "name": "VO2máx",
            "number": 5
          },
          {
            "code": "Z6",
            "high": 345,
            "low": 276,
            "name": "Capacidad anaeróbica",
            "number": 6
          },
          {
            "code": "Z7",
            "low": 345,
            "name": "Neuromuscular",
            "number": 7
          }
        ],
        "running_pace": [
          {
            "code": "Z1",
            "low": 367.7,
            "name": "Recuperación",
            "number": 1
          },
          {
            "code": "Z2",
            "high": 367.7,
            "low": 324.9,
            "name": "Aeróbico",
            "number": 2
          },
          {
            "code": "Z3",
            "high": 324.9,
            "low": 302.1,
            "name": "Tempo",
            "number": 3
          },
          {
            "code": "Z4",
            "high": 302.1,
            "low": 285,
            "name": "Umbral",
            "number": 4
          },
          {
            "code": "Z5",
            "high": 285,
            "low": 0,
            "name": "Por encima del umbral",
            "number": 5
          }
        ],
        "trail_hr": [
          {
            "code": "Z1",
            "high": 146.2,
            "low": 0,
            "name": "Recuperación",
            "number": 1
          },
          {
            "code": "Z2",
            "high": 154.8,
            "low": 146.2,
            "name": "Aeróbico",
            "number": 2
          },
          {
            "code": "Z3",
            "high": 163.4,
            "low": 154.8,
            "name": "Tempo",
            "number": 3
          },
          {
            "code": "Z4",
            "high": 172,
            "low": 163.4,
            "name": "Umbral",
            "number": 4
          },
          {
            "code": "Z5",
            "low": 172,
            "name": "Por encima del umbral",
            "number": 5
          }
        ]
      }
    }
  ],
  "ErrorResponse": [
    {
      "error": {
        "code": "unauthorized",
        "message": "Autenticación requerida."
      },
      "request_id": "6f1c2a8e3b9d4f7a"
    }
  ],
  "FitnessSeriesOut": [
    {
      "days": [
        {
          "atl": 62.9,
          "ctl": 55.6,
          "day": "2026-11-10",
          "load": 80,
          "tsb": -5
        },
        {
          "atl": 53.9,
          "ctl": 54.3,
          "day": "2026-11-11",
          "load": 0,
          "tsb": -7.3
        },
        {
          "atl": 63.3,
          "ctl": 55.8,
          "day": "2026-11-12",
          "load": 120,
          "tsb": 0.4
        }
      ],
      "from": "2026-11-10",
      "to": "2026-11-12"
    }
  ],
  "ProfileOut": [
    {
      "birth_date": "1990-05-14",
      "created_at": "2026-11-01T09:00:00Z",
      "display_name": "Leti",
      "height_cm": 168,
      "preferences": {
        "language": "es",
        "units": "metric"
      },
      "sex": "female",
      "sports": [
        "cycling",
        "trail_running"
      ],
      "timezone": "Europe/Madrid",
      "updated_at": "2026-11-15T18:30:00Z",
      "user_id": "11111111-2222-3333-4444-555555555555"
    }
  ],
  "ProfilePatch": [
    {
      "display_name": "Leti",
      "height_cm": 168,
      "sports": [
        "cycling",
        "trail_running"
      ]
    },
    {
      "timezone": "Atlantic/Canary"
    }
  ],
  "RaceCreate": [
    {
      "ascent_m": 2400,
      "discipline": "trail_running",
      "distance_m": 42000,
      "goal": "Terminar por debajo de 6 h.",
      "priority": "A",
      "source_url": "https://example.com/carrera"
    }
  ],
  "RacePatch": [
    {
      "enrichment_status": "confirmed",
      "priority": "B"
    }
  ],
  "ThresholdCreate": [
    {
      "cycling_lthr_bpm": 165,
      "effective_from": "2026-11-01",
      "ftp_w": 230,
      "hr_max_bpm": 186,
      "hr_rest_bpm": 48,
      "notes": "Test de 20 min en rodillo.",
      "running_lthr_bpm": 172,
      "source": "test",
      "threshold_pace_s_per_km": 285,
      "vo2max": 52,
      "weight_kg": 58.5
    }
  ],
  "ThresholdOut": [
    {
      "created_at": "2026-11-01T19:00:00Z",
      "cycling_lthr_bpm": 165,
      "effective_from": "2026-11-01",
      "ftp_w": 230,
      "hr_max_bpm": 186,
      "hr_rest_bpm": 48,
      "id": "8d5e2f0a-6b1c-4f3e-9a7d-2c4b6e8f0a1b",
      "notes": "Test de 20 min en rodillo.",
      "running_lthr_bpm": 172,
      "source": "test",
      "threshold_pace_s_per_km": 285,
      "updated_at": "2026-11-01T19:00:00Z",
      "vo2max": 52,
      "weight_kg": 58.5
    }
  ],
  "WeekAvailability": [
    {
      "days": [
        {
          "is_preferred_rest": true,
          "max_minutes": 0,
          "preferred_time": "any",
          "sports": [],
          "weekday": 0
        },
        {
          "is_preferred_rest": false,
          "max_minutes": 60,
          "preferred_time": "morning",
          "sports": [
            "running"
          ],
          "weekday": 1
        },
        {
          "is_preferred_rest": false,
          "max_minutes": 90,
          "preferred_time": "evening",
          "sports": [
            "cycling"
          ],
          "weekday": 2
        },
        {
          "is_preferred_rest": false,
          "max_minutes": 60,
          "preferred_time": "morning",
          "sports": [
            "running",
            "strength"
          ],
          "weekday": 3
        },
        {
          "is_preferred_rest": false,
          "max_minutes": 45,
          "preferred_time": "evening",
          "sports": [
            "cycling"
          ],
          "weekday": 4
        },
        {
          "is_preferred_rest": false,
          "max_minutes": 240,
          "preferred_time": "morning",
          "sports": [
            "cycling"
          ],
          "weekday": 5
        },
        {
          "is_preferred_rest": false,
          "max_minutes": 180,
          "preferred_time": "morning",
          "sports": [
            "trail_running"
          ],
          "weekday": 6
        }
      ]
    }
  ]
};
