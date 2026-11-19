/** Cliente de los entrenos planificados y la sesión de fuerza (contrato de #30). */
import { request, withMock } from './http';
import { strengthMock } from './strengthMock';
import type {
  ExerciseLastLogOut,
  PlannedWorkoutOut,
  StrengthSetIn,
  StrengthWorkoutComplete,
  StrengthWorkoutOut,
} from './types';

const workoutPath = (id: string) => `/v1/strength/workouts/${encodeURIComponent(id)}`;

export const plannedWorkoutsApi = {
  /** Entrenos planificados de cualquier disciplina en `[from, to]` (YYYY-MM-DD, máximo 366 días). */
  list: (from: string, to: string) =>
    withMock(
      () => request<PlannedWorkoutOut[]>('GET', '/v1/planned-workouts', { query: { from, to } }),
      () => strengthMock.listPlanned(from, to),
    ),
};

export const strengthApi = {
  /** Detalle de la sesión: ejercicios, series registradas y actividad (si ya se completó). */
  getWorkout: (id: string) =>
    withMock(
      () => request<StrengthWorkoutOut>('GET', workoutPath(id)),
      () => strengthMock.getWorkout(id),
    ),

  /** Sustituye TODAS las series de la sesión por `sets` (se envía siempre la lista completa). */
  replaceSets: (id: string, sets: StrengthSetIn[]) =>
    withMock(
      () => request<StrengthWorkoutOut>('PUT', `${workoutPath(id)}/sets`, { body: { sets } }),
      () => strengthMock.replaceSets(id, sets),
    ),

  /** Cierra la sesión: la API crea la actividad de fuerza y calcula su carga `session_rpe`. */
  complete: (id: string, body: StrengthWorkoutComplete) =>
    withMock(
      () => request<StrengthWorkoutOut>('POST', `${workoutPath(id)}/complete`, { body }),
      () => strengthMock.complete(id, body),
    ),

  /** Series de la última sesión completada con ese ejercicio (`sets` vacía si no hay ninguna). */
  lastLog: (exerciseId: string) =>
    withMock(
      () => request<ExerciseLastLogOut>('GET', `/v1/strength/exercises/${encodeURIComponent(exerciseId)}/last-log`),
      () => strengthMock.lastLog(exerciseId),
    ),
};
