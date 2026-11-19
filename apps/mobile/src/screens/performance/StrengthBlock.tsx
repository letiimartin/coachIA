/**
 * Bloque «Fuerza esta semana» de Rendimiento (#33), debajo de la forma y separado de ella por un
 * filete: la carga de fuerza (`session_rpe`) no es TSS y nunca se suma a CTL/ATL/TSB.
 *
 * - Cifras de la semana en curso (sesiones, tiempo y carga) con la semana anterior debajo.
 * - Carga por semana del periodo elegido, a todo el ancho.
 * - Últimos ejercicios hechos, que llevan a su progresión.
 *
 * Todo viene de la API (`GET /v1/strength/weekly` y `GET /v1/strength/progress`).
 */
import React, { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { strengthProgressApi } from '../../api/strengthProgressApi';
import type { PerformedExerciseOut, StrengthWeekOut } from '../../api/types';
import { startOfWeek } from '../../ui/calendarDates';
import { ErrorBanner, Section, styles as ui } from '../../ui/components';
import { Row, RowGroup } from '../../ui/Row';
import { StatStrip, type Stat } from '../../ui/StatStrip';
import { StrengthWeekChart, shortDate } from '../../ui/StrengthWeekChart';
import { colors, lines, spacing, typography } from '../../ui/theme';
import { addDays } from '../../ui/dates';
import { useFocusLoad } from '../../ui/useAsync';
import { formatWeight } from '../strength/strengthSets';
import { formatHours, formatInt } from './strengthFormat';

/** Ejercicios que se muestran en Rendimiento; el resto, en la pantalla de ejercicios. */
const RECENT_EXERCISES = 5;

type Props = {
  from: string;
  to: string;
  onOpenExercise: (item: PerformedExerciseOut) => void;
  onOpenAll: () => void;
};

/** Fila de un ejercicio hecho: nombre, sesiones y última fecha, y el peso máximo de la última sesión. */
export function exerciseRowProps(item: PerformedExerciseOut) {
  const sessions = item.sessions === 1 ? '1 sesión' : `${item.sessions} sesiones`;
  return {
    title: item.exercise.name,
    subtitle: `${sessions} · última ${shortDate(item.last_performed_on).toLowerCase()}`,
    value: item.last_max_weight_kg != null ? `${formatWeight(item.last_max_weight_kg)} kg` : undefined,
  };
}

function weekStats(current: StrengthWeekOut, previous: StrengthWeekOut | undefined): Stat[] {
  const before = (text: string) => (previous ? `ant. ${text}` : null);
  const withoutLoad = current.sessions_without_load;
  return [
    { label: 'Sesiones', value: String(current.sessions), caption: 'de fuerza', note: before(String(previous?.sessions ?? 0)) },
    { label: 'Tiempo', value: formatHours(current.duration_s), caption: 'horas', note: before(formatHours(previous?.duration_s ?? 0)) },
    {
      label: 'Carga',
      value: formatInt(current.load),
      caption: withoutLoad > 0 ? `sRPE · ${withoutLoad} sin RPE` : 'sRPE',
      note: before(formatInt(previous?.load ?? 0)),
    },
  ];
}

export function StrengthBlock({ from, to, onOpenExercise, onOpenAll }: Props) {
  const currentWeek = startOfWeek(to);
  // Siempre con la semana anterior, para comparar aunque el periodo sea de 7 días.
  const previousWeek = addDays(currentWeek, -7);
  const weeklyFrom = from < previousWeek ? from : previousWeek;
  const load = useCallback(
    () => Promise.all([strengthProgressApi.weekly(weeklyFrom, to), strengthProgressApi.performed()]),
    [weeklyFrom, to],
  );
  const { data, error, setError } = useFocusLoad(load);
  const [weekly, performed] = data ?? [null, null];

  const weeks = weekly?.weeks ?? [];
  const current = weeks.find((w) => w.week_start === currentWeek);
  const previous = weeks.find((w) => w.week_start === previousWeek);
  // La gráfica cubre el periodo elegido (la semana anterior sólo se pide para comparar).
  const chartWeeks = weeks.filter((w) => w.week_start >= startOfWeek(from));
  const anyStrength = chartWeeks.some((w) => w.sessions > 0);

  return (
    <View style={styles.block}>
      <Section title="Fuerza esta semana" right={<Text style={ui.sectionLabel}>No suma a la forma</Text>}>
        {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}
        {current ? <StatStrip stats={weekStats(current, previous)} /> : null}
        {weekly && !anyStrength ? (
          <Text style={ui.muted}>Sin sesiones de fuerza en este periodo. Al completar una, aquí verás sus sesiones, tiempo y carga.</Text>
        ) : null}
      </Section>
      {weekly && anyStrength && chartWeeks.length > 1 ? (
        <View style={styles.chart}>
          <Text style={styles.chartLabel}>Carga sRPE por semana</Text>
          <StrengthWeekChart weeks={chartWeeks} currentWeek={currentWeek} />
        </View>
      ) : null}
      {performed && performed.length > 0 ? (
        <RowGroup title="Progresión por ejercicio">
          {performed.slice(0, RECENT_EXERCISES).map((item) => (
            <Row key={item.exercise.id} {...exerciseRowProps(item)} onPress={() => onOpenExercise(item)} />
          ))}
          {performed.length > RECENT_EXERCISES ? <Row title="Todos los ejercicios" value={String(performed.length)} onPress={onOpenAll} /> : null}
        </RowGroup>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  block: { gap: spacing.xl, paddingTop: spacing.xl, borderTopWidth: lines.hairline, borderTopColor: colors.separatorStrong },
  chart: { gap: spacing.sm },
  chartLabel: { ...typography.caption, color: colors.textSecondary },
});
