/**
 * Textos de la fuerza en Rendimiento (#33). Sólo dan formato a valores que ya vienen calculados de
 * la API (peso máximo, volumen, mejor serie, carga): no calculan ninguna métrica.
 */
import type { ExerciseMode, ExerciseSessionOut } from '../../api/types';
import { longDayLabel } from '../../ui/calendarDates';
import type { ProgressPoint } from '../../ui/ProgressChart';
import { formatWeight } from '../strength/strengthSets';

/** 5400 → «1:30». */
export function formatHours(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
}

/** Cifra entera con separador de miles: 1360 → «1360», 12450 → «12.450». */
export function formatInt(value: number): string {
  return Math.round(value).toLocaleString('es-ES');
}

/** «8 × 62,5 kg», «12 reps», «60 s», «45 s × 16 kg». */
export function bestSetLabel(s: ExerciseSessionOut): string | null {
  const weight = s.max_weight_kg != null ? `${formatWeight(s.max_weight_kg)} kg` : null;
  if (s.best_set_seconds != null) return weight ? `${s.best_set_seconds} s · ${weight}` : `${s.best_set_seconds} s`;
  if (s.best_set_reps != null) return weight ? `${s.best_set_reps} × ${weight}` : `${s.best_set_reps} reps`;
  return null;
}

/** «3 series · 24 reps» o «2 series · 90 s». */
export function setsLabel(s: ExerciseSessionOut): string {
  const series = s.sets === 1 ? '1 serie' : `${s.sets} series`;
  if (s.total_reps != null) return `${series} · ${s.total_reps} reps`;
  if (s.total_seconds != null) return `${series} · ${s.total_seconds} s`;
  return series;
}

export function sessionDayLabel(s: ExerciseSessionOut): string {
  return longDayLabel(s.performed_on);
}

export type ChartSpec = { points: ProgressPoint[]; lineLabel: string; barLabel: string };

/**
 * Qué se dibuja según el ejercicio: con peso, el peso máximo (línea) y el volumen (barras); sin peso,
 * las repeticiones o segundos de la mejor serie (línea) y el total de la sesión (barras).
 */
export function chartSpec(sessions: ExerciseSessionOut[], mode: ExerciseMode): ChartSpec {
  const weighted = sessions.some((s) => s.max_weight_kg != null);
  const hasVolume = sessions.some((s) => s.volume_kg != null);
  const seconds = mode === 'seconds';
  return {
    points: sessions.map((s) => ({
      day: s.performed_on,
      line: weighted ? s.max_weight_kg : seconds ? s.best_set_seconds : s.best_set_reps,
      bar: hasVolume ? s.volume_kg : seconds ? s.total_seconds : s.total_reps,
    })),
    lineLabel: weighted ? 'Peso máximo (kg)' : seconds ? 'Mejor serie (s)' : 'Mejor serie (reps)',
    barLabel: hasVolume ? 'Volumen (kg)' : seconds ? 'Segundos totales' : 'Repeticiones totales',
  };
}
