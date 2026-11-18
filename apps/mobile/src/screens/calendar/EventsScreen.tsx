import React, { useCallback, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';
import { Plus } from 'lucide-react-native';

import { calendarApi } from '../../api/athleteApi';
import type { CalendarEventOut } from '../../api/types';
import { Button, Card, Chips, Field, Loading, Screen, styles } from '../../ui/components';
import { addDays, formatDateTime, isValidIsoDate, todayIsoDate } from '../../ui/dates';
import { EVENT_KIND_LABELS, RACE_DISCIPLINE_LABELS, TRAINING_IMPACT_LABELS } from '../../ui/labels';
import { colors } from '../../ui/theme';
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
    <Pressable onPress={onPress} accessibilityRole="button">
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
          <Text style={[styles.text, { fontSize: 16, fontWeight: '700', flex: 1 }]}>{event.title}</Text>
          <Text style={{ color: colors.primary, fontSize: 12 }}>{EVENT_KIND_LABELS[event.kind]}</Text>
        </View>
        <Text style={styles.muted}>
          {formatDateTime(event.start_at, event.all_day)}
          {event.end_at ? ` → ${formatDateTime(event.end_at, event.all_day)}` : ''}
        </Text>
        {raceInfo ? <Text style={styles.text}>{raceInfo}</Text> : null}
        {event.training_impact !== 'none' ? <Text style={styles.muted}>{TRAINING_IMPACT_LABELS[event.training_impact]}</Text> : null}
      </Card>
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
      title="Calendario"
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!events}
      onRefresh={reload}
      right={
        <Pressable onPress={() => navigation.navigate('EventForm', {})} accessibilityRole="button" accessibilityLabel="Nuevo evento">
          <Plus size={26} color={colors.primary} />
        </Pressable>
      }
    >
      <Chips options={PRESETS} value={preset} onChange={choosePreset} />
      {preset === 'custom' ? (
        <Card>
          <Field label="Desde" value={draft.from} onChangeText={(v) => setDraft((d) => ({ ...d, from: v }))} placeholder="AAAA-MM-DD" />
          <Field label="Hasta" value={draft.to} onChangeText={(v) => setDraft((d) => ({ ...d, to: v }))} placeholder="AAAA-MM-DD" />
          <Button title="Ver eventos" variant="secondary" onPress={applyCustom} />
        </Card>
      ) : null}

      {loading && !events ? <Loading /> : null}
      {events && events.length === 0 ? <Text style={styles.muted}>No hay eventos en este rango.</Text> : null}
      {events?.map((e) => <EventItem key={e.id} event={e} onPress={() => navigation.navigate('EventForm', { event: e })} />)}
    </Screen>
  );
}
