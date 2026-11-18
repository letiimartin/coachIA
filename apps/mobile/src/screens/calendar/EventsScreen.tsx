import React, { useCallback, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { calendarApi } from '../../api/athleteApi';
import type { CalendarEventOut } from '../../api/types';
import { Button, Chips, Field, IconButton, Loading, Screen, Section, styles } from '../../ui/components';
import { addDays, formatDateTime, isValidIsoDate, todayIsoDate } from '../../ui/dates';
import { EVENT_KIND_LABELS, RACE_DISCIPLINE_LABELS, TRAINING_IMPACT_LABELS } from '../../ui/labels';
import { colors, lines, spacing } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = { navigation: NavigationProp<ParamListBase> };

type Preset = '30' | '90' | '365' | 'custom';
const PRESETS: { value: Preset; label: string }[] = [
  { value: '30', label: '30 días' },
  { value: '90', label: '3 meses' },
  { value: '365', label: '1 año' },
  { value: 'custom', label: 'Otro rango' },
];

function EventItem({ event, onPress }: { event: CalendarEventOut; onPress: () => void }) {
  const race = event.race;
  const raceInfo = race
    ? [
        race.discipline ? RACE_DISCIPLINE_LABELS[race.discipline] : null,
        race.distance_m != null ? `${(race.distance_m / 1000).toLocaleString('es-ES')} km` : null,
        race.ascent_m != null ? `${race.ascent_m.toLocaleString('es-ES')} m D+` : null,
        `Prioridad ${race.priority}`,
      ]
        .filter(Boolean)
        .join(' · ')
    : null;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => [local.item, pressed && local.pressed]}>
        <View style={local.itemHeader}>
          <Text style={[styles.textStrong, local.itemTitle]}>{event.title}</Text>
          <Text style={styles.textActive}>{EVENT_KIND_LABELS[event.kind]}</Text>
        </View>
        <Text style={styles.muted}>
          {formatDateTime(event.start_at, event.all_day)}
          {event.end_at ? ` → ${formatDateTime(event.end_at, event.all_day)}` : ''}
        </Text>
        {raceInfo ? <Text style={styles.text}>{raceInfo}</Text> : null}
        {event.training_impact !== 'none' ? <Text style={styles.muted}>{TRAINING_IMPACT_LABELS[event.training_impact]}</Text> : null}
    </Pressable>
  );
}

export default function EventsScreen({ navigation }: Props) {
  const [preset, setPreset] = useState<Preset>('90');
  const [range, setRange] = useState(() => ({ from: todayIsoDate(), to: addDays(todayIsoDate(), 90) }));
  const [draft, setDraft] = useState(range);

  const load = useCallback(() => calendarApi.listEvents(range.from, range.to), [range]);
  const { data: events, loading, error, setError, reload } = useFocusLoad(load);

  // Al cambiar el rango cambia `load` y useFocusLoad vuelve a cargar.
  const applyRange = setRange;

  const choosePreset = (p: Preset) => {
    setPreset(p);
    if (p !== 'custom') applyRange({ from: todayIsoDate(), to: addDays(todayIsoDate(), Number(p)) });
  };

  const applyCustom = () => {
    if (!isValidIsoDate(draft.from) || !isValidIsoDate(draft.to)) return setError('Las fechas deben tener el formato AAAA-MM-DD.');
    if (draft.to < draft.from) return setError('La fecha final no puede ser anterior a la inicial.');
    applyRange(draft);
  };

  return (
    <Screen
      title="Plan"
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!events}
      onRefresh={reload}
      right={<IconButton icon="add" label="Nuevo evento" onPress={() => navigation.navigate('EventForm', {})} />}
    >
      <Chips options={PRESETS} value={preset} onChange={choosePreset} />
      {preset === 'custom' ? (
        <Section>
          <Field label="Desde" value={draft.from} onChangeText={(v) => setDraft((d) => ({ ...d, from: v }))} placeholder="AAAA-MM-DD" />
          <Field label="Hasta" value={draft.to} onChangeText={(v) => setDraft((d) => ({ ...d, to: v }))} placeholder="AAAA-MM-DD" />
          <Button title="Ver eventos" variant="secondary" onPress={applyCustom} />
        </Section>
      ) : null}

      {loading && !events ? <Loading /> : null}
      {events && events.length === 0 ? <Text style={styles.muted}>No hay eventos en este rango.</Text> : null}
      {events && events.length > 0 ? (
        <View>
          {events.map((e) => (
            <EventItem key={e.id} event={e} onPress={() => navigation.navigate('EventForm', { event: e })} />
          ))}
        </View>
      ) : null}
    </Screen>
  );
}

const local = StyleSheet.create({
  item: { gap: spacing.xs, paddingVertical: spacing.md, borderTopWidth: lines.hairline, borderTopColor: colors.separator },
  pressed: { backgroundColor: colors.surfaceSoft },
  itemHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', gap: spacing.sm },
  itemTitle: { flex: 1 },
});
