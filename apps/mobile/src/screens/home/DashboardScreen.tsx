/**
 * Inicio: resumen con datos reales de la API (perfil, umbral vigente, próximos eventos e
 * integraciones). Lo que aún no tiene endpoint (plan, actividades, coach) se muestra como pendiente.
 * Cada bloque se carga por separado: un fallo en uno no bloquea el resto.
 */
import React, { useCallback } from 'react';
import { Pressable, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';
import { Bot } from 'lucide-react-native';

import { athleteApi, calendarApi } from '../../api/athleteApi';
import { ApiError, errorText } from '../../api/errors';
import { integrationsApi } from '../../api/integrationsApi';
import type { CalendarEventOut, CurrentThresholdOut, IntegrationOut, ProfileOut } from '../../api/types';
import { Button, Card, InfoRow, Loading, PendingFeature, Screen, styles } from '../../ui/components';
import { addDays, formatDate, formatDateTime, formatPace, todayIsoDate } from '../../ui/dates';
import { EVENT_KIND_LABELS } from '../../ui/labels';
import { colors } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = { navigation: NavigationProp<ParamListBase> };

type Section<T> = { ok: true; value: T } | { ok: false; error: string };

type DashboardData = {
  profile: Section<ProfileOut>;
  threshold: Section<CurrentThresholdOut | null>;
  events: Section<CalendarEventOut[]>;
  integrations: Section<IntegrationOut[]>;
};

async function section<T>(promise: Promise<T>): Promise<Section<T>> {
  try {
    return { ok: true, value: await promise };
  } catch (e) {
    return { ok: false, error: errorText(e) };
  }
}

async function loadDashboard(): Promise<DashboardData> {
  const today = todayIsoDate();
  const [profile, threshold, events, integrations] = await Promise.all([
    section(athleteApi.getProfile()),
    section(
      athleteApi.getCurrentThreshold().catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 404) return null; // aún sin umbrales
        throw e;
      }),
    ),
    // Un año: basta para encontrar la próxima carrera y los eventos de la semana.
    section(calendarApi.listEvents(today, addDays(today, 365))),
    section(integrationsApi.list()),
  ]);
  return { profile, threshold, events, integrations };
}

function SectionError({ message }: { message: string }) {
  return <Text style={{ color: colors.danger, fontSize: 13 }}>{message}</Text>;
}

/** Días naturales desde hoy hasta la fecha local del evento. */
function daysUntil(iso: string): number {
  const d = new Date(iso);
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

export default function DashboardScreen({ navigation }: Props) {
  const load = useCallback(loadDashboard, []);
  const { data, loading, error, setError, reload } = useFocusLoad(load);

  const profile = data?.profile.ok ? data.profile.value : null;
  const events = data?.events.ok ? data.events.value : [];
  const weekEnd = addDays(todayIsoDate(), 7);
  const nextRace = events.find((e) => e.kind === 'race');
  const thisWeek = events.filter((e) => e.start_at.slice(0, 10) <= weekEnd).slice(0, 5);
  const wahoo = data?.integrations.ok ? data.integrations.value.find((i) => i.provider === 'wahoo') : undefined;

  return (
    <Screen
      title={profile?.display_name ? `Hola, ${profile.display_name}` : 'Inicio'}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={reload}
      right={
        <Pressable onPress={() => navigation.navigate('CoachChat')} accessibilityRole="button" accessibilityLabel="Coach">
          <Bot size={26} color={colors.primary} />
        </Pressable>
      }
    >
      {loading && !data ? <Loading /> : null}
      {data ? (
        <>
          {!data.profile.ok ? (
            <Card title="Perfil">
              <SectionError message={data.profile.error} />
            </Card>
          ) : null}

          <PendingFeature title="Entreno de hoy">
            La planificación de sesiones todavía no está disponible en la API. Aquí aparecerá el entreno del día cuando exista.
          </PendingFeature>

          <Card
            title="Próxima carrera"
            right={<Button title="Calendario" variant="secondary" onPress={() => navigation.navigate('Calendario')} />}
          >
            {!data.events.ok ? <SectionError message={data.events.error} /> : null}
            {data.events.ok && !nextRace ? <Text style={styles.muted}>No hay carreras en los próximos 12 meses.</Text> : null}
            {nextRace ? (
              <>
                <Text style={[styles.text, { fontSize: 16, fontWeight: '700' }]}>{nextRace.title}</Text>
                <InfoRow label="Fecha" value={formatDateTime(nextRace.start_at, nextRace.all_day)} />
                <InfoRow label="Faltan" value={`${daysUntil(nextRace.start_at)} días`} />
                {nextRace.race ? <InfoRow label="Prioridad" value={nextRace.race.priority} /> : null}
              </>
            ) : null}
          </Card>

          <Card title="Próximos 7 días">
            {!data.events.ok ? <SectionError message={data.events.error} /> : null}
            {data.events.ok && thisWeek.length === 0 ? <Text style={styles.muted}>Sin eventos esta semana.</Text> : null}
            {thisWeek.map((e) => (
              <InfoRow key={e.id} label={`${formatDateTime(e.start_at, e.all_day)} · ${EVENT_KIND_LABELS[e.kind]}`} value={e.title} />
            ))}
          </Card>

          <Card
            title="Umbral vigente"
            right={<Button title="Ver zonas" variant="secondary" onPress={() => navigation.navigate('Thresholds')} />}
          >
            {!data.threshold.ok ? <SectionError message={data.threshold.error} /> : null}
            {data.threshold.ok && !data.threshold.value ? (
              <Text style={styles.muted}>Todavía no hay umbrales. Regístralos para calcular tus zonas.</Text>
            ) : null}
            {data.threshold.ok && data.threshold.value ? (
              <>
                <Text style={styles.muted}>Desde {formatDate(data.threshold.value.threshold.effective_from)}</Text>
                <InfoRow label="FTP" value={data.threshold.value.threshold.ftp_w != null ? `${data.threshold.value.threshold.ftp_w} W` : '—'} />
                <InfoRow label="FC umbral" value={data.threshold.value.threshold.lthr_bpm != null ? `${data.threshold.value.threshold.lthr_bpm} ppm` : '—'} />
                <InfoRow label="Ritmo umbral" value={data.threshold.value.threshold.threshold_pace_s_per_km != null ? `${formatPace(data.threshold.value.threshold.threshold_pace_s_per_km)} /km` : '—'} />
              </>
            ) : null}
          </Card>

          <PendingFeature title="Carga y resumen semanal">
            Las métricas de carga (TSS, horas, tendencias) se calcularán en la API a partir de las actividades sincronizadas. Aún no hay endpoint.
          </PendingFeature>

          <Card
            title="Wahoo"
            right={<Button title="Gestionar" variant="secondary" onPress={() => navigation.navigate('Integrations')} />}
          >
            {!data.integrations.ok ? <SectionError message={data.integrations.error} /> : null}
            {data.integrations.ok ? (
              <Text style={styles.muted}>
                {wahoo
                  ? `Conectado${wahoo.last_sync_at ? ` · última sincronización ${formatDateTime(wahoo.last_sync_at, false)}` : ''}`
                  : 'Sin conectar.'}
              </Text>
            ) : null}
          </Card>
        </>
      ) : null}
      <View />
    </Screen>
  );
}
