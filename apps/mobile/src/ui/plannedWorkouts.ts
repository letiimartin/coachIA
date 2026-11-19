// Presentación de los entrenos planificados (Hoy y Plan): icono por disciplina, resumen y entrada de
// agenda. La fuerza va sin color de zona. Sólo datos de la API: ninguna duración ni carga inventada.
import { plannedWorkoutsApi, strengthApi } from '../api/strengthApi';
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

/** Datos de la sesión que no vienen en la lista (`GET /v1/planned-workouts`). */
export type WorkoutSummary = { exerciseCount: number; elapsedS: number | null };

export type PlannedWithSummaries = { workouts: PlannedWorkoutOut[]; summaries: Record<string, WorkoutSummary> };

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

/** «Fuerza · 6 ejercicios · 50 min», con el estado si ya no está pendiente y sin los datos que falten. */
export function workoutSummary(workout: PlannedWorkoutOut, summary?: WorkoutSummary): string {
  const count = summary?.exerciseCount;
  return [
    SPORT_LABELS[workout.sport],
    workout.status === 'done' ? 'hecho' : workout.status === 'skipped' ? 'saltado' : null,
    count != null ? (count === 1 ? '1 ejercicio' : `${count} ejercicios`) : null,
    summary?.elapsedS ? formatDuration(summary.elapsedS) : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

/** Sólo la fuerza tiene pantalla de sesión por ahora. */
export function hasSessionScreen(workout: PlannedWorkoutOut): boolean {
  return workout.sport === 'strength';
}

export function workoutToAgendaEntry(workout: PlannedWorkoutOut, summary?: WorkoutSummary, subtitle?: string): AgendaEntry {
  return {
    key: `${WORKOUT_KEY_PREFIX}${workout.id}`,
    title: workout.title,
    subtitle: subtitle ?? workoutSummary(workout, summary),
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

/**
 * Entrenos de `[from, to]` y, para los de fuerza, el número de ejercicios y la duración real (si ya se
 * hicieron), que sólo trae el detalle. Si falla un detalle, ese entreno se muestra sin resumen.
 */
export async function loadPlannedWithSummaries(from: string, to: string): Promise<PlannedWithSummaries> {
  const workouts = await plannedWorkoutsApi.list(from, to);
  const strength = workouts.filter((w) => w.sport === 'strength' && w.status !== 'skipped');
  const details = await Promise.allSettled(strength.map((w) => strengthApi.getWorkout(w.id)));
  const summaries: Record<string, WorkoutSummary> = {};
  details.forEach((d) => {
    if (d.status === 'fulfilled') summaries[d.value.id] = { exerciseCount: d.value.exercises.length, elapsedS: d.value.activity?.elapsed_s ?? null };
  });
  return { workouts, summaries };
}
