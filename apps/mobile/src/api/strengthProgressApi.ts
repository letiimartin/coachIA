/**
 * Rendimiento de fuerza (#33): resumen semanal y progresión por ejercicio. Todo lo calcula la API
 * (sesiones, duración, carga `session_rpe`, peso máximo, volumen, mejor serie); la app sólo lo
 * muestra. La carga de fuerza nunca se suma a la forma (CTL/ATL/TSB).
 */
import { contractExamples } from './contractExamples.generated';
import { request, withMock } from './http';
import type { ExerciseProgressOut, PerformedExerciseOut, StrengthWeeklyOut } from './types';

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function later<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(clone(value)), 150));
}

/** Datos de prueba: los ejemplos del contrato tal cual (la app nunca los calcula). */
const mock = {
  weekly: () => later((contractExamples.StrengthWeeklyOut?.[0] ?? { from: '', to: '', weeks: [] }) as StrengthWeeklyOut),
  performed: () => later((contractExamples.PerformedExerciseOut ?? []) as PerformedExerciseOut[]),
  exercise: (exerciseId: string) => {
    const example = contractExamples.ExerciseProgressOut[0] as ExerciseProgressOut;
    return later({ ...example, exercise: { ...example.exercise, id: exerciseId } });
  },
};

export const strengthProgressApi = {
  /** Una semana (de lunes a domingo) por cada lunes desde la semana de `from` hasta la de `to` (YYYY-MM-DD). */
  weekly: (from: string, to: string) =>
    withMock(() => request<StrengthWeeklyOut>('GET', '/v1/strength/weekly', { query: { from, to } }), mock.weekly),

  /** Ejercicios hechos en sesiones completadas, del último hecho al más antiguo. */
  performed: () => withMock(() => request<PerformedExerciseOut[]>('GET', '/v1/strength/progress'), mock.performed),

  /** Historial del ejercicio por sesión completada, de la más antigua a la más reciente. */
  exercise: (exerciseId: string) =>
    withMock(
      () => request<ExerciseProgressOut>('GET', `/v1/strength/exercises/${encodeURIComponent(exerciseId)}/progress`),
      () => mock.exercise(exerciseId),
    ),
};
