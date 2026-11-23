/**
 * Piezas de la conversación con el coach (propuesta v3, #56): mensajes sin contenedores (los
 * propios en `surfaceSoft`), etiqueta de día centrada, estado «pensando», sugerencias y caja de
 * texto fija abajo con el botón de enviar.
 */
import React from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type NativeSyntheticEvent,
  type TextInputKeyPressEventData,
} from 'react-native';

import type { MessageOrigin } from '../api/types';
import { Icon } from './Icon';
import { colors, layout, lines, radius, spacing, typography } from './theme';

/**
 * Texto del coach para mostrar sin Markdown: viñetas «- »/«* » como «• » y sin `**`. No cambia
 * el contenido.
 */
export function plainText(content: string): string {
  return content.replace(/^(\s*)[-*]\s+/gm, '$1• ').replace(/\*\*(.+?)\*\*/g, '$1');
}

/**
 * Mensaje neutro cuando el coach no puede responder (sin proveedor o presupuesto agotado). El
 * presupuesto es cosa de los desarrolladores: a la atleta no se le habla de euros ni de límites.
 */
export const COACH_UNAVAILABLE_TEXT = 'El coach no está disponible ahora mismo. Vuelve a intentarlo más tarde.';

const ORIGIN_NOTES: Partial<Record<MessageOrigin, string>> = {
  safety_filter: 'Respuesta automática de seguridad',
};

type ChatMessageProps = { role: 'user' | 'assistant'; content: string; origin?: MessageOrigin | null; children?: React.ReactNode };

/** Mensaje del coach (texto sobre el fondo) o de la atleta (a la derecha, en `surfaceSoft`). */
export function ChatMessage({ role, content, origin, children }: ChatMessageProps) {
  if (role === 'user') {
    return (
      <View style={styles.mine} accessibilityLabel={`Tú: ${content}`}>
        <Text style={styles.mineText} selectable>
          {content}
        </Text>
      </View>
    );
  }
  const note = origin ? ORIGIN_NOTES[origin] : undefined;
  // La respuesta fija por presupuesto agotado se sustituye por el mensaje neutro.
  const text = origin === 'budget_limit' ? COACH_UNAVAILABLE_TEXT : plainText(content);
  return (
    <View style={styles.coach}>
      {note ? <Text style={styles.originNote}>{note}</Text> : null}
      <Text style={styles.coachText} selectable accessibilityLabel={`Coach: ${text}`}>
        {text}
      </Text>
      {children}
    </View>
  );
}

const pad = (n: number) => String(n).padStart(2, '0');

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

/** «Hoy · 9:12», «Ayer · 18:40» o «lun, 16 nov · 9:12». */
export function chatDayLabel(iso: string, now = new Date()): string {
  const d = new Date(iso);
  const time = `${d.getHours()}:${pad(d.getMinutes())}`;
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (dayKey(d) === dayKey(now)) return `Hoy · ${time}`;
  if (dayKey(d) === dayKey(yesterday)) return `Ayer · ${time}`;
  const sameYear = d.getFullYear() === now.getFullYear();
  const date = d.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short', ...(sameYear ? {} : { year: 'numeric' }) });
  return `${date} · ${time}`;
}

/** ¿El mensaje empieza un día distinto del anterior? (para poner la etiqueta de día). */
export function startsNewDay(iso: string, previousIso: string | null | undefined): boolean {
  return !previousIso || dayKey(new Date(iso)) !== dayKey(new Date(previousIso));
}

export function ChatDayLabel({ label }: { label: string }) {
  return <Text style={styles.dayLabel}>{label}</Text>;
}

/** Estado mientras el coach prepara la respuesta (llega completa, sin streaming). */
export function ThinkingRow({ label = 'El coach está pensando…' }: { label?: string }) {
  return (
    <View style={styles.thinking} accessibilityRole="progressbar" accessibilityLabel={label}>
      <ActivityIndicator size="small" color={colors.accent} />
      <Text style={styles.thinkingText}>{label}</Text>
    </View>
  );
}

/** Mensaje que no se ha podido enviar: el error con el formato de la app y reintentar o editar. */
export function FailedMessage({ content, error, onRetry, onEdit }: { content: string; error: string; onRetry: () => void; onEdit: () => void }) {
  return (
    <View style={styles.failed}>
      <View style={[styles.mine, styles.mineFailed]}>
        <Text style={styles.mineText}>{content}</Text>
      </View>
      <View style={styles.failedBox} accessibilityRole="alert">
        <Icon name="alert" size={16} color={colors.danger} />
        <Text style={styles.failedText}>No se ha enviado. {error}</Text>
      </View>
      <View style={styles.failedActions}>
        <Pressable onPress={onEdit} accessibilityRole="button" hitSlop={6}>
          <Text style={styles.linkMuted}>Editar</Text>
        </Pressable>
        <Pressable onPress={onRetry} accessibilityRole="button" hitSlop={6}>
          <Text style={styles.link}>Reintentar</Text>
        </Pressable>
      </View>
    </View>
  );
}

