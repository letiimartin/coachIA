import React, { useState } from 'react';
import { Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { calendarApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import type {
  CalendarEventCreate,
  CalendarEventOut,
  CalendarEventPatch,
  EventKind,
  RaceCreate,
  RaceDiscipline,
  RacePriority,
  TrainingImpact,
} from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Section, Chips, Field, Screen, styles, SwitchField } from '../../ui/components';
import { confirm } from '../../ui/confirm';
import { isoToLocalParts, isValidIsoDate, isValidTime, localDateTimeToIso, todayIsoDate } from '../../ui/dates';
import { parseOptionalNumber } from '../../ui/forms';
import {
  ENRICHMENT_STATUS_LABELS,
  EVENT_KIND_LABELS,
  options,
  RACE_DISCIPLINE_LABELS,
  RACE_PRIORITY_LABELS,
  TRAINING_IMPACT_LABELS,
} from '../../ui/labels';

type Props = NativeStackScreenProps<RootStackParamList, 'EventForm'>;

type Form = {
  kind: EventKind;
  title: string;
  all_day: boolean;
  start_date: string;
  start_time: string;
  end_date: string;
  end_time: string;
  training_impact: TrainingImpact;
  notes: string;
  discipline: RaceDiscipline | null;
  distance_km: string;
  ascent_m: string;
  priority: RacePriority;
  goal: string;
  source_url: string;
};

function toForm(event?: CalendarEventOut): Form {
  const start = event ? isoToLocalParts(event.start_at) : { date: todayIsoDate(), time: '09:00' };
  const end = event?.end_at ? isoToLocalParts(event.end_at) : null;
  const race = event?.race;
  return {
    kind: event?.kind ?? 'race',
    title: event?.title ?? '',
    all_day: event?.all_day ?? true,
    start_date: start.date,
    start_time: start.time,
    end_date: end?.date ?? '',
    end_time: end?.time ?? '',
    training_impact: event?.training_impact ?? 'none',
    notes: event?.notes ?? '',
    discipline: race?.discipline ?? null,
    distance_km: race?.distance_m != null ? String(race.distance_m / 1000) : '',
    ascent_m: race?.ascent_m != null ? String(race.ascent_m) : '',
    priority: race?.priority ?? 'B',
    goal: race?.goal ?? '',
    source_url: race?.source_url ?? '',
  };
}

type Built = Omit<CalendarEventCreate, 'race'> & { race: RaceCreate | null; end_at: string | null; notes: string | null };

/** Valida el formulario y construye el evento con las fechas en ISO 8601 con desfase. */
function build(form: Form): Built | string {
  const title = form.title.trim();
  if (!title) return 'El título es obligatorio.';
  if (title.length > 200) return 'El título no puede superar los 200 caracteres.';
  if (!isValidIsoDate(form.start_date)) return 'La fecha de inicio debe tener el formato AAAA-MM-DD.';
  if (!form.all_day && !isValidTime(form.start_time)) return 'La hora de inicio debe tener el formato HH:MM.';
  const startAt = localDateTimeToIso(form.start_date, form.all_day ? '00:00' : form.start_time);

  let endAt: string | null = null;
  if (form.end_date.trim()) {
    if (!isValidIsoDate(form.end_date)) return 'La fecha de fin debe tener el formato AAAA-MM-DD.';
    const endTime = form.all_day ? '23:59' : form.end_time.trim() || form.start_time;
    if (!isValidTime(endTime)) return 'La hora de fin debe tener el formato HH:MM.';
    endAt = localDateTimeToIso(form.end_date, endTime);
    if (new Date(endAt) < new Date(startAt)) return 'La fecha de fin no puede ser anterior a la de inicio.';
  }
  const notes = form.notes.trim() || null;
  if (notes && notes.length > 5000) return 'Las notas no pueden superar los 5000 caracteres.';

  let race: RaceCreate | null = null;
  if (form.kind === 'race') {
    const km = parseOptionalNumber(form.distance_km);
    if (km !== null && (Number.isNaN(km) || km < 0)) return 'La distancia debe ser un número positivo (km).';
    const ascent = parseOptionalNumber(form.ascent_m);
    if (ascent !== null && (Number.isNaN(ascent) || ascent < 0)) return 'El desnivel debe ser un número positivo (m).';
    const url = form.source_url.trim();
    if (url && !/^https?:\/\/\S+$/i.test(url)) return 'La web de la carrera debe empezar por http:// o https://.';
    const goal = form.goal.trim();
    if (goal.length > 2000) return 'El objetivo no puede superar los 2000 caracteres.';
    race = {
      discipline: form.discipline,
      distance_m: km === null ? null : Math.round(km * 1000),
      ascent_m: ascent,
      priority: form.priority,
      goal: goal || null,
      source_url: url || null,
    };
  }

  return {
    kind: form.kind,
    title,
    all_day: form.all_day,
    start_at: startAt,
    end_at: endAt,
    training_impact: form.training_impact,
    notes,
    race,
  };
}

export default function EventFormScreen({ navigation, route }: Props) {
  const event = route.params?.event;
  const [form, setForm] = useState<Form>(() => toForm(event));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<'save' | 'delete' | 'confirm' | null>(null);

  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((f) => ({ ...f, [key]: value }));

  const run = async (kind: 'save' | 'delete' | 'confirm', action: () => Promise<unknown>) => {
    setBusy(kind);
    setError(null);
    try {
      await action();
      navigation.goBack();
    } catch (e) {
      setError(errorText(e));
      setBusy(null);
    }
  };

  const save = () => {
    const built = build(form);
    if (typeof built === 'string') return setError(built);
    if (!event) {
      const body: CalendarEventCreate = { ...built, race: built.race ?? undefined };
      return run('save', () => calendarApi.createEvent(body));
    }
    // Se envían todos los campos editables; `race` se fusiona con los datos existentes.
    const patch: CalendarEventPatch = { ...built, race: built.race ?? undefined };
    return run('save', () => calendarApi.updateEvent(event.id, patch));
  };

  const remove = async () => {
    if (!event) return;
    const ok = await confirm('Borrar evento', `¿Seguro que quieres borrar «${event.title}»?`, 'Borrar');
    if (ok) await run('delete', () => calendarApi.deleteEvent(event.id));
  };

  const confirmRaceData = () => {
    if (!event) return;
    void run('confirm', () => calendarApi.updateEvent(event.id, { race: { enrichment_status: 'confirmed' } }));
  };

  return (
    <Screen error={error} onDismissError={() => setError(null)} title={event ? 'Editar evento' : 'Nuevo evento'} onBack={navigation.goBack}>
      <Section>
        <Chips label="Tipo" options={options(EVENT_KIND_LABELS)} value={form.kind} onChange={(v) => set('kind', v)} />
        <Field label="Título" value={form.title} onChangeText={(v) => set('title', v)} />
        <SwitchField label="Todo el día" value={form.all_day} onValueChange={(v) => set('all_day', v)} />
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <View style={{ flex: 2 }}>
            <Field label="Inicio" value={form.start_date} onChangeText={(v) => set('start_date', v)} placeholder="AAAA-MM-DD" />
          </View>
          {!form.all_day ? (
            <View style={{ flex: 1 }}>
              <Field label="Hora" value={form.start_time} onChangeText={(v) => set('start_time', v)} placeholder="HH:MM" />
            </View>
          ) : null}
        </View>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <View style={{ flex: 2 }}>
            <Field label="Fin (opcional)" value={form.end_date} onChangeText={(v) => set('end_date', v)} placeholder="AAAA-MM-DD" />
          </View>
          {!form.all_day ? (
            <View style={{ flex: 1 }}>
              <Field label="Hora" value={form.end_time} onChangeText={(v) => set('end_time', v)} placeholder="HH:MM" />
            </View>
          ) : null}
        </View>
        <Chips
          label="Impacto en el entrenamiento"
          options={options(TRAINING_IMPACT_LABELS)}
          value={form.training_impact}
          onChange={(v) => set('training_impact', v)}
        />
        <Field label="Notas" value={form.notes} onChangeText={(v) => set('notes', v)} multiline />
      </Section>

      {form.kind === 'race' ? (
        <Section title="Datos de la carrera">
          {event?.race ? <Text style={styles.muted}>Estado: {ENRICHMENT_STATUS_LABELS[event.race.enrichment_status]}</Text> : null}
          {event?.race?.enrichment_status === 'pending_review' ? (
            <Button title="Confirmar datos completados" variant="secondary" onPress={confirmRaceData} loading={busy === 'confirm'} disabled={!!busy} />
          ) : null}
          <Chips label="Disciplina" options={options(RACE_DISCIPLINE_LABELS)} value={form.discipline} onChange={(v) => set('discipline', v)} allowNone />
          <Field label="Distancia (km)" value={form.distance_km} onChangeText={(v) => set('distance_km', v)} keyboardType="decimal-pad" />
          <Field label="Desnivel positivo (m)" value={form.ascent_m} onChangeText={(v) => set('ascent_m', v)} keyboardType="number-pad" />
          <Chips label="Prioridad" options={options(RACE_PRIORITY_LABELS)} value={form.priority} onChange={(v) => set('priority', v)} />
          <Field label="Objetivo" value={form.goal} onChangeText={(v) => set('goal', v)} multiline />
          <Field label="Web oficial" value={form.source_url} onChangeText={(v) => set('source_url', v)} placeholder="https://…" keyboardType="url" />
        </Section>
      ) : null}

      <Button title={event ? 'Guardar cambios' : 'Crear evento'} onPress={save} loading={busy === 'save'} disabled={!!busy} />
      {event ? <Button title="Borrar evento" variant="danger" onPress={remove} loading={busy === 'delete'} disabled={!!busy} /> : null}
    </Screen>
  );
}
