/**
 * Plan (propuesta v3, #24): semana en agenda (una fila por día) o mes en rejilla con la lista del
 * día seleccionado debajo. Ambas vistas piden el rango visible a `GET /v1/calendar/events` y a
 * `GET /v1/planned-workouts` (#31): cada día muestra primero sus entrenos y después sus eventos.
 */
import React, { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { calendarApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import type { CalendarEventOut, PlannedWorkoutOut } from '../../api/types';
import { Agenda, AgendaItems, type AgendaDay } from '../../ui/Agenda';
import {
  addMonths,
  dayLabel,
  dayOfMonth,
  isSameMonth,
  monthGridDays,
  monthLabel,
  startOfMonth,
  startOfWeek,
  WEEKDAY_LETTERS,
  weekDays,
  weekdayShort,
  weekRangeLabel,
} from '../../ui/calendarDates';
import { eventsByDay, toAgendaEntry } from '../../ui/calendarEvents';
import { IconButton, Loading, Screen, SegmentedTabs, Section, styles } from '../../ui/components';
import { addDays, todayIsoDate } from '../../ui/dates';
import { MonthGrid, type MonthGridDay } from '../../ui/MonthGrid';
import { PeriodNav } from '../../ui/PeriodNav';
import { loadPlannedWithSummaries, type PlannedWithSummaries, workoutIdFromKey, workoutsByDay, workoutToAgendaEntry } from '../../ui/plannedWorkouts';
import { spacing } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = { navigation: NavigationProp<ParamListBase> };

type View_ = 'week' | 'month';
const VIEWS: { value: View_; label: string }[] = [
  { value: 'week', label: 'Semana' },
  { value: 'month', label: 'Mes' },
];

/** «2 entrenos · 1 evento», «Sin planes». */
function countLabel(workouts: number, events: number): string {
  const parts = [
    workouts > 0 ? (workouts === 1 ? '1 entreno' : `${workouts} entrenos`) : null,
    events > 0 ? (events === 1 ? '1 evento' : `${events} eventos`) : null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(' · ') : 'Sin planes';
}

export default function EventsScreen({ navigation }: Props) {
  const today = todayIsoDate();
  const [view, setView] = useState<View_>('week');
  const [monday, setMonday] = useState(() => startOfWeek(today));
  const [month, setMonth] = useState(() => startOfMonth(today));
  const [selected, setSelected] = useState(today);

  const days = view === 'week' ? weekDays(monday) : monthGridDays(month);
  const from = days[0];
  const to = days[days.length - 1];
  const load = useCallback(
    () =>
      Promise.all([
        calendarApi.listEvents(from, to),
        // Si fallan los entrenos, los eventos se siguen viendo y el error se muestra aparte.
        loadPlannedWithSummaries(from, to).then(
          (planned) => ({ ...planned, plannedError: null as string | null }),
          (e: unknown): PlannedWithSummaries & { plannedError: string | null } => ({ workouts: [], summaries: {}, plannedError: errorText(e) }),
        ),
      ]).then(([events, planned]) => ({ events, ...planned })),
    [from, to],
  );
  const { data, loading, error, setError, reload } = useFocusLoad(load);
  const events = data?.events ?? null;
  const summaries = data?.summaries ?? {};

  const byDay = eventsByDay(events ?? [], days);
  const workoutsDay = workoutsByDay(data?.workouts ?? [], days);
  const openEvent = (key: string) => {
    const workoutId = workoutIdFromKey(key);
    if (workoutId) {
      navigation.navigate('StrengthSession', { id: workoutId });
      return;
    }
    const event = events?.find((e) => e.id === key);
    if (event) navigation.navigate('EventDetail', { event });
  };
  const uniqueCount = (list: { id: string }[]) => new Set(list.map((e) => e.id)).size;
  const dayItems = (date: string) => [
    ...workoutsDay[date].map((w: PlannedWorkoutOut) => workoutToAgendaEntry(w, summaries[w.id])),
    ...byDay[date].map((e: CalendarEventOut) => toAgendaEntry(e)),
  ];

  const changeView = (v: View_) => {
    setView(v);
    // Cada vista se abre en el periodo del día seleccionado.
    if (v === 'week') setMonday(startOfWeek(selected));
    else setMonth(startOfMonth(selected));
  };

  const moveMonth = (delta: number) => {
    const next = addMonths(month, delta);
    setMonth(next);
    setSelected(isSameMonth(today, next) ? today : next);
  };

  const moveWeek = (delta: number) => {
    const next = addDays(monday, delta * 7);
    setMonday(next);
    setSelected(weekDays(next).includes(today) ? today : next);
  };

  const monthDays = days.filter((d) => isSameMonth(d, month));
  const weekCount = countLabel(uniqueCount(days.flatMap((d) => workoutsDay[d])), uniqueCount(days.flatMap((d) => byDay[d])));
  const monthCount = countLabel(uniqueCount(monthDays.flatMap((d) => workoutsDay[d])), uniqueCount(monthDays.flatMap((d) => byDay[d])));

  const agendaDays: AgendaDay[] = days.map((date) => ({
    date,
    weekday: weekdayShort(date),
    day: String(dayOfMonth(date)),
    items: dayItems(date),
  }));

  const gridDays: MonthGridDay[] = days.map((date) => {
    const list = byDay[date];
    const dayWorkouts = workoutsDay[date];
    return {
      date,
      day: dayOfMonth(date),
      inMonth: isSameMonth(date, month),
      marker: list.some((e) => e.kind === 'race') ? 'race' : list.length + dayWorkouts.length > 0 ? 'event' : null,
      accessibilityLabel: `${dayLabel(date)}${date === today ? ', hoy' : ''}: ${countLabel(dayWorkouts.length, list.length).toLowerCase()}`,
    };
  });
  const selectedItems = byDay[selected] ? dayItems(selected) : [];

  return (
    <Screen
      title="Plan"
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!events}
      onRefresh={reload}
      right={<IconButton icon="add" label="Nuevo evento" onPress={() => navigation.navigate('EventForm', {})} />}
    >
      <View style={local.header}>
        <SegmentedTabs options={VIEWS} value={view} onChange={changeView} />
        {view === 'week' ? (
          <PeriodNav
            label={weekRangeLabel(monday)}
            caption={events ? weekCount : undefined}
            onPrevious={() => moveWeek(-1)}
            onNext={() => moveWeek(1)}
            previousLabel="Semana anterior"
            nextLabel="Semana siguiente"
          />
        ) : (
          <PeriodNav
            label={monthLabel(month)}
            caption={events ? monthCount : undefined}
            onPrevious={() => moveMonth(-1)}
            onNext={() => moveMonth(1)}
            previousLabel="Mes anterior"
            nextLabel="Mes siguiente"
          />
        )}
      </View>

      {loading && !events ? <Loading /> : null}
      {data?.plannedError ? <Text style={styles.errorInline}>{`No se han podido cargar los entrenos. ${data.plannedError}`}</Text> : null}
      {events && view === 'week' ? <Agenda days={agendaDays} today={today} emptyText="Sin planes" onPressItem={openEvent} /> : null}
      {events && view === 'month' ? (
        <>
          <View style={local.bleed}>
            <MonthGrid weekdayLetters={WEEKDAY_LETTERS} days={gridDays} selected={selected} today={today} onSelect={setSelected} />
          </View>
          <Section title={`${dayLabel(selected)}${selected === today ? ' · hoy' : ''}`}>
            {selectedItems.length > 0 ? (
              <AgendaItems items={selectedItems} onPressItem={openEvent} />
            ) : (
              <Text style={styles.muted}>Nada planificado este día.</Text>
            )}
          </Section>
        </>
      ) : null}
    </Screen>
  );
}

const local = StyleSheet.create({
  header: { gap: spacing.md, marginTop: -spacing.sm },
  /** La rejilla ocupa todo el ancho de la columna, sin el margen lateral. */
  bleed: { marginHorizontal: -spacing.lg, marginTop: -spacing.sm },
});
