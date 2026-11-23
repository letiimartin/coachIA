/**
 * «Lo que el coach sabe de mí» (#56): la memoria confirmada, por tipo, que se puede corregir o
 * borrar, y lo que el coach ha propuesto y falta por revisar. La atleta también puede añadir algo.
 */
import React, { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { coachApi } from '../../api/coachApi';
import { errorText } from '../../api/errors';
import type { MemoryKind, MemoryOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { MemoryItem, MemoryProposals } from '../../ui/CoachMemory';
import { Button, Chips, Field, Loading, Screen, Section, styles as base } from '../../ui/components';
import { confirm } from '../../ui/confirm';
import { MEMORY_KIND_LABELS, options } from '../../ui/labels';
import { spacing } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = NativeStackScreenProps<RootStackParamList, 'CoachMemory'>;

const GROUPS: { kind: MemoryKind; title: string }[] = [
  { kind: 'goal', title: 'Objetivos' },
  { kind: 'preference', title: 'Preferencias' },
  { kind: 'other', title: 'Otros' },
];

type Data = { confirmed: MemoryOut[]; proposed: MemoryOut[] };

export default function CoachMemoryScreen({ navigation }: Props) {
  const load = useCallback(async (): Promise<Data> => {
    const [confirmed, proposed] = await Promise.all([coachApi.listMemory('confirmed'), coachApi.listMemory('proposed')]);
    return { confirmed, proposed };
  }, []);
  const { data, setData, loading, error, setError, reload } = useFocusLoad(load);
  const [kind, setKind] = useState<MemoryKind>('goal');
  const [content, setContent] = useState('');
  const [adding, setAdding] = useState(false);

  /** Ejecuta una acción, muestra su error y lo relanza (el elemento sigue editable). */
  const act = async <T,>(fn: () => Promise<T>): Promise<T> => {
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(errorText(e));
      throw e;
    }
  };

  const replace = (item: MemoryOut) =>
    setData((d) => d && { ...d, confirmed: d.confirmed.map((m) => (m.id === item.id ? item : m)) });

  const onSave = async (item: MemoryOut, change: { content: string; kind: MemoryKind }) => {
    replace(await act(() => coachApi.updateMemory(item.id, change)));
  };

  const onDelete = async (item: MemoryOut) => {
    if (!(await confirm('Borrar', `El coach dejará de tener en cuenta: «${item.content}».`, 'Borrar'))) return;
    await act(() => coachApi.deleteMemory(item.id));
    setData((d) => d && { ...d, confirmed: d.confirmed.filter((m) => m.id !== item.id) });
  };

  const onConfirm = async (item: MemoryOut, correction?: { content: string; kind: MemoryKind }) => {
    const saved = await act(() => coachApi.confirmMemory(item.id, correction ?? {}));
    setData((d) => d && { confirmed: [...d.confirmed, saved], proposed: d.proposed.filter((m) => m.id !== item.id) });
  };

  const onReject = async (item: MemoryOut) => {
    await act(() => coachApi.rejectMemory(item.id));
    setData((d) => d && { ...d, proposed: d.proposed.filter((m) => m.id !== item.id) });
  };

  const onAdd = async () => {
    const text = content.trim();
    if (!text) return;
    setAdding(true);
    try {
      const created = await act(() => coachApi.createMemory({ kind, content: text }));
      setData((d) => d && { ...d, confirmed: [...d.confirmed, created] });
      setContent('');
    } catch {
      // El error ya se muestra arriba.
    } finally {
      setAdding(false);
    }
  };

  return (
    <Screen
      title="Lo que el coach sabe de mí"
      eyebrow="Coach · memoria"
      onBack={() => navigation.goBack()}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={reload}
    >
      <Text style={base.muted}>
        El coach sólo tiene en cuenta lo que has confirmado. Corrige o borra lo que ya no sea así; tus datos de entrenamiento, umbrales y calendario
        los lee directamente de la app.
      </Text>
      {loading && !data ? <Loading /> : null}
      {data && data.proposed.length > 0 ? (
        <Section title="Pendiente de revisar">
          <MemoryProposals
            items={data.proposed}
            onConfirm={onConfirm}
            onReject={onReject}
            onConfirmAll={async () => {
              for (const item of data.proposed) await onConfirm(item);
            }}
          />
        </Section>
      ) : null}
      {data && data.confirmed.length === 0 ? (
        <Text style={base.muted}>Todavía no hay nada confirmado. Lo que el coach te proponga recordar aparecerá aquí cuando lo confirmes.</Text>
      ) : null}
      {data
        ? GROUPS.map(({ kind: k, title }) => {
            const items = data.confirmed.filter((m) => m.kind === k);
            if (!items.length) return null;
            return (
              <Section key={k} title={title}>
                <View>
                  {items.map((item, i) => (
                    <MemoryItem key={`${item.id}-${item.updated_at}`} item={item} first={i === 0} showKind={false} mode="confirmed" onSave={onSave} onDelete={onDelete} />
                  ))}
                </View>
              </Section>
            );
          })
        : null}
      {data ? (
        <Section title="Añadir">
          <View style={styles.form}>
            <Chips label="Tipo" options={options(MEMORY_KIND_LABELS)} value={kind} onChange={setKind} />
            <Field
              label="Qué quieres que recuerde"
              value={content}
              onChangeText={setContent}
              multiline
              placeholder="Por ejemplo: los jueves no puedo entrenar por la tarde."
            />
            <View style={styles.actions}>
              <Button title="Añadir" onPress={() => void onAdd()} loading={adding} disabled={!content.trim()} />
            </View>
          </View>
        </Section>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  form: { gap: spacing.md },
  actions: { flexDirection: 'row' },
});
