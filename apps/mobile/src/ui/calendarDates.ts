// Fechas de las vistas de calendario (Hoy y Plan): semanas de lunes a domingo, rejilla de mes y
// textos. Sólo formato y aritmética de calendario; ningún cálculo de métricas.
import { addDays, isoToLocalParts, todayIsoDate, toIsoDate } from './dates';

const WEEKDAYS_SHORT = ['LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM'];
const WEEKDAYS_LETTER = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
const WEEKDAYS_LONG = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MONTHS_SHORT = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

function parts(isoDate: string): { y: number; m: number; d: number } {
  const [y, m, d] = isoDate.slice(0, 10).split('-').map(Number);
  return { y, m: m - 1, d };
}

/** Día de la semana con el lunes como 0. */
export function weekdayIndex(isoDate: string): number {
  const { y, m, d } = parts(isoDate);
  return (new Date(y, m, d).getDay() + 6) % 7;
}

export function startOfWeek(isoDate: string): string {
  return addDays(isoDate, -weekdayIndex(isoDate));
}

/** Los siete días (YYYY-MM-DD) de la semana que empieza en `monday`. */
export function weekDays(monday: string): string[] {
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
}

/** Primer día del mes de `isoDate`. */
export function startOfMonth(isoDate: string): string {
  const { y, m } = parts(isoDate);
  return toIsoDate(new Date(y, m, 1));
}

export function addMonths(monthStart: string, months: number): string {
  const { y, m } = parts(monthStart);
  return toIsoDate(new Date(y, m + months, 1));
}

/** Celdas de la rejilla del mes: semanas completas de lunes a domingo. */
export function monthGridDays(monthStart: string): string[] {
  const { y, m } = parts(monthStart);
  const last = toIsoDate(new Date(y, m + 1, 0));
  const first = startOfWeek(monthStart);
  const end = addDays(startOfWeek(last), 6);
  const days: string[] = [];
  for (let d = first; d <= end; d = addDays(d, 1)) days.push(d);
  return days;
}

export function isSameMonth(isoDate: string, monthStart: string): boolean {
  return isoDate.slice(0, 7) === monthStart.slice(0, 7);
}

export function dayOfMonth(isoDate: string): number {
  return parts(isoDate).d;
}

/** «LUN». */
export function weekdayShort(isoDate: string): string {
  return WEEKDAYS_SHORT[weekdayIndex(isoDate)];
}

/** «L», «M», «X»… de lunes a domingo. */
export const WEEKDAY_LETTERS = WEEKDAYS_LETTER;

/** «Martes 17 nov». */
export function longDayLabel(isoDate: string): string {
  const { m, d } = parts(isoDate);
  return `${capitalize(WEEKDAYS_LONG[weekdayIndex(isoDate)])} ${d} ${MONTHS_SHORT[m]}`;
}

/** «Martes 17». */
export function dayLabel(isoDate: string): string {
  return `${capitalize(WEEKDAYS_LONG[weekdayIndex(isoDate)])} ${parts(isoDate).d}`;
}

/** «16 – 22 nov» o «28 nov – 4 dic». */
export function weekRangeLabel(monday: string): string {
  const sunday = addDays(monday, 6);
  const a = parts(monday);
  const b = parts(sunday);
  const year = b.y !== parts(todayIsoDate()).y ? ` ${b.y}` : '';
  return a.m === b.m
    ? `${a.d} – ${b.d} ${MONTHS_SHORT[b.m]}${year}`
    : `${a.d} ${MONTHS_SHORT[a.m]} – ${b.d} ${MONTHS_SHORT[b.m]}${year}`;
}

/** «Noviembre 2026». */
export function monthLabel(monthStart: string): string {
  const { y, m } = parts(monthStart);
  return `${capitalize(MONTHS[m])} ${y}`;
}

/** Fecha local (YYYY-MM-DD) de un instante ISO. */
export function localDay(iso: string): string {
  return isoToLocalParts(iso).date;
}

/** Hora local «HH:MM» de un instante ISO. */
export function localTime(iso: string): string {
  return isoToLocalParts(iso).time;
}

/** Días naturales desde `from` hasta `to` (YYYY-MM-DD). */
export function daysBetween(from: string, to: string): number {
  const a = parts(from);
  const b = parts(to);
  return Math.round((new Date(b.y, b.m, b.d).getTime() - new Date(a.y, a.m, a.d).getTime()) / 86_400_000);
}
