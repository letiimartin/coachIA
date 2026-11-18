/**
 * Modelo de zonas de cada disciplina (#22, #25). Sólo **consulta** las zonas que devuelve la API en
 * `ZonesOut`: nunca calcula límites. Sirve para que toda la app use la misma referencia, la misma
 * unidad y el mismo color para cada deporte.
 *
 * - Ciclismo: potencia (`power`, W).
 * - Carrera: ritmo (`running_pace`, s/km en la API, min/km en la app).
 * - Trail: FC (`trail_hr`, ppm).
 *
 * `hr_cycling` y `hr_running` no se muestran en la app.
 */
import type { Sport, ZoneOut, ZonesOut } from '../api/types';
import { formatPace } from './dates';
import { zoneColors, type ZoneCode } from './theme';

/** Claves de `ZonesOut` que la app muestra. `running_pace` y `trail_hr` llegan con el contrato de #22. */
export type ZoneModelKey = 'power' | 'running_pace' | 'trail_hr';
export type ZoneMetric = 'power' | 'pace' | 'hr';

export type ZoneModel = {
  key: ZoneModelKey;
  metric: ZoneMetric;
  /** Nombre corto de la métrica (cabeceras: «Potencia», «Ritmo», «FC»). */
  label: string;
  /** Unidad tal como se muestra. */
  unit: string;
  /** Umbral de referencia (para textos como «230 W FTP»). */
  thresholdLabel: string;
  /** Zonas que devuelve la API para esta disciplina, o null si faltan el umbral o el modelo. */
  zones: (zones: ZonesOut | null | undefined) => ZoneOut[] | null;
  /** Formatea un valor de la API en la unidad de la disciplina (sin la unidad). */
  format: (value: number) => string;
};

/** Lee una clave de `ZonesOut` aunque el cliente generado aún no la tenga (contrato de #22). */
function read(key: ZoneModelKey) {
  return (zones: ZonesOut | null | undefined): ZoneOut[] | null => {
    if (!zones) return null;
    const list = (zones as Partial<Record<ZoneModelKey, ZoneOut[] | null>>)[key];
    return list ?? null;
  };
}

const integer = (value: number) => String(Math.round(value));

const MODELS: Record<ZoneModelKey, ZoneModel> = {
  power: { key: 'power', metric: 'power', label: 'Potencia', unit: 'W', thresholdLabel: 'FTP', zones: read('power'), format: integer },
  running_pace: {
    key: 'running_pace',
    metric: 'pace',
    label: 'Ritmo',
    unit: '/km',
    thresholdLabel: 'ritmo umbral',
    zones: read('running_pace'),
    format: (value) => formatPace(value),
  },
  trail_hr: { key: 'trail_hr', metric: 'hr', label: 'FC', unit: 'ppm', thresholdLabel: 'FC umbral', zones: read('trail_hr'), format: integer },
};

/** Disciplinas con modelo de zonas propio. El resto de deportes no tiene zonas en la app. */
const BY_SPORT: Partial<Record<Sport, ZoneModelKey>> = {
  cycling: 'power',
  running: 'running_pace',
  trail_running: 'trail_hr',
};

/** Modelo de zonas de un deporte, o null si ese deporte no tiene zonas en la app. */
export function zoneModelFor(sport: Sport): ZoneModel | null {
  const key = BY_SPORT[sport];
  return key ? MODELS[key] : null;
}

/** Color de una zona a partir de su código (Z1…Z7; las subzonas Z5a–Z5c usan el de Z5). */
export function zoneColor(code: string): string {
  const base = code.slice(0, 2) as ZoneCode;
  return zoneColors[base] ?? zoneColors.Z1;
}
