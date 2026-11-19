// Modelo de las series de una sesión de fuerza en la app: borradores editables a partir del detalle
// de la API y la lista completa que se envía a `PUT /v1/strength/workouts/{id}/sets` (contrato de #30).
// Sólo validación de formato y rangos del contrato; ningún cálculo de métricas.
import type {
  ExerciseLastLogOut,
  ExerciseMode,
  PlannedStrengthExerciseOut,
  StrengthSetIn,
  StrengthSetLogOut,
  StrengthWorkoutOut,
} from '../../api/types';
import { longDayLabel } from '../../ui/calendarDates';

/** `pending`: sin registrar. `done`: hecha. `failed`: registrada como no completada (p. ej. desde otro cliente). */
export type SetStatus = 'pending' | 'done' | 'failed';

export type SetField = 'value' | 'weight' | 'rpe' | 'rir';

export type SetDraft = {
  setNumber: number;
  status: SetStatus;
  /** Repeticiones o segundos, según `mode`. */
  mode: ExerciseMode;
  value: string;
  weight: string;
  rpe: string;
  rir: string;
  /**
   * Ejercicio hecho si no es el planificado (una sustitución registrada desde otro cliente); se
   * conserva al reenviar la lista.
   */
  exerciseId: string | null;
};

/** Borradores por ejercicio planificado (`PlannedStrengthExerciseOut.id`). */
export type Drafts = Record<string, SetDraft[]>;

const RANGES: Record<SetField | 'seconds', { min: number; max: number }> = {
  value: { min: 0, max: 1000 },
  seconds: { min: 0, max: 3600 },
  weight: { min: 0, max: 999.99 },
  rpe: { min: 1, max: 10 },
  rir: { min: 0, max: 10 },
};

/** 62.5 → «62,5». */
export function formatWeight(kg: number): string {
  return kg.toLocaleString('es-ES', { maximumFractionDigits: 2, useGrouping: false });
}

const intText = (n: number | null | undefined) => (n == null ? '' : String(n));

function draftFromLog(log: StrengthSetLogOut, planned: PlannedStrengthExerciseOut): SetDraft {
  const mode: ExerciseMode = log.seconds != null ? 'seconds' : log.reps != null ? 'reps' : planned.exercise.mode;
  return {
    setNumber: log.set_number,
    status: log.completed ? 'done' : 'failed',
    mode,
    value: intText(mode === 'seconds' ? log.seconds : log.reps),
    weight: log.weight_kg == null ? '' : formatWeight(log.weight_kg),
    rpe: intText(log.rpe),
    rir: intText(log.rir),
    exerciseId: log.exercise_id !== planned.exercise.id ? log.exercise_id : null,
  };
}

/** Serie sin registrar, precargada con lo planificado (repeticiones o segundos y peso objetivo). */
function draftFromTarget(setNumber: number, planned: PlannedStrengthExerciseOut): SetDraft {
  const mode = planned.exercise.mode;
  return {
    setNumber,
    status: 'pending',
    mode,
    value: intText(mode === 'seconds' ? planned.target_seconds : planned.target_reps),
    weight: planned.target_weight_kg == null ? '' : formatWeight(planned.target_weight_kg),
    rpe: '',
    rir: '',
    exerciseId: null,
  };
}

/** Una fila por serie planificada (más las registradas por encima de lo planificado). */
export function draftsFromWorkout(workout: StrengthWorkoutOut): Drafts {
  const drafts: Drafts = {};
  for (const planned of workout.exercises) {
    const logs = workout.set_logs.filter((l) => l.planned_exercise_id === planned.id);
    const count = Math.max(planned.sets, ...logs.map((l) => l.set_number));
    drafts[planned.id] = Array.from({ length: count }, (_, i) => {
      const log = logs.find((l) => l.set_number === i + 1);
      return log ? draftFromLog(log, planned) : draftFromTarget(i + 1, planned);
    });
  }
  return drafts;
}

/** Series extra (sin ejercicio planificado): la app no las edita, pero las reenvía tal cual. */
export function extraSets(workout: StrengthWorkoutOut): StrengthSetIn[] {
  return workout.set_logs
    .filter((l) => l.planned_exercise_id == null)
    .map((l) => ({
      planned_exercise_id: null,
      exercise_id: l.exercise_id,
      set_number: l.set_number,
      reps: l.reps,
      seconds: l.seconds,
      weight_kg: l.weight_kg,
      rpe: l.rpe,
      rir: l.rir,
      completed: l.completed,
    }));
}

/** Los borradores guardados siguen valiendo si cubren exactamente los mismos ejercicios planificados. */
export function draftsMatchWorkout(drafts: Drafts, workout: StrengthWorkoutOut): boolean {
  const ids = Object.keys(drafts);
  return ids.length === workout.exercises.length && workout.exercises.every((e) => Array.isArray(drafts[e.id]));
}

type Parsed = { ok: true; value: number | null } | { ok: false };

