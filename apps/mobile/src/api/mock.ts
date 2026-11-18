/**
 * Datos de prueba en memoria a partir de los `examples` del contrato (apps/api/openapi.json).
 *
 * Se usan mientras el backend responda 501. Las escrituras se guardan sólo en memoria (se pierden al
 * recargar). La app nunca calcula zonas: en el mock sólo hay zonas para el umbral de ejemplo, que
 * trae las suyas en el contrato; para un umbral creado en el mock se devuelven vacías.
 */
import { contractExamples } from './contractExamples.generated';
import { ApiError } from './errors';
import type {
  CalendarEventCreate,
  CalendarEventOut,
  CalendarEventPatch,
  CurrentThresholdOut,
  ProfileOut,
  ProfilePatch,
  RaceOut,
  ThresholdCreate,
  ThresholdOut,
  WeekAvailability,
  ZoneOut,
  ZonesOut,
} from './types';

function clone<T>(value: T): T {
  return value === undefined ? value : (JSON.parse(JSON.stringify(value)) as T);
}

function example<T>(schema: string, index = 0): T {
  const list = contractExamples[schema];
  if (!list || list[index] === undefined) throw new Error(`El contrato no tiene ejemplo de ${schema}[${index}]`);
  return clone(list[index]) as T;
}

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.floor(Math.random() * 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const nowIso = () => new Date().toISOString();

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Los ejemplos omiten `high` en la última zona; el schema lo exige (null = sin límite). */
function normalizeZones(zones: Partial<Record<keyof ZonesOut, Partial<ZoneOut>[] | null>>): ZonesOut {
  const norm = (list: Partial<ZoneOut>[] | null | undefined): ZoneOut[] | null =>
    list ? list.map((z) => ({ ...(z as ZoneOut), high: z.high ?? null })) : null;
  return {
    power: norm(zones.power),
    running_pace: norm(zones.running_pace),
    trail_hr: norm(zones.trail_hr),
    hr_cycling: norm(zones.hr_cycling),
    hr_running: norm(zones.hr_running),
  };
}

function raceFromCreate(race: CalendarEventCreate['race']): RaceOut {
  return {
    discipline: race?.discipline ?? null,
    distance_m: race?.distance_m ?? null,
    ascent_m: race?.ascent_m ?? null,
    priority: race?.priority ?? 'B',
    goal: race?.goal ?? null,
    source_url: race?.source_url ?? null,
    enrichment_status: 'none',
  };
}

function eventFromCreate(body: CalendarEventCreate): CalendarEventOut {
  const now = nowIso();
  return {
    id: uuid(),
    kind: body.kind,
    title: body.title,
    start_at: body.start_at,
    end_at: body.end_at ?? null,
    all_day: body.all_day ?? true,
    training_impact: body.training_impact ?? 'none',
    notes: body.notes ?? null,
    details: body.details ?? {},
    race: body.kind === 'race' ? raceFromCreate(body.race) : null,
    created_at: now,
    updated_at: now,
  };
}

// --- Estado inicial ----------------------------------------------------------------------------

const exampleCurrent = example<CurrentThresholdOut>('CurrentThresholdOut');
const exampleZones = normalizeZones(exampleCurrent.zones);

const db = {
  profile: example<ProfileOut>('ProfileOut'),
  thresholds: [example<ThresholdOut>('ThresholdOut')],
  availability: example<WeekAvailability>('WeekAvailability'),
  events: [
    example<CalendarEventOut>('CalendarEventOut'),
    // El segundo ejemplo de creación (un viaje) también se muestra, para tener más de un tipo.
    eventFromCreate(example<CalendarEventCreate>('CalendarEventCreate', 1)),
  ],
};

const delay = <T>(value: T): Promise<T> => new Promise((resolve) => setTimeout(() => resolve(clone(value)), 150));

const notFound = () => new ApiError(404, 'not_found', 'Recurso no encontrado (datos de prueba).');

// --- Endpoints -----------------------------------------------------------------------------------

export const mockApi = {
  getProfile: () => delay(db.profile),

  updateProfile(patch: ProfilePatch) {
    const next = { ...db.profile, updated_at: nowIso() };
    for (const [key, value] of Object.entries(patch) as [keyof ProfilePatch, unknown][]) {
      if (value === undefined) continue;
      (next as Record<string, unknown>)[key] = value;
    }
    db.profile = next;
    return delay(db.profile);
  },

  listThresholds: () =>
    delay([...db.thresholds].sort((a, b) => b.effective_from.localeCompare(a.effective_from))),

  getCurrentThreshold(on?: string): Promise<CurrentThresholdOut> {
    const date = on ?? todayIso();
    const current = [...db.thresholds]
      .filter((t) => t.effective_from <= date)
      .sort((a, b) => b.effective_from.localeCompare(a.effective_from))[0];
    if (!current) return Promise.reject(new ApiError(404, 'not_found', 'No hay umbrales vigentes en esa fecha.'));
    const zones =
      current.id === exampleCurrent.threshold.id
        ? exampleZones
        : { power: null, running_pace: null, trail_hr: null, hr_cycling: null, hr_running: null };
    return delay({ on: date, threshold: current, zones });
  },

  createThreshold(body: ThresholdCreate) {
    if (db.thresholds.some((t) => t.effective_from === body.effective_from)) {
      return Promise.reject(new ApiError(409, 'conflict', 'Ya hay umbrales registrados en esa fecha.'));
    }
    const now = nowIso();
    const created: ThresholdOut = {
      id: uuid(),
      effective_from: body.effective_from,
      ftp_w: body.ftp_w ?? null,
      cycling_lthr_bpm: body.cycling_lthr_bpm ?? null,
      running_lthr_bpm: body.running_lthr_bpm ?? null,
      legacy_lthr_bpm: null,
      hr_max_bpm: body.hr_max_bpm ?? null,
      hr_rest_bpm: body.hr_rest_bpm ?? null,
      threshold_pace_s_per_km: body.threshold_pace_s_per_km ?? null,
      vo2max: body.vo2max ?? null,
      weight_kg: body.weight_kg ?? null,
      source: body.source ?? 'manual',
      notes: body.notes ?? null,
      ftp_proposal_id: null,
      created_at: now,
      updated_at: now,
    };
    db.thresholds.push(created);
    return delay(created);
  },

  getAvailability: () => delay(db.availability),

  replaceAvailability(body: WeekAvailability) {
    db.availability = clone(body);
    return delay(db.availability);
  },

  listEvents(from: string, to: string) {
    // Solapamiento por días: [start, end ?? start] ∩ [from, to].
    const events = db.events
      .filter((e) => {
        const start = e.start_at.slice(0, 10);
        const end = (e.end_at ?? e.start_at).slice(0, 10);
        return start <= to && end >= from;
      })
      .sort((a, b) => a.start_at.localeCompare(b.start_at));
    return delay(events);
  },

  createEvent(body: CalendarEventCreate) {
    const created = eventFromCreate(body);
    db.events.push(created);
    return delay(created);
  },

  updateEvent(id: string, patch: CalendarEventPatch) {
    const index = db.events.findIndex((e) => e.id === id);
    if (index < 0) return Promise.reject(notFound());
    const current = db.events[index];
    const { race: racePatch, ...rest } = patch;
    const next: CalendarEventOut = { ...current, updated_at: nowIso() };
    for (const [key, value] of Object.entries(rest)) {
      if (value === undefined) continue;
      if (value === null && key !== 'end_at' && key !== 'notes') continue;
      (next as Record<string, unknown>)[key] = value;
    }
    if (next.kind !== 'race') {
      next.race = null;
    } else {
      const base = next.race ?? raceFromCreate(null);
      next.race = { ...base };
      for (const [key, value] of Object.entries(racePatch ?? {})) {
        if (value === undefined) continue;
        if (value === null && (key === 'priority' || key === 'enrichment_status')) continue;
        (next.race as Record<string, unknown>)[key] = value;
      }
    }
    if (next.end_at && next.end_at < next.start_at) {
      return Promise.reject(new ApiError(409, 'conflict', 'La fecha de fin es anterior a la de inicio.'));
    }
    db.events[index] = next;
    return delay(next);
  },

  deleteEvent(id: string) {
    const before = db.events.length;
    db.events = db.events.filter((e) => e.id !== id);
    if (db.events.length === before) return Promise.reject(notFound());
    return delay(undefined);
  },
};
