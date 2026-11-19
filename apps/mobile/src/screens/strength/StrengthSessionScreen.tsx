/**
 * Sesión de fuerza (Fuerza 2, #31), con la composición de la v3: etiqueta y título, cifras en tira y
 * ejercicios en filas con filete, sin tarjetas.
 *
 * - Cada ejercicio muestra lo planificado (3 × 10…) y, debajo, la última vez que se hizo antes de esta
 *   sesión (la API la toma como referencia, también si ya está hecha, #52).
 * - Cada serie se marca como hecha; las repeticiones o segundos vienen precargados con lo planificado y
 *   el peso es opcional. RPE y RIR por serie, ocultos por defecto.
 * - Las series se guardan solas en la API (`PUT /sets`, siempre la lista completa) y en una copia local,
 *   así que se puede dejar a medias y retomar.
 * - Al terminar se envían la hora de inicio, la duración y, si se indica, el RPE; la API crea la
 *   actividad de fuerza y, con RPE, calcula su carga `session_rpe`. Sin RPE no hay carga (#52).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { errorText } from '../../api/errors';
import { strengthApi } from '../../api/strengthApi';
import type { ExerciseLastLogOut, StrengthSetIn, StrengthWorkoutOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { localDay, localTime, longDayLabel } from '../../ui/calendarDates';
import { Button, Chips, Field, Loading, Screen, Section, styles } from '../../ui/components';
import { isValidTime, localDateTimeToIso, todayIsoDate } from '../../ui/dates';
import { Icon } from '../../ui/Icon';
import { formatDuration } from '../../ui/plannedWorkouts';
import { StatStrip, type Stat } from '../../ui/StatStrip';
import { StrengthSetRow, type SetRowField } from '../../ui/StrengthSetRow';
import { colors, lines, spacing, typography } from '../../ui/theme';
import { clearSession, readSession, writeSession } from './sessionStore';
import {
  buildSetsPayload,
  countSets,
  draftsFromWorkout,
  draftsMatchWorkout,
  extraSets,
  invalidFields,
  lastLogLabel,
  targetLabel,
  type Drafts,
} from './strengthSets';

type Props = NativeStackScreenProps<RootStackParamList, 'StrengthSession'>;

type SaveState = 'saved' | 'dirty' | 'saving' | 'invalid' | 'error';

const SAVE_DELAY_MS = 1000;
const RPE_OPTIONS = Array.from({ length: 10 }, (_, i) => ({ value: String(i + 1), label: String(i + 1) }));

const SAVE_TEXT: Record<SaveState, string> = {
  saved: 'Guardado',
  dirty: 'Cambios sin guardar',
  saving: 'Guardando…',
  invalid: 'Revisa los valores marcados en rojo',
  error: 'No se ha podido guardar',
};

/** Minutos enteros desde `startedAt` (null si no hay hora de inicio o pasa de un día). */
function minutesSince(startedAt: string | null): number | null {
  if (!startedAt) return null;
  const minutes = Math.round((Date.now() - new Date(startedAt).getTime()) / 60_000);
  return minutes > 0 && minutes <= 24 * 60 ? minutes : null;
}

