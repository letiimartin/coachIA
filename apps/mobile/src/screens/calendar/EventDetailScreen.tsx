/**
 * Detalle de un evento (#24): vista de lectura con los datos de carrera, las notas y la fuente.
 * «Editar» abre el formulario. Al volver se recarga el evento para mostrar los cambios.
 */
import React, { useCallback } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { calendarApi } from '../../api/athleteApi';
import { ApiError } from '../../api/errors';
import type { CalendarEventOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { daysBetween, localDay, localTime, longDayLabel } from '../../ui/calendarDates';
import { formatKm, formatMeters } from '../../ui/calendarEvents';
import { Button, InfoRow, Screen, Section, styles } from '../../ui/components';
import { todayIsoDate } from '../../ui/dates';
import { Icon } from '../../ui/Icon';
import { ENRICHMENT_STATUS_LABELS, EVENT_KIND_LABELS, RACE_DISCIPLINE_LABELS, TRAINING_IMPACT_LABELS } from '../../ui/labels';
import { StatStrip, type Stat } from '../../ui/StatStrip';
import { colors, lines, spacing, typography } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = NativeStackScreenProps<RootStackParamList, 'EventDetail'>;

function whenLabel(event: CalendarEventOut): string {
  const start = localDay(event.start_at);
  const startText = `${longDayLabel(start)}${event.all_day ? '' : ` · ${localTime(event.start_at)}`}`;
  if (!event.end_at) return startText;
  const end = localDay(event.end_at);
  if (end === start) return event.all_day ? startText : `${startText} – ${localTime(event.end_at)}`;
  return `${startText} → ${longDayLabel(end)}${event.all_day ? '' : ` · ${localTime(event.end_at)}`}`;
}

function countdown(event: CalendarEventOut): string | null {
  const days = daysBetween(todayIsoDate(), localDay(event.start_at));
  if (days < 0) return null;
  if (days === 0) return 'hoy';
  return days === 1 ? 'mañana' : `faltan ${days} días`;
}

export default function EventDetailScreen({ navigation, route }: Props) {
  const initial = route.params.event;
  // El evento se vuelve a pedir al enfocar la pantalla (p. ej. al volver de editarlo).
  const load = useCallback(async () => {
    const from = localDay(initial.start_at);
    const events = await calendarApi.listEvents(from, from);
    const found = events.find((e) => e.id === initial.id);
    if (!found) throw new ApiError(404, 'not_found', 'Este evento ya no existe.');
    return found;
  }, [initial.id, initial.start_at]);
  const { data, error, setError } = useFocusLoad(load);
  const event = data ?? initial;
  const race = event.race;
  const left = countdown(event);

  const raceStats: Stat[] = race
    ? [
        { value: race.distance_m != null ? formatKm(race.distance_m) : '—', caption: 'Distancia' },
        { value: race.ascent_m != null ? formatMeters(race.ascent_m) : '—', caption: 'Desnivel positivo' },
      ]
    : [];
  const raceStats2: Stat[] = race
    ? [
        { value: race.discipline ? RACE_DISCIPLINE_LABELS[race.discipline] : '—', caption: 'Disciplina' },
        { value: race.priority, caption: 'Prioridad' },
      ]
    : [];

  return (
    <Screen
      title={event.title}
      onBack={navigation.goBack}
      right={<Button title="Editar" variant="text" onPress={() => navigation.navigate('EventForm', { event })} />}
      error={error}
      onDismissError={() => setError(null)}
    >
      <View style={local.head}>
        <View style={local.kind}>
          <Text style={[local.kindText, race && local.kindRace]}>
            {EVENT_KIND_LABELS[event.kind]}
            {race ? ` · prioridad ${race.priority}` : ''}
          </Text>
        </View>
        <View style={local.when}>
          <Text style={[styles.muted, local.whenText]}>{whenLabel(event)}</Text>
          {left ? <Text style={local.countdown}>{left}</Text> : null}
        </View>
      </View>

      {race ? (
        <View>
          <View style={local.ruled}>
            <StatStrip stats={raceStats} />
          </View>
          <View style={local.ruled}>
            <StatStrip stats={raceStats2} />
          </View>
        </View>
      ) : null}

      {race?.goal ? (
        <Section title="Objetivo">
          <Text style={styles.text}>{race.goal}</Text>
        </Section>
      ) : null}

      {event.training_impact !== 'none' ? (
        <Section title="Entrenamiento">
          <Text style={styles.text}>{TRAINING_IMPACT_LABELS[event.training_impact]}</Text>
        </Section>
      ) : null}

      <Section title="Notas">
        <Text style={event.notes ? styles.text : styles.muted}>{event.notes || 'Sin notas.'}</Text>
      </Section>

      {race ? (
        <Section title="Fuente">
          <InfoRow label="Datos de la carrera" value={ENRICHMENT_STATUS_LABELS[race.enrichment_status]} />
          {race.source_url ? (
            <Pressable
              onPress={() => void Linking.openURL(race.source_url as string)}
              accessibilityRole="link"
              style={({ pressed }) => [local.link, pressed && local.pressed]}
            >
              <Text style={[styles.textActive, local.linkText]} numberOfLines={1}>
                {race.source_url.replace(/^https?:\/\//i, '')}
              </Text>
              <Icon name="externalLink" size={16} color={colors.textActive} />
            </Pressable>
          ) : (
            <Text style={styles.muted}>Sin web oficial.</Text>
          )}
        </Section>
      ) : null}
    </Screen>
  );
}

const local = StyleSheet.create({
  head: { gap: spacing.sm, marginTop: -spacing.md },
  kind: { flexDirection: 'row' },
  kindText: { ...typography.label, color: colors.textSecondary },
  kindRace: { color: colors.textActive },
  when: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', gap: spacing.md },
  whenText: { flexShrink: 1 },
  countdown: { ...typography.smallBold, color: colors.text },
  ruled: { borderTopWidth: lines.hairline, borderTopColor: colors.separator, paddingVertical: spacing.sm + 2 },
  link: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.xs },
  pressed: { opacity: 0.7 },
  linkText: { flexShrink: 1 },
});
