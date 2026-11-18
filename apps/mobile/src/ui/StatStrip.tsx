/**
 * Fila de cifras separadas por filetes verticales (forma CTL/ATL/TSB en Hoy, datos de carrera en el
 * detalle de evento). Sin estado: sólo pinta lo que recibe, ya formateado.
 */
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, fontSize, lines, spacing, typography } from './theme';

export type Stat = { value: string; label: string; caption?: string };

type Props = {
  items: Stat[];
  /** `large`: cifras de 28 px (Hoy). `medium`: 22 px (detalle). */
  size?: 'large' | 'medium';
  /** Filete superior, para apilar varias filas como una rejilla. */
  ruled?: boolean;
};

export function StatStrip({ items, size = 'large', ruled }: Props) {
  return (
    <View style={[styles.row, ruled && styles.ruled]}>
      {items.map((item, i) => (
        <View
          key={item.label}
          style={[styles.cell, i > 0 && styles.divided]}
          accessible
          accessibilityLabel={`${item.label}: ${item.value}${item.caption ? `, ${item.caption}` : ''}`}
        >
          <Text style={[styles.value, size === 'medium' && styles.valueMedium]} numberOfLines={1} adjustsFontSizeToFit>
            {item.value}
          </Text>
          <Text style={styles.label}>{item.label}</Text>
          {item.caption ? <Text style={styles.caption}>{item.caption}</Text> : null}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row' },
  ruled: { borderTopWidth: lines.hairline, borderTopColor: colors.separator, paddingTop: spacing.sm + 2 },
  cell: { flex: 1, minWidth: 0, gap: spacing.xxs, paddingRight: spacing.md },
  divided: { borderLeftWidth: lines.hairline, borderLeftColor: colors.separator, paddingLeft: spacing.md },
  value: { ...typography.title, color: colors.text, fontVariant: ['tabular-nums'] },
  valueMedium: { ...typography.heading },
  label: { ...typography.caption, color: colors.textSecondary },
  caption: { ...typography.caption, fontSize: fontSize.micro, color: colors.textSecondary },
});
