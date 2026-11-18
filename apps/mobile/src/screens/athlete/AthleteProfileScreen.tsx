/**
 * Pestaña Perfil (propuesta v3, #25): ficha con nombre, deportes y tira de umbrales vigentes, y
 * secciones de filas con filetes (Entrenamiento, Conexiones y Aplicación). El engranaje abre
 * Ajustes y conexiones. La edición de los datos personales es la de #20; la zona horaria se
 * cambia en Ajustes.
 */
import React, { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { athleteApi } from '../../api/athleteApi';
import { ApiError, errorText } from '../../api/errors';
import { integrationsApi } from '../../api/integrationsApi';
import type { CurrentThresholdOut, IntegrationOut, ProfileOut, ProfilePatch, Sex, Sport, ThresholdOut, WeekAvailability } from '../../api/types';
import { Button, Chips, Field, IconButton, Loading, Screen, Section, styles as base } from '../../ui/components';
import { formatDate, formatDateTime, formatPace, isValidIsoDate } from '../../ui/dates';
import { numberToText, parseOptionalNumber } from '../../ui/forms';
import { options, SEX_LABELS, SPORT_LABELS } from '../../ui/labels';
import { Row, RowGroup, StatusDot } from '../../ui/Row';
import { StatStrip } from '../../ui/StatStrip';
import { spacing } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';
import { zoneModelFor } from '../../ui/zoneModel';

type Props = { navigation: NavigationProp<ParamListBase>; onLogout?: () => void };

type Form = {
  display_name: string;
  birth_date: string;
  sex: Sex | null;
  height_cm: string;
  sports: Sport[];
};

type Loaded<T> = { ok: true; value: T } | { ok: false; error: string };

type ProfileData = {
  profile: ProfileOut;
  threshold: Loaded<CurrentThresholdOut | null>;
  integrations: Loaded<IntegrationOut[]>;
  availability: Loaded<WeekAvailability>;
};

async function settle<T>(promise: Promise<T>): Promise<Loaded<T>> {
  try {
    return { ok: true, value: await promise };
  } catch (e) {
    return { ok: false, error: errorText(e) };
  }
}

/** El perfil es imprescindible; umbrales, Wahoo y disponibilidad se muestran si cargan. */
async function loadProfile(): Promise<ProfileData> {
  const [profile, threshold, integrations, availability] = await Promise.all([
    athleteApi.getProfile(),
    settle(
      athleteApi.getCurrentThreshold().catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) return null; // aún sin umbrales
        throw e;
      }),
    ),
    settle(integrationsApi.list()),
    settle(athleteApi.getAvailability()),
  ]);
  return { profile, threshold, integrations, availability };
}

