import React, { useState } from 'react';
import { Text } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { athleteApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import type { ThresholdCreate, ThresholdSource } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Section, Chips, Field, Screen, styles } from '../../ui/components';
import { formatPace, isValidIsoDate, parsePace, todayIsoDate } from '../../ui/dates';
import { numberToText, parseOptionalNumber, unassignedLegacyLthr } from '../../ui/forms';
import { options, THRESHOLD_SOURCE_LABELS } from '../../ui/labels';

type Props = NativeStackScreenProps<RootStackParamList, 'ThresholdForm'>;

type NumericKey = 'ftp_w' | 'cycling_lthr_bpm' | 'running_lthr_bpm' | 'hr_max_bpm' | 'hr_rest_bpm' | 'vo2max' | 'weight_kg';

/** Límites del contrato (ThresholdCreate). */
const NUMERIC_FIELDS: { key: NumericKey; label: string; min: number; max: number; integer: boolean; decimals: number }[] = [
  { key: 'ftp_w', label: 'FTP (W)', min: 50, max: 700, integer: true, decimals: 0 },
  { key: 'cycling_lthr_bpm', label: 'FC umbral en ciclismo (ppm)', min: 80, max: 230, integer: true, decimals: 0 },
  { key: 'running_lthr_bpm', label: 'FC umbral en carrera y trail (ppm)', min: 80, max: 230, integer: true, decimals: 0 },
  { key: 'hr_max_bpm', label: 'FC máxima (ppm)', min: 100, max: 240, integer: true, decimals: 0 },
  { key: 'hr_rest_bpm', label: 'FC en reposo (ppm)', min: 25, max: 120, integer: true, decimals: 0 },
  { key: 'vo2max', label: 'VO2máx (ml/kg/min)', min: 10, max: 100, integer: false, decimals: 1 },
  { key: 'weight_kg', label: 'Peso (kg)', min: 25, max: 250, integer: false, decimals: 2 },
];

export default function ThresholdFormScreen({ navigation, route }: Props) {
  const current = route.params?.current ?? null;
  // Precargado con el umbral vigente: el POST es una foto completa.
  const [values, setValues] = useState<Record<NumericKey, string>>(() => ({
    ftp_w: numberToText(current?.ftp_w),
    cycling_lthr_bpm: numberToText(current?.cycling_lthr_bpm),
    running_lthr_bpm: numberToText(current?.running_lthr_bpm),
    hr_max_bpm: numberToText(current?.hr_max_bpm),
    hr_rest_bpm: numberToText(current?.hr_rest_bpm),
    vo2max: numberToText(current?.vo2max),
    weight_kg: numberToText(current?.weight_kg),
  }));
  const [pace, setPace] = useState(current?.threshold_pace_s_per_km != null ? formatPace(current.threshold_pace_s_per_km) : '');
  const [effectiveFrom, setEffectiveFrom] = useState(todayIsoDate());
  const [source, setSource] = useState<ThresholdSource>('manual');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const build = (): ThresholdCreate | string => {
    if (!isValidIsoDate(effectiveFrom.trim())) return 'La fecha de vigencia debe tener el formato AAAA-MM-DD.';
    const body: ThresholdCreate = { effective_from: effectiveFrom.trim(), source, notes: notes.trim() || null };
    let any = false;
    for (const f of NUMERIC_FIELDS) {
      const n = parseOptionalNumber(values[f.key]);
      if (n === null) {
        body[f.key] = null;
        continue;
      }
      if (Number.isNaN(n) || n < f.min || n > f.max) return `${f.label}: debe estar entre ${f.min} y ${f.max}.`;
      if (f.integer && !Number.isInteger(n)) return `${f.label}: debe ser un número entero.`;
      const factor = 10 ** f.decimals;
      body[f.key] = Math.round(n * factor) / factor;
      any = true;
    }
    const p = parsePace(pace);
    if (p !== null) {
      if (Number.isNaN(p) || p < 120 || p > 1800) return 'Ritmo umbral: usa el formato m:ss por km (entre 2:00 y 30:00).';
      body.threshold_pace_s_per_km = Math.round(p * 10) / 10;
      any = true;
    } else {
      body.threshold_pace_s_per_km = null;
    }
    if (!any) return 'Indica al menos un umbral.';
    if (body.notes && body.notes.length > 2000) return 'Las notas no pueden superar los 2000 caracteres.';
    return body;
  };

  const save = async () => {
    const body = build();
    if (typeof body === 'string') return setError(body);
    setSaving(true);
    setError(null);
    try {
      await athleteApi.createThreshold(body);
      navigation.goBack();
    } catch (e) {
      setError(errorText(e));
      setSaving(false);
    }
  };

  return (
    <Screen error={error} onDismissError={() => setError(null)} title="Nuevo umbral" onBack={navigation.goBack}>
      <Section>
        <Text style={styles.muted}>
          {current
            ? 'Precargado con el umbral vigente. Cambia lo que haya variado: los valores que dejes vacíos quedarán sin registrar desde esa fecha.'
            : 'Registra tus umbrales. Las zonas se calculan a partir del FTP y de la FC umbral.'}
        </Text>
        <Field label="Vigente desde" value={effectiveFrom} onChangeText={setEffectiveFrom} placeholder="AAAA-MM-DD" />
        {current && unassignedLegacyLthr(current) != null ? (
          <Text style={styles.muted}>
            FC umbral antigua, sin asignar a ninguna disciplina: {unassignedLegacyLthr(current)} ppm. Es sólo informativa
            y no se puede editar.
          </Text>
        ) : null}
        {NUMERIC_FIELDS.map((f) => (
          <Field
            key={f.key}
            label={f.label}
            value={values[f.key]}
            onChangeText={(v) => setValues((s) => ({ ...s, [f.key]: v }))}
            keyboardType={f.integer ? 'number-pad' : 'decimal-pad'}
          />
        ))}
        <Field label="Ritmo umbral (min/km)" value={pace} onChangeText={setPace} placeholder="4:45" />
        <Chips label="Origen" options={options(THRESHOLD_SOURCE_LABELS)} value={source} onChange={setSource} />
        <Field label="Notas" value={notes} onChangeText={setNotes} multiline placeholder="Test de 20 min en rodillo…" />
        <Button title="Guardar umbral" onPress={save} loading={saving} />
      </Section>
    </Screen>
  );
}
