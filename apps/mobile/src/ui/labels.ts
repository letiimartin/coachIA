// Textos en castellano para los enums del contrato.
import type {
  EnrichmentStatus,
  EventKind,
  MemoryKind,
  PreferredTime,
  RaceDiscipline,
  RacePriority,
  Sex,
  Sport,
  ThresholdSource,
  TrainingImpact,
} from '../api/types';

export const SPORT_LABELS: Record<Sport, string> = {
  cycling: 'Ciclismo',
  running: 'Carrera',
  trail_running: 'Trail',
  hiking: 'Senderismo',
  strength: 'Fuerza',
  swimming: 'Natación',
  other: 'Otro',
};

export const SEX_LABELS: Record<Sex, string> = { female: 'Mujer', male: 'Hombre', other: 'Otro' };

export const THRESHOLD_SOURCE_LABELS: Record<ThresholdSource, string> = {
  manual: 'Manual',
  test: 'Test',
  estimated: 'Estimado',
};

export const PREFERRED_TIME_LABELS: Record<PreferredTime, string> = {
  morning: 'Mañana',
  midday: 'Mediodía',
  afternoon: 'Tarde',
  evening: 'Noche',
  any: 'Cualquiera',
};

export const WEEKDAY_LABELS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export const EVENT_KIND_LABELS: Record<EventKind, string> = {
  race: 'Carrera',
  social: 'Social',
  travel: 'Viaje',
  health: 'Salud',
  personal: 'Personal',
  unavailable: 'No disponible',
};

export const TRAINING_IMPACT_LABELS: Record<TrainingImpact, string> = {
  none: 'Sin impacto',
  reduce: 'Reducir carga',
  no_training: 'Sin entrenar',
  move: 'Mover sesiones',
};

export const RACE_DISCIPLINE_LABELS: Record<RaceDiscipline, string> = {
  road_cycling: 'Ciclismo en ruta',
  gravel: 'Gravel',
  mtb: 'MTB',
  trail_running: 'Trail',
  road_running: 'Carrera en asfalto',
  other: 'Otra',
};

export const RACE_PRIORITY_LABELS: Record<RacePriority, string> = { A: 'A (objetivo)', B: 'B', C: 'C' };

export const ENRICHMENT_STATUS_LABELS: Record<EnrichmentStatus, string> = {
  none: 'Sin completar',
  pending_review: 'Completada automáticamente, pendiente de revisar',
  confirmed: 'Confirmada',
};

/** Tipos de memoria del coach (#56). */
export const MEMORY_KIND_LABELS: Record<MemoryKind, string> = { goal: 'Objetivo', preference: 'Preferencia', other: 'Otro' };

export function options<T extends string>(labels: Record<T, string>): { value: T; label: string }[] {
  return (Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value] }));
}
