/** Serie de forma: carga diaria y CTL/ATL/TSB (`GET /v1/athlete/fitness`, #17). */
import { request, withMock } from './http';
import { contractExamples } from './contractExamples.generated';
import type { components } from './schema';

export type FitnessSeriesOut = components['schemas']['FitnessSeriesOut'];
export type FitnessDayOut = components['schemas']['FitnessDayOut'];

/** Datos de prueba: el ejemplo del contrato tal cual (la app nunca genera ni calcula la serie). */
function mockSeries(): Promise<FitnessSeriesOut> {
  const example = contractExamples.FitnessSeriesOut?.[0] as FitnessSeriesOut | undefined;
  return new Promise((resolve) => setTimeout(() => resolve(JSON.parse(JSON.stringify(example ?? { days: [], from: '', to: '' }))), 150));
}

export const fitnessApi = {
  /** Un elemento por día de `[from, to]` (fechas YYYY-MM-DD, ambas incluidas; máximo 366 días). */
  getSeries: (from: string, to: string) =>
    withMock(() => request<FitnessSeriesOut>('GET', '/v1/athlete/fitness', { query: { from, to } }), mockSeries),
};
