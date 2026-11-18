// Utilidades de fecha para formularios y listas (sólo formato; ningún cálculo de métricas).

const pad = (n: number) => String(n).padStart(2, '0');

/** Fecha local en formato YYYY-MM-DD. */
export function toIsoDate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function todayIsoDate(): string {
  return toIsoDate(new Date());
}

export function addDays(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  return toIsoDate(new Date(y, m - 1, d + days));
}

export function isValidIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [y, m, d] = value.split('-').map(Number);
  const date = new Date(y, m - 1, d);
  return date.getFullYear() === y && date.getMonth() === m - 1 && date.getDate() === d;
}

export function isValidTime(value: string): boolean {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(value);
}

/** Fecha y hora locales a ISO 8601 con desfase (la API exige zona horaria). */
export function localDateTimeToIso(isoDate: string, time: string): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  const [hh, mm] = time.split(':').map(Number);
  const date = new Date(y, m - 1, d, hh, mm);
  const offset = -date.getTimezoneOffset();
  const sign = offset >= 0 ? '+' : '-';
  const abs = Math.abs(offset);
  return `${toIsoDate(date)}T${pad(hh)}:${pad(mm)}:00${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

/** Fecha (YYYY-MM-DD) y hora (HH:MM) locales de un instante ISO. */
export function isoToLocalParts(iso: string): { date: string; time: string } {
  const d = new Date(iso);
  return { date: toIsoDate(d), time: `${pad(d.getHours())}:${pad(d.getMinutes())}` };
}

export function formatDate(isoDate: string): string {
  const [y, m, d] = isoDate.slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatDateTime(iso: string, allDay: boolean): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  return allDay ? date : `${date}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Ritmo en s/km a "m:ss". */
export function formatPace(secondsPerKm: number | null | undefined): string {
  if (secondsPerKm == null) return '—';
  const total = Math.round(secondsPerKm);
  return `${Math.floor(total / 60)}:${pad(total % 60)}`;
}

/** "m:ss" (o segundos) a s/km. Devuelve null si está vacío y NaN si no es válido. */
export function parsePace(text: string): number | null {
  const value = text.trim();
  if (!value) return null;
  const match = /^(\d{1,2}):([0-5]\d)$/.exec(value);
  if (match) return Number(match[1]) * 60 + Number(match[2]);
  const seconds = Number(value.replace(',', '.'));
  return Number.isFinite(seconds) ? seconds : NaN;
}
