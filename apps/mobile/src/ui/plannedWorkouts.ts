// Presentación de los entrenos planificados (Hoy y Plan): icono por disciplina, resumen y entrada de
// agenda. La fuerza va sin color de zona. Sólo datos de la API: ninguna duración ni carga inventada.
import type { PlannedWorkoutOut, Sport } from '../api/types';
import type { AgendaEntry } from './Agenda';
import type { IconName } from './Icon';
import { SPORT_LABELS } from './labels';

export const SPORT_ICONS: Record<Sport, IconName> = {
  strength: 'sportStrength',
  cycling: 'sportCycling',
  running: 'sportRunning',
  trail_running: 'sportTrail',
  hiking: 'sportTrail',
  swimming: 'sportSwimming',
  other: 'sportOther',
};

/** Prefijo de la clave de agenda de un entreno (las de los eventos son su id). */
export const WORKOUT_KEY_PREFIX = 'workout:';

export function workoutIdFromKey(key: string): string | null {
  return key.startsWith(WORKOUT_KEY_PREFIX) ? key.slice(WORKOUT_KEY_PREFIX.length) : null;
}

/** «50 min», «1 h 05 min». */
export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, '0')} min`;
}

/**
 * «Fuerza · 6 ejercicios · 50 min», con el estado si ya no está pendiente. Todo sale de la lista
 * (`GET /v1/planned-workouts`, #52): el número de ejercicios y la duración planificada, sólo si se ha
 * definido y la sesión no está hecha. La duración real de una sesión hecha está en su pantalla.
 */
export function workoutSummary(workout: PlannedWorkoutOut): string {
  const count = workout.exercise_count;
  const planned = workout.status !== 'done' ? workout.planned_duration_s : null;
  return [
    SPORT_LABELS[workout.sport],
    workout.status === 'done' ? 'hecho' : workout.status === 'skipped' ? 'saltado' : null,
    workout.sport === 'strength' ? (count === 1 ? '1 ejercicio' : `${count} ejercicios`) : null,
    planned ? formatDuration(planned) : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

/** Sólo la fuerza tiene pantalla de sesión por ahora. */
export function hasSessionScreen(workout: PlannedWorkoutOut): boolean {
  return workout.sport === 'strength';
}

export function workoutToAgendaEntry(workout: PlannedWorkoutOut, subtitle?: string): AgendaEntry {
  return {
    key: `${WORKOUT_KEY_PREFIX}${workout.id}`,
    title: workout.title,
    subtitle: subtitle ?? workoutSummary(workout),
    icon: workout.status === 'done' ? 'check' : SPORT_ICONS[workout.sport],
    muted: workout.status !== 'planned',
    disabled: !hasSessionScreen(workout),
  };
}

/** Entrenos de cada día de `days`. */
export function workoutsByDay(workouts: PlannedWorkoutOut[], days: string[]): Record<string, PlannedWorkoutOut[]> {
  const map: Record<string, PlannedWorkoutOut[]> = Object.fromEntries(days.map((d) => [d, []]));
  for (const w of workouts) map[w.scheduled_on]?.push(w);
  return map;
}
