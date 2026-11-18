import React, { useState } from 'react';
import { Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { athleteApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import type { ProfileOut, ProfilePatch, Sex, Sport } from '../../api/types';
import { Button, Card, Chips, Field, InfoRow, Loading, Screen, styles } from '../../ui/components';
import { formatDate, isValidIsoDate } from '../../ui/dates';
import { numberToText, parseOptionalNumber } from '../../ui/forms';
import { options, SEX_LABELS, SPORT_LABELS } from '../../ui/labels';
import { useFocusLoad } from '../../ui/useAsync';

type Props = { navigation: NavigationProp<ParamListBase>; onLogout?: () => void };

type Form = {
  display_name: string;
  birth_date: string;
  sex: Sex | null;
  height_cm: string;
  timezone: string;
  sports: Sport[];
};

function toForm(p: ProfileOut): Form {
  return {
    display_name: p.display_name ?? '',
    birth_date: p.birth_date ?? '',
    sex: p.sex ?? null,
    height_cm: numberToText(p.height_cm),
    timezone: p.timezone,
    sports: [...p.sports],
  };
}

/** Valida el formulario y devuelve el PATCH con los campos cambiados (o un mensaje de error). */
function buildPatch(form: Form, profile: ProfileOut): ProfilePatch | string {
  const patch: ProfilePatch = {};
  const name = form.display_name.trim();
  if (name.length > 120) return 'El nombre no puede tener más de 120 caracteres.';
  if ((name || null) !== profile.display_name) patch.display_name = name || null;

  const birth = form.birth_date.trim();
  if (birth && !isValidIsoDate(birth)) return 'La fecha de nacimiento debe tener el formato AAAA-MM-DD.';
  if ((birth || null) !== profile.birth_date) patch.birth_date = birth || null;

  if (form.sex !== profile.sex) patch.sex = form.sex;

  const height = parseOptionalNumber(form.height_cm);
  if (height !== null && (Number.isNaN(height) || height < 100 || height > 250)) {
    return 'La altura debe estar entre 100 y 250 cm.';
  }
  if (height !== profile.height_cm) patch.height_cm = height === null ? null : Math.round(height * 10) / 10;

  const tz = form.timezone.trim();
  if (!tz || tz.length > 64) return 'Indica una zona horaria válida (p. ej. Europe/Madrid).';
  if (tz !== profile.timezone) patch.timezone = tz;

  if (form.sports.join() !== profile.sports.join()) patch.sports = form.sports;
  return patch;
}

export default function AthleteProfileScreen({ navigation, onLogout }: Props) {
  const { data: profile, setData, loading, error, setError, reload } = useFocusLoad(athleteApi.getProfile);
  const [form, setForm] = useState<Form | null>(null);
  const [saving, setSaving] = useState(false);

  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => (f ? { ...f, [key]: value } : f));

  const save = async () => {
    if (!form || !profile) return;
    const patch = buildPatch(form, profile);
    if (typeof patch === 'string') return setError(patch);
    if (Object.keys(patch).length === 0) return setForm(null);
    setSaving(true);
    setError(null);
    try {
      setData(await athleteApi.updateProfile(patch));
      setForm(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Screen error={error} onDismissError={() => setError(null)} title="Perfil" refreshing={loading && !!profile} onRefresh={form ? undefined : reload}>
      {loading && !profile ? <Loading /> : null}

      {profile && !form ? (
        <Card title={profile.display_name || 'Sin nombre'} right={<Button title="Editar" variant="secondary" onPress={() => setForm(toForm(profile))} />}>
          <InfoRow label="Fecha de nacimiento" value={profile.birth_date ? formatDate(profile.birth_date) : '—'} />
          <InfoRow label="Sexo" value={profile.sex ? SEX_LABELS[profile.sex] : '—'} />
          <InfoRow label="Altura" value={profile.height_cm != null ? `${profile.height_cm} cm` : '—'} />
          <InfoRow label="Zona horaria" value={profile.timezone} />
          <InfoRow label="Deportes" value={profile.sports.length ? profile.sports.map((s) => SPORT_LABELS[s]).join(', ') : '—'} />
        </Card>
      ) : null}

      {form ? (
        <Card title="Editar perfil">
          <Field label="Nombre" value={form.display_name} onChangeText={(v) => set('display_name', v)} />
          <Field label="Fecha de nacimiento" value={form.birth_date} onChangeText={(v) => set('birth_date', v)} placeholder="AAAA-MM-DD" />
          <Chips label="Sexo" options={options(SEX_LABELS)} value={form.sex} onChange={(v) => set('sex', v)} allowNone />
          <Field label="Altura (cm)" value={form.height_cm} onChangeText={(v) => set('height_cm', v)} keyboardType="decimal-pad" />
          <Field label="Zona horaria" value={form.timezone} onChangeText={(v) => set('timezone', v)} placeholder="Europe/Madrid" hint="Identificador IANA, p. ej. Europe/Madrid o Atlantic/Canary." />
          <Chips label="Deportes" options={options(SPORT_LABELS)} value={form.sports} onChange={(v) => set('sports', v)} multiple />
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <View style={{ flex: 1 }}>
              <Button title="Cancelar" variant="secondary" onPress={() => setForm(null)} disabled={saving} />
            </View>
            <View style={{ flex: 1 }}>
              <Button title="Guardar" onPress={save} loading={saving} />
            </View>
          </View>
        </Card>
      ) : null}

      <Card title="Entrenamiento">
        <Text style={styles.muted}>Umbrales, zonas y disponibilidad semanal que usa el coach para planificar.</Text>
        <Button title="Umbrales y zonas" variant="secondary" onPress={() => navigation.navigate('Thresholds')} />
        <Button title="Disponibilidad semanal" variant="secondary" onPress={() => navigation.navigate('Availability')} />
        <Button title="Integraciones (Wahoo)" variant="secondary" onPress={() => navigation.navigate('Integrations')} />
      </Card>

      {onLogout ? <Button title="Cerrar sesión" variant="danger" onPress={onLogout} /> : null}
    </Screen>
  );
}