/** Respuestas rápidas que rellenan la caja de texto. */
export function Suggestions({ items, onPick }: { items: string[]; onPick: (text: string) => void }) {
  return (
    <View style={styles.suggestions}>
      {items.map((s) => (
        <Pressable key={s} onPress={() => onPick(s)} style={({ pressed }) => [styles.suggestion, pressed && styles.pressed]} accessibilityRole="button">
          <Text style={styles.suggestionText}>{s}</Text>
        </Pressable>
      ))}
    </View>
  );
}

type ComposeBarProps = {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  /** Sin poder escribir (coach no disponible, presupuesto agotado…). */
  editable?: boolean;
  /** Se puede escribir pero no enviar todavía (p. ej. esperando la respuesta). */
  busy?: boolean;
  placeholder?: string;
};

/** Caja de texto fija abajo. En web, Intro envía y Mayús+Intro hace salto de línea. */
export function ComposeBar({ value, onChangeText, onSend, editable = true, busy, placeholder = 'Cuéntame qué ha cambiado…' }: ComposeBarProps) {
  const canSend = editable && !busy && value.trim().length > 0;
  const onKeyPress = (e: NativeSyntheticEvent<TextInputKeyPressEventData>) => {
    if (Platform.OS !== 'web') return;
    const event = e.nativeEvent as TextInputKeyPressEventData & { shiftKey?: boolean };
    if (event.key === 'Enter' && !event.shiftKey) {
      e.preventDefault();
      if (canSend) onSend();
    }
  };
  return (
    <View style={styles.composeBar}>
      <View style={styles.compose}>
        <TextInput
          style={styles.input}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textDisabled}
          editable={editable}
          multiline
          // En web, `multiline` pinta dos filas por defecto: se empieza con una.
          numberOfLines={Platform.OS === 'web' ? 1 : undefined}
          onKeyPress={onKeyPress}
          accessibilityLabel="Mensaje al coach"
        />
        <Pressable
          onPress={onSend}
          disabled={!canSend}
          style={({ pressed }) => [styles.send, !canSend && styles.sendDisabled, pressed && styles.pressed]}
          accessibilityRole="button"
          accessibilityLabel="Enviar"
          accessibilityState={{ disabled: !canSend, busy: !!busy }}
        >
          <Icon name="send" size={18} color={colors.onPrimary} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  coach: { paddingTop: spacing.lg, gap: spacing.xs },
  coachText: { ...typography.body, color: colors.text },
  originNote: { ...typography.label, color: colors.textSecondary },
  mine: {
    alignSelf: 'flex-end',
    maxWidth: '82%',
    marginTop: spacing.lg,
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.sm,
    paddingVertical: spacing.sm + 1,
    paddingHorizontal: spacing.md + 1,
  },
  mineText: { ...typography.body, color: colors.text },
  mineFailed: { opacity: 0.6 },
  dayLabel: { ...typography.label, color: colors.textSecondary, textAlign: 'center', paddingTop: spacing.lg },
  thinking: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingTop: spacing.lg },
  thinkingText: { ...typography.small, color: colors.textSecondary },
  failed: { alignItems: 'flex-end', gap: spacing.xs },
  failedBox: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.xs, maxWidth: '82%' },
  failedText: { ...typography.small, color: colors.danger, flexShrink: 1 },
  failedActions: { flexDirection: 'row', gap: spacing.lg },
  link: { ...typography.smallBold, color: colors.textActive },
  linkMuted: { ...typography.smallBold, color: colors.textSecondary },
  suggestions: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', gap: spacing.sm, paddingTop: spacing.lg },
  suggestion: { borderWidth: lines.hairline, borderColor: colors.separator, borderRadius: radius.sm, paddingHorizontal: spacing.md, paddingVertical: 7 },
  suggestionText: { ...typography.smallBold, color: colors.text },
  pressed: { opacity: 0.7 },
  composeBar: { borderTopWidth: lines.hairline, borderTopColor: colors.separator, backgroundColor: colors.background },
  compose: {
    width: '100%',
    maxWidth: layout.contentMaxWidth,
    alignSelf: 'center',
    paddingHorizontal: spacing.lg,
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: spacing.sm,
    paddingVertical: spacing.sm + 2,
  },
  input: { ...typography.body, flex: 1, color: colors.text, paddingVertical: spacing.sm, maxHeight: 132 },
  send: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary, borderRadius: radius.sm },
  sendDisabled: { opacity: 0.35 },
});