export default function StrengthSessionScreen({ navigation, route }: Props) {
  const { id } = route.params;
  const scrollRef = useRef<ScrollView>(null);

  const [workout, setWorkout] = useState<StrengthWorkoutOut | null>(null);
  const [drafts, setDraftsState] = useState<Drafts>({});
  const [lastLogs, setLastLogs] = useState<Record<string, ExerciseLastLogOut>>({});
  const [lastLogsLoaded, setLastLogsLoaded] = useState(false);
  const [showEffort, setShowEffort] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>('saved');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [finishing, setFinishing] = useState(false);
  const [startTime, setStartTime] = useState('');
  const [durationMin, setDurationMin] = useState('');
  const [sessionRpe, setSessionRpe] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);

  // Estado que necesita el guardado fuera del ciclo de render (temporizador y desmontaje).
  const draftsRef = useRef<Drafts>({});
  const extrasRef = useRef<StrengthSetIn[]>([]);
  const serverUpdatedAtRef = useRef('');
  const startedAtRef = useRef<string | null>(null);
  const dirtyRef = useRef(false);
  const savingRef = useRef<Promise<boolean> | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const persist = useCallback(
    (unsaved: boolean) =>
      writeSession(id, { drafts: draftsRef.current, unsaved, serverUpdatedAt: serverUpdatedAtRef.current, startedAt: startedAtRef.current }),
    [id],
  );

  /** Envía la lista completa de series si hay cambios. Devuelve false si no se ha podido guardar. */
  const save = useCallback(async (): Promise<boolean> => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    while (savingRef.current) await savingRef.current;
    if (!dirtyRef.current) return true;
    const payload = buildSetsPayload(draftsRef.current, extrasRef.current);
    if (!payload) {
      if (mountedRef.current) setSaveState('invalid');
      return false;
    }
    dirtyRef.current = false;
    if (mountedRef.current) setSaveState('saving');
    const run = (async () => {
      try {
        const updated = await strengthApi.replaceSets(id, payload);
        serverUpdatedAtRef.current = updated.updated_at;
        extrasRef.current = extraSets(updated);
        if (mountedRef.current) setWorkout(updated);
        if (!dirtyRef.current) {
          await persist(false);
          if (mountedRef.current) setSaveState('saved');
        }
        return true;
      } catch (e) {
        dirtyRef.current = true;
        await persist(true);
        if (mountedRef.current) {
          setSaveState('error');
          setError(errorText(e));
        }
        return false;
      }
    })();
    savingRef.current = run;
    try {
      return await run;
    } finally {
      savingRef.current = null;
    }
  }, [id, persist]);

  const scheduleSave = useCallback(
    (delay = SAVE_DELAY_MS) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => void save(), delay);
    },
    [save],
  );

  const setDrafts = (next: Drafts) => {
    draftsRef.current = next;
    setDraftsState(next);
    dirtyRef.current = true;
    setSaveState(buildSetsPayload(next, extrasRef.current) ? 'dirty' : 'invalid');
    void persist(true);
  };

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const [w, stored] = await Promise.all([strengthApi.getWorkout(id), readSession(id)]);
      // La copia local manda si tiene cambios sin enviar o si la API no ha cambiado desde que se guardó.
      const useStored = !!stored && draftsMatchWorkout(stored.drafts, w) && (stored.unsaved || stored.serverUpdatedAt === w.updated_at);
      const initial = useStored && stored ? stored.drafts : draftsFromWorkout(w);
      if (!mountedRef.current) return;
      draftsRef.current = initial;
      extrasRef.current = extraSets(w);
      serverUpdatedAtRef.current = w.updated_at;
      startedAtRef.current = w.status === 'planned' ? (stored?.startedAt ?? null) : null;
      setWorkout(w);
      setDraftsState(initial);
      setShowEffort(Object.values(initial).some((list) => list.some((d) => d.rpe !== '' || d.rir !== '')));
      if (useStored && stored?.unsaved && w.status !== 'skipped') {
        dirtyRef.current = true;
        void save();
      }
      const exerciseIds = [...new Set(w.exercises.map((e) => e.exercise.id))];
      const results = await Promise.allSettled(exerciseIds.map((exerciseId) => strengthApi.lastLog(exerciseId, w.id)));
      if (!mountedRef.current) return;
      const logs: Record<string, ExerciseLastLogOut> = {};
      results.forEach((r) => {
        if (r.status === 'fulfilled') logs[r.value.exercise.id] = r.value;
      });
      setLastLogs(logs);
      setLastLogsLoaded(true);
    } catch (e) {
      if (mountedRef.current) setLoadError(errorText(e));
    }
  }, [id, save]);

  useEffect(() => {
    mountedRef.current = true;
    void load();
    return () => {
      mountedRef.current = false;
      // Al salir, lo pendiente se envía sin esperar.
      if (dirtyRef.current) void save();
    };
    // Sólo al abrir la pantalla: recargar al enfocar pisaría lo que se está escribiendo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!workout) {
    return (
      // El mismo `scrollRef` que la pantalla cargada: en web, ScrollView no cambia de ref entre renders.
      <Screen title="Sesión de fuerza" onBack={() => navigation.goBack()} error={loadError} onDismissError={() => void load()} scrollRef={scrollRef}>
        {loadError ? <Button title="Reintentar" variant="secondary" onPress={() => void load()} /> : <Loading />}
      </Screen>
    );
  }

  const editable = workout.status !== 'skipped';
  const done = workout.status === 'done';
  const { done: setsDone, total: setsTotal } = countSets(drafts);

  const updateSet = (plannedId: string, index: number, change: (d: Drafts[string][number]) => Drafts[string][number]) => {
    const list = drafts[plannedId].map((d, i) => (i === index ? change(d) : d));
    setDrafts({ ...drafts, [plannedId]: list });
  };

  const toggleSet = (plannedId: string, index: number) => {
    updateSet(plannedId, index, (d) => ({ ...d, status: d.status === 'done' ? 'pending' : 'done' }));
    if (workout.status === 'planned' && !startedAtRef.current) startedAtRef.current = new Date().toISOString();
    scheduleSave(300);
  };

  const changeField = (plannedId: string, index: number, field: SetRowField, text: string) => {
    updateSet(plannedId, index, (d) => ({ ...d, [field]: text }));
    scheduleSave();
  };

  const openFinish = () => {
    const started = startedAtRef.current;
    setStartTime(started ? localTime(started) : '');
    const minutes = minutesSince(started);
    setDurationMin(minutes != null ? String(minutes) : '');
    setFinishing(true);
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
  };

  const minutes = /^\d+$/.test(durationMin.trim()) ? Number(durationMin.trim()) : NaN;
  const finishValid = isValidTime(startTime.trim()) && minutes >= 1 && minutes <= 24 * 60;

  const complete = async () => {
    if (!finishValid) return;
    setCompleting(true);
    setError(null);
    try {
      if (!(await save())) {
        setError('Antes de terminar hay que guardar las series. Revisa los valores marcados o la conexión.');
        return;
      }
      const day = startedAtRef.current ? localDay(startedAtRef.current) : todayIsoDate();
      const updated = await strengthApi.complete(id, {
        started_at: localDateTimeToIso(day, startTime.trim()),
        duration_s: minutes * 60,
        rpe: sessionRpe != null ? Number(sessionRpe) : null,
      });
      startedAtRef.current = null;
      serverUpdatedAtRef.current = updated.updated_at;
      await clearSession(id);
      setWorkout(updated);
      setFinishing(false);
      // Tras el render sin el formulario, se vuelve arriba para ver el resumen de la sesión hecha.
      setTimeout(() => scrollRef.current?.scrollTo({ y: 0, animated: true }), 50);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setCompleting(false);
    }
  };

  const activity = workout.activity;
  // Sin RPE no hay carga: no se muestra ninguna cifra de carga (#52).
  const stats: Stat[] = done
    ? [
        { value: activity?.elapsed_s ? formatDuration(activity.elapsed_s) : '—', caption: 'Duración' },
        { value: activity?.rpe != null ? String(activity.rpe) : '—', caption: 'RPE de la sesión' },
        ...(activity?.load != null ? [{ value: String(Math.round(activity.load)), caption: 'Carga (sRPE)' }] : []),
      ]
    : [
        { value: String(workout.exercises.length), caption: workout.exercises.length === 1 ? 'Ejercicio' : 'Ejercicios' },
        { value: `${setsDone}/${setsTotal}`, caption: 'Series hechas' },
      ];

  const footer = editable ? (
    <View style={local.footer}>
      <View style={local.footerStatus}>
        <Text style={[local.saveText, (saveState === 'error' || saveState === 'invalid') && local.saveError]} accessibilityLiveRegion="polite">
          {SAVE_TEXT[saveState]}
        </Text>
        {saveState === 'error' ? <Button title="Reintentar" variant="text" onPress={() => void save()} /> : null}
      </View>
      {!done && !finishing ? <Button title="Terminar sesión" onPress={openFinish} /> : null}
    </View>
  ) : null;

  return (
    <Screen
      title={workout.title}
      eyebrow={`Fuerza · ${longDayLabel(workout.scheduled_on)}${done ? ' · hecha' : workout.status === 'skipped' ? ' · saltada' : ''}`}
      onBack={() => navigation.goBack()}
      error={error}
      onDismissError={() => setError(null)}
      footer={footer}
      scrollRef={scrollRef}
    >
      <StatStrip stats={stats} />
      {workout.status === 'skipped' ? <Text style={styles.muted}>Esta sesión está marcada como saltada: no se pueden registrar series.</Text> : null}

      <Section
        title="Ejercicios"
        right={
          editable ? <Button title={showEffort ? 'Ocultar RPE y RIR' : 'Anotar RPE y RIR'} variant="text" onPress={() => setShowEffort(!showEffort)} /> : null
        }
      >
        {workout.exercises.length === 0 ? <Text style={styles.muted}>Esta sesión no tiene ejercicios.</Text> : null}
        {workout.exercises.map((planned, i) => {
          const list = drafts[planned.id] ?? [];
          const lastLog = lastLogs[planned.exercise.id];
          const last = lastLogLabel(lastLog, workout.id);
          const substituted = list.some((d) => d.exerciseId != null);
          return (
            <View key={planned.id} style={[local.exercise, i > 0 && local.exerciseRuled]}>
              <View style={local.exerciseHeader}>
                <Text style={local.position}>{planned.position}</Text>
                <View style={local.exerciseText}>
                  <Text style={local.exerciseName}>{planned.exercise.name}</Text>
                  <Text style={local.target}>{targetLabel(planned)}</Text>
                  {planned.notes ? <Text style={styles.muted}>{planned.notes}</Text> : null}
                </View>
              </View>
              {lastLogsLoaded ? (
                <View style={local.last}>
                  <Icon name="lastLog" size={14} color={colors.textSecondary} />
                  <Text style={local.lastText}>{last ? `Última vez · ${last}` : 'Sin registros anteriores'}</Text>
                </View>
              ) : null}
              {substituted ? <Text style={local.lastText}>Alguna serie se registró con otro ejercicio (sustitución).</Text> : null}
              <View>
                {list.map((d, index) => (
                  <StrengthSetRow
                    key={d.setNumber}
                    setNumber={d.setNumber}
                    done={d.status === 'done'}
                    failed={d.status === 'failed'}
                    unit={d.mode === 'seconds' ? 's' : 'rep.'}
                    values={{ value: d.value, weight: d.weight, rpe: d.rpe, rir: d.rir }}
                    invalid={invalidFields(d)}
                    showEffort={showEffort}
                    disabled={!editable}
                    onToggle={() => toggleSet(planned.id, index)}
                    onChange={(field, text) => changeField(planned.id, index, field, text)}
                  />
                ))}
              </View>
            </View>
          );
        })}
        {extrasRef.current.length > 0 ? (
          <Text style={styles.muted}>
            {extrasRef.current.length === 1 ? 'Hay 1 serie extra' : `Hay ${extrasRef.current.length} series extra`} registrada fuera de lo planificado; se conserva.
          </Text>
        ) : null}
      </Section>

      {workout.coach_reason ? (
        <Section title="Por qué hoy">
          <Text style={styles.text}>{workout.coach_reason}</Text>
        </Section>
      ) : null}

      {finishing && !done ? (
        <Section title="Terminar la sesión">
          {setsDone === 0 ? <Text style={styles.muted}>Todavía no has marcado ninguna serie como hecha.</Text> : null}
          <View style={local.finishRow}>
            <View style={local.finishField}>
              <Field label="Hora de inicio" value={startTime} onChangeText={setStartTime} placeholder="18:30" keyboardType="numbers-and-punctuation" />
            </View>
            <View style={local.finishField}>
              <Field label="Duración (min)" value={durationMin} onChangeText={setDurationMin} placeholder="50" keyboardType="number-pad" />
            </View>
          </View>
          <Chips label="RPE de la sesión (1–10, opcional)" options={RPE_OPTIONS} value={sessionRpe} onChange={setSessionRpe} allowNone />
          <Text style={local.hint}>
            Con RPE, la API calcula la carga de la sesión (minutos × RPE). Sin RPE, la sesión se guarda como hecha con todas sus series, pero sin carga.
          </Text>
          <View style={local.finishActions}>
            <Button title="Guardar y terminar" onPress={() => void complete()} disabled={!finishValid} loading={completing} />
            <Button title="Cancelar" variant="text" onPress={() => setFinishing(false)} />
          </View>
        </Section>
      ) : null}
    </Screen>
  );
}

const local = StyleSheet.create({
  exercise: { gap: spacing.sm, paddingTop: spacing.xs },
  exerciseRuled: { paddingTop: spacing.lg, borderTopWidth: lines.hairline, borderTopColor: colors.separatorStrong },
  exerciseHeader: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
  position: { ...typography.heading, color: colors.textSecondary, width: 32, fontVariant: ['tabular-nums'] },
  exerciseText: { flex: 1, minWidth: 0, gap: spacing.xxs },
  exerciseName: { ...typography.bodyBold, color: colors.text },
  target: { ...typography.smallBold, color: colors.textActive, fontVariant: ['tabular-nums'] },
  last: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.xs, paddingLeft: 32 + spacing.md },
  lastText: { ...typography.caption, color: colors.textSecondary, flexShrink: 1 },
  hint: { ...typography.caption, color: colors.textSecondary },
  finishRow: { flexDirection: 'row', gap: spacing.md },
  finishField: { flex: 1, minWidth: 0 },
  finishActions: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md },
  footerStatus: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, flexShrink: 1 },
  saveText: { ...typography.small, color: colors.textSecondary, flexShrink: 1 },
  saveError: { color: colors.danger },
});
