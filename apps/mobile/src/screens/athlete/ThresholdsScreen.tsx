import React from 'react';
import { Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { athleteApi } from '../../api/athleteApi';
import { ApiError } from '../../api/errors';
import { useUsingMock } from '../../api/mockStatus';
import type { CurrentThresholdOut, ThresholdOut, ZoneOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Card, InfoRow, Loading, Screen, styles } from '../../ui/components';
import { formatDate, formatPace } from '../../ui/dates';
import { unassignedLegacyLthr } from '../../ui/forms';
import { THRESHOLD_SOURCE_LABELS } from '../../ui/labels';
import { colors } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = NativeStackScreenProps<RootStackParamList, 'Thresholds'>;

async function loadAll(): Promise<{ current: CurrentThresholdOut | null; history: ThresholdOut[] }> {
  const [current, history] = await Promise.all([
    athleteApi.getCurrentThreshold().catch((e: unknown) => {
      // 404: todavía no hay ningún umbral registrado.
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }),
    athleteApi.listThresholds(),
  ]);
  return { current, history };
}

function ThresholdValues({ t }: { t: ThresholdOut }) {
  const rows: [string, string | null][] = [
    ['FTP', t.ftp_w != null ? `${t.ftp_w} W` : null],
    ['FC umbral en ciclismo', t.cycling_lthr_bpm != null ? `${t.cycling_lthr_bpm} ppm` : null],
    ['FC umbral en carrera y trail', t.running_lthr_bpm != null ? `${t.running_lthr_bpm} ppm` : null],
    ['FC umbral antigua (sin asignar)', unassignedLegacyLthr(t) != null ? `${unassignedLegacyLthr(t)} ppm` : null],
    ['FC máxima', t.hr_max_bpm != null ? `${t.hr_max_bpm} ppm` : null],
    ['FC en reposo', t.hr_rest_bpm != null ? `${t.hr_rest_bpm} ppm` : null],
    ['Ritmo umbral', t.threshold_pace_s_per_km != null ? `${formatPace(t.threshold_pace_s_per_km)} /km` : null],
    ['VO2máx', t.vo2max != null ? `${t.vo2max} ml/kg/min` : null],
    ['Peso', t.weight_kg != null ? `${t.weight_kg} kg` : null],
  ];
  return (
    <>
      {rows
        .filter((r): r is [string, string] => r[1] !== null)
        .map(([label, value]) => (
          <InfoRow key={label} label={label} value={value} />
        ))}
      <InfoRow label="Origen" value={THRESHOLD_SOURCE_LABELS[t.source]} />
      {t.notes ? <Text style={styles.muted}>{t.notes}</Text> : null}
    </>
  );
}

function ZonesTable({ title, unit, zones }: { title: string; unit: string; zones: ZoneOut[] | null }) {
  if (!zones) return null;
  return (
    <Card title={title}>
      {zones.map((z) => (
        <View key={z.code} style={{ flexDirection: 'row', gap: 8 }}>
          <Text style={[styles.text, { width: 40, color: colors.primary, fontWeight: '700' }]}>{z.code}</Text>
          <Text style={[styles.text, { flex: 1 }]}>{z.name}</Text>
          <Text style={styles.muted}>
            {z.high == null ? `> ${Math.round(z.low)}` : `${Math.round(z.low)}–${Math.round(z.high)}`} {unit}
          </Text>
        </View>
      ))}
    </Card>
  );
}

export default function ThresholdsScreen({ navigation }: Props) {
  const { data, loading, error, setError, reload } = useFocusLoad(loadAll);
  const usingMock = useUsingMock();
  const current = data?.current ?? null;
  const zones = current?.zones;
  const hasZones = !!(zones?.power || zones?.hr_cycling || zones?.hr_running);

  return (
    <Screen error={error} onDismissError={() => setError(null)} title="Umbrales y zonas" onBack={navigation.goBack} refreshing={loading && !!data} onRefresh={reload}>
      {loading && !data ? <Loading /> : null}

      {data ? (
        <>
          <Button title="Nuevo umbral" onPress={() => navigation.navigate('ThresholdForm', { current: current?.threshold ?? null })} />

          {current ? (
            <Card title={`Vigente desde ${formatDate(current.threshold.effective_from)}`}>
              <ThresholdValues t={current.threshold} />
            </Card>
          ) : (
            <Card>
              <Text style={styles.muted}>Todavía no hay umbrales. Registra el primero para calcular tus zonas.</Text>
            </Card>
          )}

          {current && !hasZones ? (
            <Text style={styles.muted}>
              {usingMock
                ? 'Datos de prueba: sólo el umbral de ejemplo del contrato trae zonas. La app no las calcula; lo hará la API.'
                : 'No hay zonas: faltan el FTP o la FC umbral en el umbral vigente.'}
            </Text>
          ) : null}
          <ZonesTable title="Zonas de potencia" unit="W" zones={zones?.power ?? null} />
          <ZonesTable title="Zonas de FC · ciclismo" unit="ppm" zones={zones?.hr_cycling ?? null} />
          <ZonesTable title="Zonas de FC · carrera" unit="ppm" zones={zones?.hr_running ?? null} />

          {data.history.length > 0 ? (
            <Card title="Histórico">
              {data.history.map((t) => (
                <View key={t.id} style={{ paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.border, gap: 4 }}>
                  <Text style={[styles.text, { fontWeight: '700' }]}>
                    Desde {formatDate(t.effective_from)}
                    {t.id === current?.threshold.id ? ' · vigente' : ''}
                  </Text>
                  <ThresholdValues t={t} />
                </View>
              ))}
            </Card>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}
