/**
 * Filas con filete (propuesta v3, #25): listas agrupadas sin tarjetas para Perfil y Ajustes.
 * Icono de trazo fino a la izquierda, título y subtítulo, y valor con flecha a la derecha.
 */
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Icon, type IconName } from './Icon';
import { colors, lines, spacing, typography } from './theme';

type RowProps = {
  title: string;
  subtitle?: string | null;
  icon?: IconName;
  /** Valor a la derecha (texto o un elemento, p. ej. `StatusDot`). */
  value?: React.ReactNode;
  onPress?: () => void;
  /** Acción destructiva (cerrar sesión): texto e icono en color de error, sin flecha. */
  danger?: boolean;
  /** Primera fila del grupo: sin filete superior. `RowGroup` lo pone solo. */
  first?: boolean;
  accessibilityLabel?: string;
};

export function Row({ title, subtitle, icon, value, onPress, danger, first, accessibilityLabel }: RowProps) {
  const tint = danger ? colors.danger : colors.textSecondary;
  const content = (
    <>
      {icon ? <Icon name={icon} size={20} color={tint} /> : null}
      <View style={styles.text}>
        <Text style={[styles.title, danger && styles.danger]} numberOfLines={1}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={styles.subtitle} numberOfLines={2}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      <View style={styles.value}>
        {typeof value === 'string' ? <Text style={styles.valueText}>{value}</Text> : value}
        {onPress && !danger ? <Icon name="forward" size={16} color={colors.textDisabled} /> : null}
      </View>
    </>
  );
  if (!onPress) return <View style={[styles.row, first && styles.first]}>{content}</View>;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? [title, subtitle, typeof value === 'string' ? value : null].filter(Boolean).join(', ')}
      style={({ pressed }) => [styles.row, first && styles.first, pressed && styles.pressed]}
    >
      {content}
    </Pressable>
  );
}

/** Grupo de filas con etiqueta de sección. La primera fila va sin filete. */
export function RowGroup({ title, children }: { title?: string; children: React.ReactNode }) {
  const rows = React.Children.toArray(children).filter(React.isValidElement);
  return (
    <View style={styles.group}>
      {title ? <Text style={styles.label}>{title}</Text> : null}
      <View>
        {rows.map((child, i) =>
          i === 0 && child.type === Row ? React.cloneElement(child as React.ReactElement<RowProps>, { first: true }) : child,
        )}
      </View>
    </View>
  );
}

/** Marca cuadrada de estado (conexión activa) en color de acento. */
export function StatusDot({ active = true }: { active?: boolean }) {
  return <View style={[styles.dot, !active && styles.dotOff]} />;
}

const styles = StyleSheet.create({
  group: { gap: spacing.xs },
  label: { ...typography.label, color: colors.textSecondary, paddingBottom: spacing.xs },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: 52,
    paddingVertical: spacing.md - 1,
    borderTopWidth: lines.hairline,
    borderTopColor: colors.separator,
  },
  first: { borderTopWidth: 0 },
  pressed: { opacity: 0.6 },
  text: { flex: 1, gap: 1 },
  title: { ...typography.bodyBold, color: colors.text },
  danger: { color: colors.danger },
  subtitle: { ...typography.small, color: colors.textSecondary },
  value: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs, flexShrink: 1, maxWidth: '45%' },
  valueText: { ...typography.small, color: colors.textSecondary, textAlign: 'right', flexShrink: 1 },
  dot: { width: 7, height: 7, backgroundColor: colors.accent },
  dotOff: { backgroundColor: colors.textDisabled },
});
