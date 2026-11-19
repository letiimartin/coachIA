/**
 * Progresión de un ejercicio (#33), con la composición de la v3: cifras de la última sesión en tira,
 * gráfica a todo el ancho (peso máximo y volumen por sesión) e historial en filas con filete. Todo
 * viene de `GET /v1/strength/exercises/{id}/progress`: la app no calcula nada.
 */
import React, { useCallback } from 'react';
import { Text } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { strengthProgressApi } from '../../api/strengthProgressApi';
import type { RootStackParamList } from '../../navigation/types';
import { Loading, Screen, Section, styles } from '../../ui/components';
import { ProgressChart } from '../../ui/ProgressChart';
import { Row, RowGroup } from '../../ui/Row';
import { StatStrip, type Stat } from '../../ui/StatStrip';
import { useFocusLoad } from '../../ui/useAsync';
import { formatWeight } from '../strength/strengthSets';
import { bestSetLabel, chartSpec, formatInt, sessionDayLabel, setsLabel } from './strengthFormat';

type Props = NativeStackScreenProps<RootStackParamList, 'ExerciseProgress'>;

export default function ExerciseProgressScreen({ navigation, route }: Props) {
  const { id, name } = route.params;
  const load = useCallback(() => strengthProgressApi.exercise(id), [id]);
  const { data, loading, error, setError, reload } = useFocusLoad(load);

  const sessions = data?.sessions ?? [];
  const last = sessions[sessions.length - 1];
  const mode = data?.exercise.mode ?? 'reps';
  const stats: Stat[] = last
    ? [
        last.max_weight_kg != null
          ? { label: 'Peso máx.', value: formatWeight(last.max_weight_kg), caption: 'kg' }
          : mode === 'seconds'
            ? { label: 'Mejor serie', value: String(last.best_set_seconds ?? '–'), caption: 's' }
            : { label: 'Mejor serie', value: String(last.best_set_reps ?? '–'), caption: 'reps' },
        last.volume_kg != null
          ? { label: 'Volumen', value: formatInt(last.volume_kg), caption: 'kg' }
          : mode === 'seconds'
            ? { label: 'Total', value: String(last.total_seconds ?? '–'), caption: 's' }
            : { label: 'Total', value: String(last.total_reps ?? '–'), caption: 'reps' },
        { label: 'Sesiones', value: String(sessions.length), caption: 'completadas' },
      ]
    : [];
  const chart = data ? chartSpec(sessions, mode) : null;

  return (
    <Screen
      title={data?.exercise.name ?? name ?? 'Ejercicio'}
      eyebrow="Fuerza · progresión"
      onBack={() => navigation.goBack()}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={reload}
    >
      {loading && !data ? <Loading /> : null}
      {data && sessions.length === 0 ? (
        <Text style={styles.muted}>Todavía no has completado ninguna sesión con este ejercicio.</Text>
      ) : null}
      {last && chart ? (
        <>
          <Section title={`Última sesión · ${sessionDayLabel(last)}`}>
            <StatStrip stats={stats} size="large" />
          </Section>
          {sessions.length > 1 ? <ProgressChart points={chart.points} lineLabel={chart.lineLabel} barLabel={chart.barLabel} /> : null}
          <RowGroup title="Historial">
            {[...sessions].reverse().map((s) => (
              <Row
                key={s.activity_id}
                title={sessionDayLabel(s)}
                subtitle={[setsLabel(s), bestSetLabel(s) ? `mejor ${bestSetLabel(s)}` : null].filter(Boolean).join(' · ')}
                value={s.volume_kg != null ? `${formatInt(s.volume_kg)} kg` : undefined}
                onPress={s.planned_workout_id ? () => navigation.navigate('StrengthSession', { id: s.planned_workout_id as string }) : undefined}
              />
            ))}
          </RowGroup>
        </>
      ) : null}
    </Screen>
  );
}
