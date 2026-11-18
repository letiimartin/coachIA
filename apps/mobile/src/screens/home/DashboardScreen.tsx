/**
 * Hoy (propuesta v3, #24): saludo y fecha, el entreno del día en la superficie destacada, la forma
 * (CTL/ATL/TSB de la API), la semana con sus eventos y la cuenta atrás al próximo objetivo.
 * Sólo datos reales: lo que aún no tiene endpoint (el plan de sesiones) se dice tal cual.
 * Cada bloque se carga por separado: un fallo en uno no bloquea el resto.
 */
import React, { useCallback } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { athleteApi, calendarApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import { fitnessApi, type FitnessDayOut } from '../../api/fitnessApi';
import type { CalendarEventOut, ProfileOut } from '../../api/types';
import { AgendaItems } from '../../ui/Agenda';
import { daysBetween, localDay, longDayLabel, startOfWeek, WEEKDAY_LETTERS, weekDays } from '../../ui/calendarDates';
import { EVENT_KIND_ICONS, eventsByDay, raceSummary, toAgendaEntry } from '../../ui/calendarEvents';
import { Button, Card, Loading, Screen, Section, styles } from '../../ui/components';
import { addDays, formatDate, todayIsoDate } from '../../ui/dates';
import { StatStrip } from '../../ui/StatStrip';
import { colors, lines, spacing, typography } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';
import { WeekStrip, type WeekStripDay } from '../../ui/WeekStrip';

type Props = { navigation: NavigationProp<ParamListBase> };

type Loaded<T> = { ok: true; value: T } | { ok: false; error: string };

type DashboardData = {
  today: string;
  profile: Loaded<ProfileOut>;
  fitness: Loaded<FitnessDayOut | null>;
  events: Loaded<CalendarEventOut[]>;
};

async function section<T>(promise: Promise<T>): Promise<Loaded<T>> {
  try {
    return { ok: true, value: await promise };
  } catch (e) {
    return { ok: false, error: errorText(e) };
  }
}

async function loadDashboard(): Promise<DashboardData> {
  const today = todayIsoDate();
  const [profile, fitness, events] = await Promise.all([
    section(athleteApi.getProfile()),
    section(fitnessApi.getSeries(today, today).then((s) => s.days[s.days.length - 1] ?? null)),
    // Desde el lunes y durante un año: la semana en curso y el próximo objetivo.
    section(calendarApi.listEvents(startOfWeek(today), addDays(today, 365))),
  ]);
  return { today, profile, fitness, events };
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour >= 6 && hour < 14) return 'Buenos días';
  if (hour >= 14 && hour < 21) return 'Buenas tardes';
  return 'Buenas noches';
}

/** Cifra con signo menos tipográfico y sin decimales (la API ya las redondea). */
function formatLoad(value: number): string {
  const n = Math.round(value);
  return n < 0 ? `−${Math.abs(n)}` : String(n);
}

function SectionError({ message }: { message: string }) {
  return <Text style={styles.errorInline}>{message}</Text>;
}

