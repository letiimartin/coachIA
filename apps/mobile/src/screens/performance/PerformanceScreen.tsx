/**
 * Pestaña Rendimiento (propuesta v3, #25): cifras de forma con su variación, gráfica de forma con
 * selector de periodo (`GET /v1/athlete/fitness`), el bloque de fuerza separado de la forma (#33) y
 * estados vacíos para lo que aún no tiene endpoint (volumen, tiempo por zonas y actividades, fase 2).
 */
import React, { useCallback, useState } from 'react';
import { Text } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { fitnessApi, type FitnessDayOut } from '../../api/fitnessApi';
import { Loading, Screen, SegmentedTabs, Section, styles } from '../../ui/components';
import { addDays, todayIsoDate } from '../../ui/dates';
import { FitnessChart } from '../../ui/FitnessChart';
import { Row, RowGroup } from '../../ui/Row';
import { StatStrip, type Stat } from '../../ui/StatStrip';
import { useFocusLoad } from '../../ui/useAsync';
import { zoneModelFor } from '../../ui/zoneModel';
import { StrengthBlock } from './StrengthBlock';

type Props = { navigation: NavigationProp<ParamListBase> };

type Period = '7d' | '6w' | '90d' | 'year';

const PERIODS: { value: Period; label: string; days: number; since: string }[] = [
  { value: '7d', label: '7 d', days: 7, since: 'en 7 d' },
  { value: '6w', label: '6 sem', days: 42, since: 'en 6 sem' },
  { value: '90d', label: '90 d', days: 90, since: 'en 90 d' },
  { value: 'year', label: 'Año', days: 365, since: 'en un año' },
];

/** Cifra entera con signo menos tipográfico (sin «−0» al redondear valores como −0,3). */
function number(v: number): string {
  const n = Math.round(v);
  return n < 0 ? `−${Math.abs(n)}` : String(n);
}

/**
 * Variación entre el primer y el último día que devuelve la API para el periodo. Es una resta de
 * dos valores de la serie para mostrarla, no una métrica nueva.
 */
function change(days: FitnessDayOut[], key: 'ctl' | 'atl' | 'tsb', since: string): string | null {
  if (days.length < 2) return null;
  const delta = Math.round(days[days.length - 1][key] - days[0][key]);
  if (delta === 0) return `= ${since}`;
  return `${delta > 0 ? '▲' : '▼'} ${Math.abs(delta)} ${since}`;
}

export default function PerformanceScreen({ navigation }: Props) {
  const [period, setPeriod] = useState<Period>('6w');
  const spec = PERIODS.find((p) => p.value === period) ?? PERIODS[1];
  const today = todayIsoDate();
  const from = addDays(today, -(spec.days - 1));
  const load = useCallback(() => fitnessApi.getSeries(from, today), [from, today]);
  const { data, loading, error, setError, reload } = useFocusLoad(load);

  const days = data?.days ?? [];
  const last = days[days.length - 1];
  const empty = days.length === 0 || days.every((d) => d.ctl === 0 && d.atl === 0);
  const isToday = last?.day === today;
  const stats: Stat[] = last
    ? [
        { label: 'Forma', value: number(last.ctl), caption: 'CTL', note: change(days, 'ctl', spec.since) },
        { label: 'Fatiga', value: number(last.atl), caption: 'ATL', note: change(days, 'atl', spec.since) },
        { label: 'Balance', value: number(last.tsb), caption: 'TSB', note: change(days, 'tsb', spec.since) },
      ]
    : [];
  const power = zoneModelFor('cycling');

  return (
    <Screen title="Rendimiento" error={error} onDismissError={() => setError(null)} refreshing={loading && !!data} onRefresh={reload}>
      <SegmentedTabs options={PERIODS} value={period} onChange={setPeriod} />

      {loading && !data ? <Loading /> : null}
      {data && empty ? (
        <Section title="Forma">
          <Text style={styles.muted}>
            Todavía no hay actividades con carga en este periodo. Cuando sincronices Wahoo, aquí verás tu forma, fatiga y balance.
          </Text>
        </Section>
      ) : null}
      {data && !empty ? (
        <>
          <StatStrip stats={stats} size="large" />
          <FitnessChart days={days} endLabel={isToday ? 'HOY' : undefined} />
        </>
      ) : null}

      <StrengthBlock
        from={from}
        to={today}
        onOpenExercise={(item) => navigation.navigate('ExerciseProgress', { id: item.exercise.id, name: item.exercise.name })}
        onOpenAll={() => navigation.navigate('StrengthExercises')}
      />

      <Section title="Volumen">
        <Text style={styles.muted}>Distancia, tiempo, desnivel y carga frente al mes anterior. Disponible cuando la API exponga las actividades.</Text>
      </Section>

      <Section title="Tiempo por zonas" right={power ? <Text style={styles.sectionLabel}>{power.label}</Text> : null}>
        <Text style={styles.muted}>Reparto del tiempo por zonas de cada disciplina. Disponible cuando la API lo calcule.</Text>
      </Section>

      <RowGroup>
        <Row icon="activities" title="Actividades" subtitle="Disponible cuando la API exponga las actividades sincronizadas" />
        <Row icon="sync" title="Wahoo" subtitle="Conectar o sincronizar" onPress={() => navigation.navigate('Integrations')} />
      </RowGroup>
    </Screen>
  );
}