function toForm(p: ProfileOut): Form {
  return {
    display_name: p.display_name ?? '',
    birth_date: p.birth_date ?? '',
    sex: p.sex ?? null,
    height_cm: numberToText(p.height_cm),
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

  if (form.sports.join() !== profile.sports.join()) patch.sports = form.sports;
  return patch;
}

/** Años cumplidos a partir de la fecha de nacimiento (dato de la ficha, no una métrica). */
function age(birth: string | null): number | null {
  if (!birth) return null;
  const [y, m, d] = birth.split('-').map(Number);
  const now = new Date();
  const years = now.getFullYear() - y - (now.getMonth() + 1 < m || (now.getMonth() + 1 === m && now.getDate() < d) ? 1 : 0);
  return years >= 0 ? years : null;
}

/**
 * FC umbral de la tira: `running_lthr_bpm`, la referencia de las zonas de trail (#22). La de
 * ciclismo sólo se usa para la carga por FC, y la antigua (`legacy_lthr_bpm`) no se muestra aquí.
 */
function thresholdHr(t: ThresholdOut): number | null {
  return t.running_lthr_bpm;
}

function availabilitySummary(week: WeekAvailability): string {
  const training = week.days.filter((d) => !d.is_preferred_rest && d.max_minutes !== 0);
  if (training.length === 0) return 'Sin días de entreno';
  const label = `${training.length} ${training.length === 1 ? 'día' : 'días'}`;
  if (training.some((d) => d.max_minutes == null)) return `${label} por semana`;
  const minutes = training.reduce((sum, d) => sum + (d.max_minutes ?? 0), 0);
  return `${label} · ${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')} h por semana`;
}

function wahooSummary(wahoo: IntegrationOut | undefined): string {
  if (!wahoo) return 'Sin conectar';
  if (wahoo.status === 'revoked') return 'Acceso revocado';
  if (wahoo.status === 'error') return 'Con errores';
  return wahoo.last_sync_at ? `Sincronizado ${formatDateTime(wahoo.last_sync_at, false)}` : 'Conectado, sin sincronizar';
}

const orDash = (v: number | null | undefined, format: (n: number) => string) => (v == null ? '—' : format(v));

export default function AthleteProfileScreen({ navigation, onLogout }: Props) {
  const load = useCallback(loadProfile, []);
  const { data, setData, loading, error, setError, reload } = useFocusLoad(load);
  const [form, setForm] = useState<Form | null>(null);
  const [saving, setSaving] = useState(false);
  const profile = data?.profile ?? null;

  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => (f ? { ...f, [key]: value } : f));

  const save = async () => {
    if (!form || !data) return;
    const patch = buildPatch(form, data.profile);
    if (typeof patch === 'string') return setError(patch);
    if (Object.keys(patch).length === 0) return setForm(null);
    setSaving(true);
    setError(null);
    try {
      const updated = await athleteApi.updateProfile(patch);
      setData({ ...data, profile: updated });
      setForm(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  };

  const current = data?.threshold.ok ? data.threshold.value : null;
  const t = current?.threshold ?? null;
  const power = zoneModelFor('cycling');
  const pace = zoneModelFor('running');
  const hr = zoneModelFor('trail_running');
  const wahoo = data?.integrations.ok ? data.integrations.value.find((i) => i.provider === 'wahoo') : undefined;
  const years = age(profile?.birth_date ?? null);
  const meta = [profile?.sports.map((s) => SPORT_LABELS[s]).join(' · '), years != null ? `${years} años` : null].filter(Boolean).join(' · ');

  return (
    <Screen
      title={profile?.display_name || 'Perfil'}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={form ? undefined : reload}
      right={<IconButton icon="settings" label="Ajustes y conexiones" onPress={() => navigation.navigate('Integrations')} />}
    >
      {loading && !data ? <Loading /> : null}

      {profile && !form ? (
        <View style={styles.identity}>
          <Text style={[base.muted, styles.meta]}>{meta || 'Completa tu perfil'}</Text>
          <Button title="Editar" variant="text" onPress={() => setForm(toForm(profile))} />
        </View>
      ) : null}

      {form ? (
        <Section title="Editar perfil">
          <Field label="Nombre" value={form.display_name} onChangeText={(v) => set('display_name', v)} />
          <Field label="Fecha de nacimiento" value={form.birth_date} onChangeText={(v) => set('birth_date', v)} placeholder="AAAA-MM-DD" />
          <Chips label="Sexo" options={options(SEX_LABELS)} value={form.sex} onChange={(v) => set('sex', v)} allowNone />
          <Field label="Altura (cm)" value={form.height_cm} onChangeText={(v) => set('height_cm', v)} keyboardType="decimal-pad" />
          <Chips label="Deportes" options={options(SPORT_LABELS)} value={form.sports} onChange={(v) => set('sports', v)} multiple />
          <View style={styles.actions}>
            <View style={styles.action}>
              <Button title="Cancelar" variant="secondary" onPress={() => setForm(null)} disabled={saving} />
            </View>
            <View style={styles.action}>
              <Button title="Guardar" onPress={save} loading={saving} />
            </View>
          </View>
        </Section>
      ) : null}

      {data && !form ? (
        <View style={styles.thresholds}>
          {!data.threshold.ok ? <Text style={base.errorInline}>{data.threshold.error}</Text> : null}
          {data.threshold.ok && !t ? <Text style={base.muted}>Todavía no hay umbrales. Regístralos para calcular tus zonas.</Text> : null}
          {t && power && pace && hr ? (
            <>
              <StatStrip
                stats={[
                  { value: orDash(t.ftp_w, power.format), caption: `${power.unit} ${power.thresholdLabel}` },
                  { value: orDash(t.threshold_pace_s_per_km, formatPace), caption: `${pace.unit} umbral` },
                  { value: orDash(thresholdHr(t), hr.format), caption: `${hr.unit} umbral` },
                  { value: orDash(t.weight_kg, (v) => v.toLocaleString('es-ES', { maximumFractionDigits: 1 })), caption: 'kg' },
                ]}
              />
              <Text style={base.muted}>Umbrales vigentes desde el {formatDate(t.effective_from)}</Text>
            </>
          ) : null}
        </View>
      ) : null}

      {data && !form ? (
        <>
          <RowGroup title="Entrenamiento">
            <Row icon="thresholds" title="Umbrales y zonas" subtitle="FTP, ritmo y FC de trail" onPress={() => navigation.navigate('Thresholds')} />
            <Row
              icon="availability"
              title="Disponibilidad"
              subtitle={data.availability.ok ? availabilitySummary(data.availability.value) : data.availability.error}
              onPress={() => navigation.navigate('Availability')}
            />
          </RowGroup>

          <RowGroup title="Conexiones">
            <Row
              icon="sync"
              title="Wahoo"
              subtitle={data.integrations.ok ? wahooSummary(wahoo) : data.integrations.error}
              value={wahoo ? <StatusDot active={wahoo.status === 'active'} /> : undefined}
              onPress={() => navigation.navigate('Integrations')}
            />
          </RowGroup>

          <RowGroup title="Aplicación">
            <Row icon="timezone" title="Zona horaria" value={data.profile.timezone} onPress={() => navigation.navigate('Integrations')} />
            {onLogout ? <Row icon="logout" title="Cerrar sesión" danger onPress={onLogout} /> : null}
          </RowGroup>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  identity: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md, marginTop: -spacing.md },
  meta: { flexShrink: 1 },
  thresholds: { gap: spacing.sm },
  actions: { flexDirection: 'row', gap: spacing.sm },
  action: { flex: 1 },
});
