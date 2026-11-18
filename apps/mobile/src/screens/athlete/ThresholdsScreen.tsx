import React, { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { athleteApi } from '../../api/athleteApi';
import { ApiError } from '../../api/errors';
import { useUsingMock } from '../../api/mockStatus';
import type { CurrentThresholdOut, Sport, ThresholdOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, InfoRow, Loading, Screen, Section, SegmentedTabs, styles as ui } from '../../ui/components';
import { formatDate, formatPace } from '../../ui/dates';
import { unassignedLegacyLthr } from '../../ui/forms';
import { THRESHOLD_SOURCE_LABELS } from '../../ui/labels';
import { Row, RowGroup } from '../../ui/Row';
import { colors, fontSize, spacing, typography } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';
import { ZoneRuler } from '../../ui/ZoneRuler';
import { ZoneTable } from '../../ui/ZoneTable';
import { zoneModelFor, type ZoneModel } from '../../ui/zoneModel';

type Props = NativeStackScreenProps<RootStackParamList, 'Thresholds'>;

/** Disciplinas con pestaña, en el orden de la v3. `hr_cycling` y `hr_running` no se muestran. */
const SPORTS = ['cycling', 'running', 'trail_running'] as const satisfies readonly Sport[];
type TabSport = (typeof SPORTS)[number];

function modelFor(sport: TabSport): ZoneModel {
  const model = zoneModelFor(sport);
  if (!model) throw new Error(`Sin modelo de zonas para ${sport}`);
  return model;
}

const TABS = SPORTS.map((s) => ({ value: s, label: modelFor(s).sportLabel }));

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

const bpm = (v: number | null) => (v != null ? `${v} ppm` : null);

/** Valores del umbral que resume cada pestaña en el histórico. */
function summary(t: ThresholdOut, sport: TabSport): string {
  const parts =
    sport === 'cycling'
      ? [t.ftp_w != null ? `${t.ftp_w} W` : null, bpm(t.cycling_lthr_bpm)]
      : sport === 'running'
        ? [t.threshold_pace_s_per_km != null ? `${formatPace(t.threshold_pace_s_per_km)} /km` : null]
        : [bpm(t.running_lthr_bpm)];
  const shown = parts.filter(Boolean);
  return shown.length ? shown.join(' · ') : '—';
}

/** Resto de valores del umbral vigente (los que no son la referencia de la pestaña). */
function OtherValues({ t, model }: { t: ThresholdOut; model: ZoneModel }) {
  const legacy = unassignedLegacyLthr(t);
  const rows: [string, string | null, boolean][] = [
    ['FTP', t.ftp_w != null ? `${t.ftp_w} W` : null, model.key === 'power'],
    ['Ritmo umbral', t.threshold_pace_s_per_km != null ? `${formatPace(t.threshold_pace_s_per_km)} /km` : null, model.key === 'running_pace'],
    ['FC umbral en ciclismo', bpm(t.cycling_lthr_bpm), false],
    ['FC umbral en carrera y trail', bpm(t.running_lthr_bpm), model.key === 'trail_hr'],
    ['FC umbral antigua (sin asignar)', bpm(legacy), false],
    ['FC máxima', bpm(t.hr_max_bpm), false],
    ['FC en reposo', bpm(t.hr_rest_bpm), false],
    ['VO2máx', t.vo2max != null ? `${t.vo2max} ml/kg/min` : null, false],
    ['Peso', t.weight_kg != null ? `${t.weight_kg} kg` : null, false],
  ];
  return (
    <Section title="Resto del umbral vigente">
      <View>
        {rows
          .filter(([, value, hidden]) => value !== null && !hidden)
          .map(([label, value]) => (
            <InfoRow key={label} label={label} value={value} />
          ))}
        <InfoRow label="Origen" value={THRESHOLD_SOURCE_LABELS[t.source]} />
      </View>
      {legacy != null ? (
        <Text style={ui.muted}>La FC umbral antigua es anterior a la FC umbral por disciplina. Es sólo informativa y no se usa en las zonas.</Text>
      ) : null}
      {t.notes ? <Text style={ui.muted}>{t.notes}</Text> : null}
    </Section>
  );
}

function SportZones({ current, model, usingMock }: { current: CurrentThresholdOut; model: ZoneModel; usingMock: boolean }) {
  const t = current.threshold;
  const value = model.threshold(t);
  const zones = model.zones(current.zones);
  const title = `${model.thresholdLabel.charAt(0).toUpperCase()}${model.thresholdLabel.slice(1)} vigente`;

  return (
    <View style={local.block}>
      <View style={local.hero}>
        <View style={local.heroMain}>
          <Text style={local.label}>{title}</Text>
          {value != null ? (
            <Text style={local.value}>
              {model.format(value)}
              <Text style={local.unit}> {model.unit}</Text>
            </Text>
          ) : (
            <Text style={local.valueEmpty}>—</Text>
          )}
        </View>
        <Text style={local.since}>desde el {formatDate(t.effective_from)}</Text>
      </View>

      {zones ? (
        <>
          <View style={local.ruler}>
            <ZoneRuler zones={zones} threshold={value} model={model} />
            <Text style={ui.muted}>{model.basis} Para cambiarlas, registra un umbral nuevo.</Text>
          </View>
          <ZoneTable zones={zones} model={model} />
        </>
      ) : (
        <Text style={ui.muted}>
          {value == null
            ? `Sin zonas: el umbral vigente no tiene ${model.thresholdLabel}. Registra un umbral nuevo para verlas.`
            : usingMock
              ? 'Datos de prueba: sólo el umbral de ejemplo del contrato trae zonas. La app no las calcula; lo hará la API.'
              : 'La API no ha devuelto zonas para esta disciplina.'}
        </Text>
      )}
    </View>
  );
}

export default function ThresholdsScreen({ navigation }: Props) {
  const { data, loading, error, setError, reload } = useFocusLoad(loadAll);
  const usingMock = useUsingMock();
  const [sport, setSport] = useState<TabSport>('cycling');
  const model = modelFor(sport);
  const current = data?.current ?? null;
  const newThreshold = () => navigation.navigate('ThresholdForm', { current: current?.threshold ?? null });

  return (
    <Screen error={error} onDismissError={() => setError(null)} title="Umbrales y zonas" onBack={navigation.goBack} refreshing={loading && !!data} onRefresh={reload}>
      <SegmentedTabs options={TABS} value={sport} onChange={setSport} />

      {loading && !data ? <Loading /> : null}

      {data ? (
        <>
          {current ? (
            <SportZones current={current} model={model} usingMock={usingMock} />
          ) : (
            <Text style={ui.muted}>Todavía no hay umbrales. Registra el primero para calcular tus zonas.</Text>
          )}

          {data.history.length > 0 ? (
            <RowGroup title="Historial">
              {data.history.map((t) => (
                <Row
                  key={t.id}
                  title={formatDate(t.effective_from)}
                  subtitle={`${THRESHOLD_SOURCE_LABELS[t.source]}${t.id === current?.threshold.id ? ' · vigente' : ''}`}
                  value={summary(t, sport)}
                />
              ))}
            </RowGroup>
          ) : null}

          <Button title="Nuevo umbral" variant="secondary" onPress={newThreshold} />

          {current ? <OtherValues t={current.threshold} model={model} /> : null}
        </>
      ) : null}
    </Screen>
  );
}

const local = StyleSheet.create({
  block: { gap: spacing.lg },
  hero: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', gap: spacing.md },
  heroMain: { gap: spacing.xxs },
  label: { ...typography.label, color: colors.textSecondary },
  value: { ...typography.display, fontSize: fontSize.display + 10, lineHeight: 48, color: colors.text, fontVariant: ['tabular-nums'] },
  valueEmpty: { ...typography.display, color: colors.textDisabled },
  unit: { ...typography.heading, fontSize: fontSize.heading - 4, color: colors.textSecondary },
  since: { ...typography.caption, color: colors.textSecondary, textAlign: 'right', paddingBottom: spacing.xs },
  ruler: { gap: spacing.sm },
});
