// Presentación de los eventos del calendario: icono por tipo, días que ocupa y textos de resumen.
import type { CalendarEventOut, EventKind } from '../api/types';
import type { AgendaEntry } from './Agenda';
import { addDays } from './dates';
import { localDay, localTime } from './calendarDates';
import type { IconName } from './Icon';
import { EVENT_KIND_LABELS, RACE_DISCIPLINE_LABELS } from './labels';

/** Un icono por tipo de evento; la carrera lleva su bandera. */
export const EVENT_KIND_ICONS: Record<EventKind, IconName> = {
  race: 'race',
  social: 'eventSocial',
  travel: 'eventTravel',
  health: 'eventHealth',
  personal: 'eventPersonal',
  unavailable: 'eventUnavailable',
};

/** Días locales (YYYY-MM-DD) que ocupa el evento, de inicio a fin. */
export function eventDays(event: CalendarEventOut): string[] {
  const start = localDay(event.start_at);
  const end = event.end_at ? localDay(event.end_at) : start;
  const days: string[] = [];
  for (let d = start; d <= end && days.length < 366; d = addDays(d, 1)) days.push(d);
  return days;
}

/** Eventos de cada día de `days`, en el orden en que llegan de la API. */
export function eventsByDay(events: CalendarEventOut[], days: string[]): Record<string, CalendarEventOut[]> {
  const map: Record<string, CalendarEventOut[]> = Object.fromEntries(days.map((d) => [d, []]));
  for (const event of events) {
    for (const day of eventDays(event)) map[day]?.push(event);
  }
  return map;
}

export function formatKm(meters: number): string {
  return `${(meters / 1000).toLocaleString('es-ES', { maximumFractionDigits: 1 })} km`;
}

export function formatMeters(meters: number): string {
  return `${meters.toLocaleString('es-ES')} m`;
}

/** «Carrera · Gravel · 83 km · 1250 m+ · prioridad A», sin los datos que falten. */
export function raceSummary(event: CalendarEventOut, withKind = true): string {
  const race = event.race;
  return [
    withKind ? EVENT_KIND_LABELS[event.kind] : null,
    race?.discipline ? RACE_DISCIPLINE_LABELS[race.discipline] : null,
    race?.distance_m != null ? formatKm(race.distance_m) : null,
    race?.ascent_m != null ? `${formatMeters(race.ascent_m)}+` : null,
    race ? `prioridad ${race.priority}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

/** Subtítulo de un evento en una lista de un día: hora (si la tiene) y tipo o datos de carrera. */
export function eventSubtitle(event: CalendarEventOut): string {
  const time = event.all_day ? null : localTime(event.start_at);
  const detail = event.kind === 'race' ? raceSummary(event) : EVENT_KIND_LABELS[event.kind];
  return [time, detail].filter(Boolean).join(' · ');
}

/** Elemento de `Agenda` para un evento (la clave es el id del evento). */
export function toAgendaEntry(event: CalendarEventOut, subtitle = eventSubtitle(event)): AgendaEntry {
  return { key: event.id, title: event.title, subtitle, icon: EVENT_KIND_ICONS[event.kind], highlight: event.kind === 'race' };
}