function parseNumber(text: string, range: { min: number; max: number }, opts: { required: boolean; decimals: number }): Parsed {
  const t = text.trim().replace(',', '.');
  if (!t) return opts.required ? { ok: false } : { ok: true, value: null };
  const pattern = opts.decimals > 0 ? new RegExp(`^\\d+(\\.\\d{1,${opts.decimals}})?$`) : /^\d+$/;
  if (!pattern.test(t)) return { ok: false };
  const value = Number(t);
  if (value < range.min || value > range.max) return { ok: false };
  return { ok: true, value };
}

/** Campos no válidos de una serie (vacío si se puede enviar). Las pendientes no se envían. */
export function invalidFields(draft: SetDraft): SetField[] {
  if (draft.status === 'pending') return [];
  const bad: SetField[] = [];
  if (!parseNumber(draft.value, draft.mode === 'seconds' ? RANGES.seconds : RANGES.value, { required: true, decimals: 0 }).ok) bad.push('value');
  if (!parseNumber(draft.weight, RANGES.weight, { required: false, decimals: 2 }).ok) bad.push('weight');
  if (!parseNumber(draft.rpe, RANGES.rpe, { required: false, decimals: 0 }).ok) bad.push('rpe');
  if (!parseNumber(draft.rir, RANGES.rir, { required: false, decimals: 0 }).ok) bad.push('rir');
  return bad;
}

function valueOf(text: string, decimals: number): number | null {
  const t = text.trim().replace(',', '.');
  return t ? Number(Number(t).toFixed(decimals)) : null;
}

/**
 * Lista completa para `PUT /sets`: las series hechas (o registradas como no completadas) de cada
 * ejercicio planificado y las extras. Devuelve null si alguna serie registrada tiene datos no válidos:
 * enviar la lista sin ella la borraría en la API.
 */
export function buildSetsPayload(drafts: Drafts, extras: StrengthSetIn[]): StrengthSetIn[] | null {
  const sets: StrengthSetIn[] = [];
  for (const [plannedId, list] of Object.entries(drafts)) {
    for (const d of list) {
      if (d.status === 'pending') continue;
      if (invalidFields(d).length > 0) return null;
      const amount = valueOf(d.value, 0);
      sets.push({
        planned_exercise_id: plannedId,
        ...(d.exerciseId ? { exercise_id: d.exerciseId } : {}),
        set_number: d.setNumber,
        reps: d.mode === 'reps' ? amount : null,
        seconds: d.mode === 'seconds' ? amount : null,
        weight_kg: valueOf(d.weight, 2),
        rpe: valueOf(d.rpe, 0),
        rir: valueOf(d.rir, 0),
        completed: d.status === 'done',
      });
    }
  }
  return [...sets, ...extras];
}

export function countSets(drafts: Drafts): { done: number; total: number } {
  const all = Object.values(drafts).flat();
  return { done: all.filter((d) => d.status === 'done').length, total: all.length };
}

/** «3 × 10», «3 × 30 s», con peso, RPE y RIR objetivo si los hay. */
export function targetLabel(planned: PlannedStrengthExerciseOut): string {
  const amount = planned.exercise.mode === 'seconds' ? (planned.target_seconds != null ? `${planned.target_seconds} s` : null) : planned.target_reps;
  return [
    amount != null ? `${planned.sets} × ${amount}` : `${planned.sets} series`,
    planned.target_weight_kg != null ? `${formatWeight(planned.target_weight_kg)} kg` : null,
    planned.target_rpe != null ? `RPE ${planned.target_rpe}` : null,
    planned.target_rir != null ? `RIR ${planned.target_rir}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

/**
 * «Jueves 12 nov · 57,5 kg × 8 · 8 · 6»: series completadas de la última sesión completada. Si el peso
 * cambia entre series, va en cada una («60 kg × 8 · 62,5 kg × 6»). Null si no hay ninguna anterior (o
 * si la última es esta misma sesión).
 */
export function lastLogLabel(log: ExerciseLastLogOut | undefined, currentWorkoutId: string): string | null {
  if (!log || !log.performed_on || log.sets.length === 0 || log.planned_workout_id === currentWorkoutId) return null;
  const completed = log.sets.filter((s) => s.completed);
  const sets = completed.length > 0 ? completed : log.sets;
  const amount = (s: (typeof sets)[number]) => (s.seconds != null ? `${s.seconds} s` : s.reps != null ? String(s.reps) : '—');
  const weights = new Set(sets.map((s) => s.weight_kg));
  let detail: string;
  if (weights.size === 1) {
    const kg = sets[0].weight_kg;
    const amounts = sets.map(amount).join(' · ');
    const reps = sets.every((s) => s.seconds == null) ? ' rep.' : '';
    detail = kg != null ? `${formatWeight(kg)} kg × ${amounts}` : `${amounts}${reps}`;
  } else {
    detail = sets.map((s) => (s.weight_kg != null ? `${formatWeight(s.weight_kg)} kg × ${amount(s)}` : amount(s))).join(' · ');
  }
  return `${longDayLabel(log.performed_on)} · ${detail}`;
}
