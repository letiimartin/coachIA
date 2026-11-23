/**
 * Memoria del coach (#56). El coach sólo PROPONE lo que recordar; la atleta lo
 * confirma, lo corrige o lo descarta aquí, con los endpoints de memoria (nunca en el chat).
 */
import React, { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { MemoryKind, MemoryOut } from '../api/types';
import { Button, Chips, Field } from './components';
import { formatDate } from './dates';
import { MEMORY_KIND_LABELS, options } from './labels';
import { colors, lines, spacing, typography } from './theme';

const KIND_OPTIONS = options(MEMORY_KIND_LABELS);

/** Las acciones muestran su error en la pantalla y lo relanzan (así el elemento sigue editable). */
type ProposalActions = {
  /** Con `content`/`kind` si la atleta lo ha corregido. */
  onConfirm: (item: MemoryOut, correction?: { content: string; kind: MemoryKind }) => Promise<void>;
  onReject: (item: MemoryOut) => Promise<void>;
};

type ConfirmedActions = {
  onSave: (item: MemoryOut, change: { content: string; kind: MemoryKind }) => Promise<void>;
  onDelete: (item: MemoryOut) => Promise<void>;
};

type MemoryItemProps = {
  item: MemoryOut;
  first?: boolean;
  /** false si ya va dentro de un grupo de su tipo. */
  showKind?: boolean;
} & (
  | ({ mode: 'proposal' } & ProposalActions)
  | ({ mode: 'confirmed' } & ConfirmedActions)
);

function metaText(item: MemoryOut): string {
  if (item.status === 'proposed') return 'Propuesto por el coach';
  const who = item.source === 'athlete' ? 'Añadido por ti' : 'Propuesto por el coach';
  return item.confirmed_at ? `${who} · confirmado el ${formatDate(item.confirmed_at)}` : who;
}

/** Un elemento de memoria con su edición en línea. */
export function MemoryItem(props: MemoryItemProps) {
  const { item, first, showKind = true } = props;
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(item.content);
  const [kind, setKind] = useState<MemoryKind>(item.kind);
  const [busy, setBusy] = useState<null | 'confirm' | 'reject' | 'save' | 'delete'>(null);

  const run = async (action: NonNullable<typeof busy>, fn: () => Promise<void>) => {
    setBusy(action);
    try {
      await fn();
      setEditing(false);
    } catch {
      // La pantalla muestra el error; se sigue editando para poder reintentar.
    } finally {
      setBusy(null);
    }
  };

  const startEdit = () => {
    setContent(item.content);
    setKind(item.kind);
    setEditing(true);
  };

  const trimmed = content.trim();
  const changed = trimmed !== item.content || kind !== item.kind;

  if (editing) {
    const isProposal = props.mode === 'proposal';
    return (
      <View style={[styles.item, first && styles.first]}>
        <Chips label="Tipo" options={KIND_OPTIONS} value={kind} onChange={setKind} />
        <Field label="Qué debe recordar el coach" value={content} onChangeText={setContent} multiline />
        <View style={styles.actions}>
          <Button
            title={isProposal ? 'Confirmar corregido' : 'Guardar'}
            disabled={!trimmed || (!isProposal && !changed)}
            loading={busy === 'confirm' || busy === 'save'}
            onPress={() =>
              props.mode === 'proposal'
                ? void run('confirm', () => props.onConfirm(item, changed ? { content: trimmed, kind } : undefined))
                : void run('save', () => props.onSave(item, { content: trimmed, kind }))
            }
          />
          <Button title="Cancelar" variant="text" disabled={!!busy} onPress={() => setEditing(false)} />
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.item, first && styles.first]}>
      {showKind ? <Text style={styles.kind}>{MEMORY_KIND_LABELS[item.kind]}</Text> : null}
      <Text style={styles.content} selectable>
        {item.content}
      </Text>
      <Text style={styles.meta}>{metaText(item)}</Text>
      <View style={styles.actions}>
        {props.mode === 'proposal' ? (
          <>
            <Button title="Confirmar" loading={busy === 'confirm'} disabled={!!busy} onPress={() => void run('confirm', () => props.onConfirm(item))} />
            <Button title="Corregir" variant="text" disabled={!!busy} onPress={startEdit} />
            <Button title="Descartar" variant="danger" loading={busy === 'reject'} disabled={!!busy} onPress={() => void run('reject', () => props.onReject(item))} />
          </>
        ) : (
          <>
            <Button title="Corregir" variant="text" disabled={!!busy} onPress={startEdit} />
            <Button title="Borrar" variant="danger" loading={busy === 'delete'} disabled={!!busy} onPress={() => void run('delete', () => props.onDelete(item))} />
          </>
        )}
      </View>
    </View>
  );
}

/**
 * Lo que el coach propone recordar, bajo su mensaje (p. ej. el resumen final de la toma de
 * contacto): cada punto se confirma, se corrige o se descarta.
 */
export function MemoryProposals({ items, onConfirm, onReject, onConfirmAll }: { items: MemoryOut[]; onConfirmAll?: () => Promise<void> } & ProposalActions) {
  const [confirmingAll, setConfirmingAll] = useState(false);
  if (!items.length) return null;
  return (
    <View style={styles.proposals}>
      <Text style={styles.label}>Para recordar · revisa y confirma</Text>
      {items.map((item, i) => (
        <MemoryItem key={item.id} item={item} first={i === 0} mode="proposal" onConfirm={onConfirm} onReject={onReject} />
      ))}
      {onConfirmAll && items.length > 1 ? (
        <View style={styles.confirmAll}>
          <Button
            title="Confirmar todo"
            variant="secondary"
            loading={confirmingAll}
            onPress={async () => {
              setConfirmingAll(true);
              try {
                await onConfirmAll();
              } catch {
                // La pantalla muestra el error.
              } finally {
                setConfirmingAll(false);
              }
            }}
          />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  proposals: { marginTop: spacing.md, paddingTop: spacing.md, borderTopWidth: lines.hairline, borderTopColor: colors.separatorStrong, gap: spacing.xs },
  label: { ...typography.label, color: colors.textSecondary },
  item: { gap: spacing.xs, paddingVertical: spacing.md, borderTopWidth: lines.hairline, borderTopColor: colors.separator },
  first: { borderTopWidth: 0 },
  kind: { ...typography.label, color: colors.textActive },
  content: { ...typography.body, color: colors.text },
  meta: { ...typography.caption, color: colors.textSecondary },
  actions: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: spacing.md, paddingTop: spacing.xs },
  confirmAll: { flexDirection: 'row', paddingTop: spacing.xs },
});
