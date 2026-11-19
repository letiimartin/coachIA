/**
 * Datos de prueba de la fuerza a partir de los `examples` del contrato (apps/api/openapi.json).
 *
 * La sesión de ejemplo se planifica para hoy, para que se vea en Hoy y en Plan. Las escrituras sólo
 * viven en memoria. La carga de la actividad la calcula la API: aquí se deja vacía.
 */
import { contractExamples } from './contractExamples.generated';
import { ApiError } from './errors';
import type {
  ExerciseLastLogOut,
  ExerciseOut,
  PlannedWorkoutOut,
  StrengthSetIn,
  StrengthSetLogOut,
  StrengthWorkoutComplete,
  StrengthWorkoutOut,
} from './types';

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Los ejemplos omiten los campos opcionales; el schema de salida los exige (null). */
function normalizeWorkout(raw: unknown): StrengthWorkoutOut {
  const w = raw as StrengthWorkoutOut;
  return {
    ...w,
    coach_reason: w.coach_reason ?? null,
    exercise_count: w.exercises.length,
    planned_duration_s: w.planned_duration_s ?? null,
    activity_id: w.activity_id ?? null,
    activity: w.activity ?? null,
    exercises: w.exercises.map((e) => ({
      ...e,
      target_reps: e.target_reps ?? null,
      target_seconds: e.target_seconds ?? null,
      target_weight_kg: e.target_weight_kg ?? null,
      target_rpe: e.target_rpe ?? null,
      target_rir: e.target_rir ?? null,
      notes: e.notes ?? null,
    })),
    set_logs: w.set_logs.map(normalizeLog),
  };
}

function normalizeLog(raw: StrengthSetLogOut): StrengthSetLogOut {
  return {
    ...raw,
    activity_id: raw.activity_id ?? null,
    planned_exercise_id: raw.planned_exercise_id ?? null,
    reps: raw.reps ?? null,
    seconds: raw.seconds ?? null,
    weight_kg: raw.weight_kg ?? null,
    rpe: raw.rpe ?? null,
    rir: raw.rir ?? null,
  };
}

const exampleWorkout = normalizeWorkout(contractExamples.StrengthWorkoutOut?.[0]);
const exampleLastLog = contractExamples.ExerciseLastLogOut?.[0] as ExerciseLastLogOut | undefined;

const db: { workouts: StrengthWorkoutOut[] } = {
  workouts: [{ ...exampleWorkout, scheduled_on: todayIso() }],
};

const delay = <T>(value: T): Promise<T> => new Promise((resolve) => setTimeout(() => resolve(clone(value)), 150));
const notFound = () => new ApiError(404, 'not_found', 'Entreno no encontrado (datos de prueba).');

function toPlanned(w: StrengthWorkoutOut): PlannedWorkoutOut {
  const { exercises: _e, set_logs: _s, activity: _a, ...planned } = w;
  return planned;
}

function find(id: string): StrengthWorkoutOut | undefined {
  return db.workouts.find((w) => w.id === id);
}

export const strengthMock = {
  listPlanned: (from: string, to: string) =>
    delay(db.workouts.filter((w) => w.scheduled_on >= from && w.scheduled_on <= to).map(toPlanned)),

  getWorkout(id: string) {
    const w = find(id);
    return w ? delay(w) : Promise.reject(notFound());
  },

  replaceSets(id: string, sets: StrengthSetIn[]) {
    const w = find(id);
    if (!w) return Promise.reject(notFound());
    if (w.status === 'skipped') return Promise.reject(new ApiError(409, 'conflict', 'El entreno está saltado.'));
    w.set_logs = sets.map((s) => {
      const planned = w.exercises.find((e) => e.id === s.planned_exercise_id);
      return {
        id: uuid(),
        exercise_id: s.exercise_id ?? planned?.exercise.id ?? '',
        planned_exercise_id: s.planned_exercise_id ?? null,
        activity_id: w.activity_id,
        set_number: s.set_number,
        reps: s.reps ?? null,
        seconds: s.seconds ?? null,
        weight_kg: s.weight_kg ?? null,
        rpe: s.rpe ?? null,
        rir: s.rir ?? null,
        completed: s.completed ?? true,
      };
    });
    w.updated_at = new Date().toISOString();
    return delay(w);
  },

  complete(id: string, body: StrengthWorkoutComplete) {
    const w = find(id);
    if (!w) return Promise.reject(notFound());
    if (w.status !== 'planned') return Promise.reject(new ApiError(409, 'conflict', 'El entreno ya está completado o saltado.'));
    const activityId = uuid();
    w.status = 'done';
    w.activity_id = activityId;
    w.activity = { id: activityId, start_at: body.started_at, elapsed_s: body.duration_s, rpe: body.rpe ?? null, load: null, load_method: null };
    w.set_logs = w.set_logs.map((s) => ({ ...s, activity_id: activityId }));
    return delay(w);
  },

  /**
   * El ejemplo del contrato hace de sesión anterior (es de otro día). Comparte el id de la sesión de
   * ejemplo, así que con `beforeWorkoutId` se devuelve sin ese id, como si fuera otra sesión.
   */
  lastLog(exerciseId: string, beforeWorkoutId?: string) {
    if (exampleLastLog && exampleLastLog.exercise.id === exerciseId) {
      const sets = exampleLastLog.sets.map((x) => ({ ...x, reps: x.reps ?? null, seconds: x.seconds ?? null, weight_kg: x.weight_kg ?? null, rpe: x.rpe ?? null, rir: x.rir ?? null }));
      const sameWorkout = beforeWorkoutId != null && exampleLastLog.planned_workout_id === beforeWorkoutId;
      return delay({ ...exampleLastLog, planned_workout_id: sameWorkout ? null : exampleLastLog.planned_workout_id, sets });
    }
    const exercise = db.workouts.flatMap((w) => w.exercises).find((e) => e.exercise.id === exerciseId)?.exercise;
    if (!exercise) return Promise.reject(new ApiError(404, 'not_found', 'Ejercicio no encontrado (datos de prueba).'));
    const empty: ExerciseLastLogOut = { exercise: exercise as ExerciseOut, performed_on: null, activity_id: null, planned_workout_id: null, sets: [] };
    return delay(empty);
  },
};
