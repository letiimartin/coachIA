/**
 * Plan (propuesta v3, #24): semana en agenda (una fila por día) o mes en rejilla con la lista del
 * día seleccionado debajo. Ambas vistas piden los eventos del rango visible a `GET /v1/calendar/events`.
 * Aún no hay plan de sesiones en la API: los días muestran sólo eventos.
 */
import React, { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { calendarApi } from '../../api/athleteApi';
import type { CalendarEventOut } from '../../api/types';
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
import { spacing } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = { navigation: NavigationProp<ParamListBase> };

type View_ = 'week' | 'month';
const VIEWS: { value: View_; label: string }[] = [
  { value: 'week', label: 'Semana' },
  { value: 'month', label: 'Mes' },
];

function countLabel(n: number): string {
  if (n === 0) return 'Sin eventos';
  return n === 1 ? '1 evento' : `${n} eventos`;
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
  const load = useCallback(() => calendarApi.listEvents(from, to), [from, to]);
  const { data: events, loading, error, setError, reload } = useFocusLoad(load);

  const byDay = eventsByDay(events ?? [], days);
  const openEvent = (id: string) => {
    const event = events?.find((e) => e.id === id);
    if (event) navigation.navigate('EventDetail', { event });
  };
  const uniqueCount = (list: CalendarEventOut[]) => new Set(list.map((e) => e.id)).size;

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

  const weekEvents = uniqueCount(days.flatMap((d) => byDay[d]));
  const monthEvents = uniqueCount(days.filter((d) => isSameMonth(d, month)).flatMap((d) => byDay[d]));

  const agendaDays: AgendaDay[] = days.map((date) => ({
    date,
    weekday: weekdayShort(date),
    day: String(dayOfMonth(date)),
    items: byDay[date].map((e) => toAgendaEntry(e)),
  }));

  const gridDays: MonthGridDay[] = days.map((date) => {
    const list = byDay[date];
    return {
      date,
      day: dayOfMonth(date),
      inMonth: isSameMonth(date, month),
      marker: list.some((e) => e.kind === 'race') ? 'race' : list.length > 0 ? 'event' : null,
      accessibilityLabel: `${dayLabel(date)}${date === today ? ', hoy' : ''}: ${countLabel(list.length).toLowerCase()}`,
    };
  });
  const selectedEvents = byDay[selected] ?? [];

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
            caption={events ? countLabel(weekEvents) : undefined}
            onPrevious={() => moveWeek(-1)}
            onNext={() => moveWeek(1)}
            previousLabel="Semana anterior"
            nextLabel="Semana siguiente"
          />
        ) : (
          <PeriodNav
            label={monthLabel(month)}
            caption={events ? countLabel(monthEvents) : undefined}
            onPrevious={() => moveMonth(-1)}
            onNext={() => moveMonth(1)}
            previousLabel="Mes anterior"
            nextLabel="Mes siguiente"
          />
        )}
      </View>

      {loading && !events ? <Loading /> : null}
      {events && view === 'week' ? <Agenda days={agendaDays} today={today} emptyText="Sin eventos" onPressItem={openEvent} /> : null}
      {events && view === 'month' ? (
        <>
          <View style={local.bleed}>
            <MonthGrid weekdayLetters={WEEKDAY_LETTERS} days={gridDays} selected={selected} today={today} onSelect={setSelected} />
          </View>
          <Section title={`${dayLabel(selected)}${selected === today ? ' · hoy' : ''}`}>
            {selectedEvents.length > 0 ? (
              <AgendaItems items={selectedEvents.map((e) => toAgendaEntry(e))} onPressItem={openEvent} />
            ) : (
              <Text style={styles.muted}>Sin eventos este día.</Text>
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
