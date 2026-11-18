/**
 * Tira de cifras separadas por filetes verticales (propuesta v3, #25): umbrales del Perfil y
 * forma de Rendimiento. Sólo muestra valores que ya vienen de la API.
 */
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, fonts, fontSize, lines, spacing, typography } from './theme';

export type Stat = {
  /** Etiqueta encima de la cifra (opcional, en mayúsculas). */
  label?: string;
  value: string;
  /** Texto pequeño debajo de la cifra (unidad o descripción). */
  caption?: string;
  /** Variación o nota bajo la cifra. */
  note?: string | null;
};

type Props = { stats: Stat[]; size?: 'large' | 'medium' };

export function StatStrip({ stats, size = 'medium' }: Props) {
  return (
    <View style={styles.strip}>
      {stats.map((s, i) => (
        <View key={`${s.label ?? ''}${s.caption ?? ''}${i}`} style={[styles.cell, i === 0 && styles.firstCell]}>
          {s.label ? (
            <Text style={styles.label} numberOfLines={1}>
              {s.label}
            </Text>
          ) : null}
          <Text style={[styles.value, size === 'large' && styles.valueLarge]} numberOfLines={1} adjustsFontSizeToFit>
            {s.value}
          </Text>
          {s.caption ? (
            <Text style={styles.caption} numberOfLines={2}>
              {s.caption}
            </Text>
          ) : null}
          {s.note ? (
            <Text style={styles.note} numberOfLines={1}>
              {s.note}
            </Text>
          ) : null}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  strip: { flexDirection: 'row' },
  cell: {
    flex: 1,
    minWidth: 0,
    paddingHorizontal: spacing.sm + 2,
    borderLeftWidth: lines.hairline,
    borderLeftColor: colors.separator,
    gap: 2,
  },
  firstCell: { paddingLeft: 0, borderLeftWidth: 0 },
  label: { ...typography.label, color: colors.textSecondary },
  value: { fontFamily: fonts.bold, fontSize: fontSize.heading, lineHeight: 27, letterSpacing: -0.3, color: colors.text, fontVariant: ['tabular-nums'] },
  valueLarge: { fontSize: fontSize.display, lineHeight: 38, letterSpacing: -0.7 },
  caption: { ...typography.caption, color: colors.textSecondary },
  note: { ...typography.caption, fontFamily: fonts.bold, color: colors.textSecondary },
});