export default function DashboardScreen({ navigation }: Props) {
  const load = useCallback(loadDashboard, []);
  const { data, loading, error, setError, reload } = useFocusLoad(load);

  const today = data?.today ?? todayIsoDate();
  const profile = data?.profile.ok ? data.profile.value : null;
  const events = data?.events.ok ? data.events.value : [];
  const openEvent = (id: string) => {
    const event = events.find((e) => e.id === id);
    if (event) navigation.navigate('EventDetail', { event });
  };

  const week = weekDays(startOfWeek(today));
  const byDay = eventsByDay(events, week);
  const weekStrip: WeekStripDay[] = week.map((date, i) => {
    const dayEvents = byDay[date];
    const race = dayEvents.find((e) => e.kind === 'race');
    const first = race ?? dayEvents[0];
    return {
      date,
      letter: WEEKDAY_LETTERS[i],
      day: Number(date.slice(8, 10)),
      icon: first ? EVENT_KIND_ICONS[first.kind] : null,
      highlight: !!race,
      count: dayEvents.length,
    };
  });
  const weekEvents = events.filter((e) => localDay(e.start_at) <= week[6] && localDay(e.end_at ?? e.start_at) >= week[0]);
  const todayEvents = byDay[today] ?? [];
  const nextRace = events.find((e) => e.kind === 'race' && localDay(e.start_at) >= today);
  const fitness = data?.fitness.ok ? data.fitness.value : null;
  const noLoadYet = fitness != null && fitness.ctl === 0 && fitness.atl === 0;

  return (
    <Screen
      title={profile?.display_name ? `${greeting()}, ${profile.display_name}` : greeting()}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={reload}
    >
      <Text style={local.date}>{longDayLabel(today)}</Text>
      {loading && !data ? <Loading /> : null}
      {data ? (
        <>
          {!data.profile.ok ? <SectionError message={data.profile.error} /> : null}

          <Card title="Entreno de hoy">
            <Text style={local.heroTitle}>Sin sesión planificada</Text>
            <Text style={local.heroText}>
              El plan de entrenamiento todavía no existe en la API. Cuando lo haga, aquí verás la sesión del día con su duración y su carga.
            </Text>
            {todayEvents.length > 0 ? (
              <View style={local.heroEvents}>
                <AgendaItems items={todayEvents.map((e) => toAgendaEntry(e))} onPressItem={openEvent} />
              </View>
            ) : null}
            <View style={local.heroActions}>
              <Button title="Ver el plan" onPress={() => navigation.navigate('Plan')} />
            </View>
          </Card>

          <Section
            title="Forma"
            right={<Button title="Rendimiento" variant="text" onPress={() => navigation.navigate('Rendimiento')} />}
          >
            {!data.fitness.ok ? <SectionError message={data.fitness.error} /> : null}
            {fitness && !noLoadYet ? (
              <>
                <StatStrip
                  size="large"
                  stats={[
                    { value: formatLoad(fitness.ctl), caption: 'Forma (CTL)' },
                    { value: formatLoad(fitness.atl), caption: 'Fatiga (ATL)' },
                    { value: formatLoad(fitness.tsb), caption: 'Balance (TSB)' },
                  ]}
                />
                {fitness.day !== today ? <Text style={styles.muted}>Datos del {formatDate(fitness.day)}.</Text> : null}
              </>
            ) : null}
            {data.fitness.ok && (!fitness || noLoadYet) ? (
              <Text style={styles.muted}>Aún no hay actividades con carga. La forma se calculará cuando se sincronicen tus entrenos.</Text>
            ) : null}
          </Section>

          <Section title="Esta semana" right={<Button title="Plan" variant="text" onPress={() => navigation.navigate('Plan')} />}>
            {!data.events.ok ? <SectionError message={data.events.error} /> : null}
            <WeekStrip days={weekStrip} today={today} />
            {data.events.ok && weekEvents.length === 0 ? <Text style={styles.muted}>Sin eventos esta semana.</Text> : null}
            {weekEvents.length > 0 ? (
              <AgendaItems
                items={weekEvents.map((e) => toAgendaEntry(e, `${longDayLabel(localDay(e.start_at))} · ${toAgendaEntry(e).subtitle}`))}
                onPressItem={openEvent}
              />
            ) : null}
          </Section>

          <Section title="Próximo objetivo">
            {data.events.ok && !nextRace ? <Text style={styles.muted}>No hay carreras en los próximos 12 meses.</Text> : null}
            {nextRace ? (
              <Pressable
                onPress={() => openEvent(nextRace.id)}
                accessibilityRole="button"
                style={({ pressed }) => [local.goal, pressed && local.pressed]}
              >
                <View style={local.countdown}>
                  <Text style={local.countdownNumber}>{daysBetween(today, localDay(nextRace.start_at))}</Text>
                  <Text style={local.countdownUnit}>{daysBetween(today, localDay(nextRace.start_at)) === 1 ? 'día' : 'días'}</Text>
                </View>
                <View style={local.goalText}>
                  <Text style={local.goalTitle}>{nextRace.title}</Text>
                  <Text style={styles.muted}>
                    {[longDayLabel(localDay(nextRace.start_at)), raceSummary(nextRace, false)].filter(Boolean).join(' · ')}
                  </Text>
                </View>
              </Pressable>
            ) : null}
          </Section>
        </>
      ) : null}
    </Screen>
  );
}

const local = StyleSheet.create({
  date: { ...typography.label, color: colors.textSecondary, marginTop: -spacing.md },
  heroTitle: { ...typography.title, color: colors.text },
  heroText: { ...typography.small, color: colors.textSecondary },
  heroEvents: { paddingTop: spacing.sm, borderTopWidth: lines.hairline, borderTopColor: colors.separatorStrong },
  heroActions: { flexDirection: 'row', paddingTop: spacing.sm },
  goal: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  pressed: { opacity: 0.7 },
  countdown: { alignItems: 'flex-start' },
  countdownNumber: { ...typography.display, color: colors.text, fontVariant: ['tabular-nums'] },
  countdownUnit: { ...typography.label, color: colors.textSecondary },
  goalText: { flex: 1, minWidth: 0, gap: spacing.xxs },
  goalTitle: { ...typography.bodyBold, color: colors.textActive },
});
