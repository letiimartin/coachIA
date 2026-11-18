/** Cliente de los endpoints de perfil, umbrales, disponibilidad y calendario (contrato de #10). */
import { request, withMock } from './http';
import { mockApi } from './mock';
import type {
  CalendarEventCreate,
  CalendarEventOut,
  CalendarEventPatch,
  CurrentThresholdOut,
  FitnessSeriesOut,
  ProfileOut,
  ProfilePatch,
  ThresholdCreate,
  ThresholdOut,
  WeekAvailability,
} from './types';

export const athleteApi = {
  getProfile: () => withMock(() => request<ProfileOut>('GET', '/v1/athlete/profile'), mockApi.getProfile),

  updateProfile: (patch: ProfilePatch) =>
    withMock(
      () => request<ProfileOut>('PATCH', '/v1/athlete/profile', { body: patch }),
      () => mockApi.updateProfile(patch),
    ),

  listThresholds: () =>
    withMock(() => request<ThresholdOut[]>('GET', '/v1/athlete/thresholds'), mockApi.listThresholds),

  /** Umbral vigente y sus zonas (calculadas por la API). Lanza ApiError 404 si no hay ninguno. */
  getCurrentThreshold: (on?: string) =>
    withMock(
      () => request<CurrentThresholdOut>('GET', '/v1/athlete/thresholds/current', { query: { on } }),
      () => mockApi.getCurrentThreshold(on),
    ),

  createThreshold: (body: ThresholdCreate) =>
    withMock(
      () => request<ThresholdOut>('POST', '/v1/athlete/thresholds', { body }),
      () => mockApi.createThreshold(body),
    ),

  /** Carga diaria y CTL/ATL/TSB de cada día de `[from, to]` (calculadas por la API; máx. 366 días). */
  getFitness: (from: string, to: string) =>
    withMock(
      () => request<FitnessSeriesOut>('GET', '/v1/athlete/fitness', { query: { from, to } }),
      mockApi.getFitness,
    ),

  getAvailability: () =>
    withMock(() => request<WeekAvailability>('GET', '/v1/athlete/availability'), mockApi.getAvailability),

  replaceAvailability: (body: WeekAvailability) =>
    withMock(
      () => request<WeekAvailability>('PUT', '/v1/athlete/availability', { body }),
      () => mockApi.replaceAvailability(body),
    ),
};

export const calendarApi = {
  /** Eventos que se solapan con `[from, to]` (fechas YYYY-MM-DD, ambas incluidas). */
  listEvents: (from: string, to: string) =>
    withMock(
      () => request<CalendarEventOut[]>('GET', '/v1/calendar/events', { query: { from, to } }),
      () => mockApi.listEvents(from, to),
    ),

  createEvent: (body: CalendarEventCreate) =>
    withMock(
      () => request<CalendarEventOut>('POST', '/v1/calendar/events', { body }),
      () => mockApi.createEvent(body),
    ),

  updateEvent: (id: string, patch: CalendarEventPatch) =>
    withMock(
      () => request<CalendarEventOut>('PATCH', `/v1/calendar/events/${encodeURIComponent(id)}`, { body: patch }),
      () => mockApi.updateEvent(id, patch),
    ),

  deleteEvent: (id: string) =>
    withMock(
      () => request<void>('DELETE', `/v1/calendar/events/${encodeURIComponent(id)}`),
      () => mockApi.deleteEvent(id),
    ),
};
