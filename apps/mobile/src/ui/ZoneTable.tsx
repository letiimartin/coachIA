/**
 * Tabla de zonas de sólo lectura (propuesta v3, #29): marca del color de la zona, número, nombre y
 * rango tal como lo devuelve la API, en la unidad de la disciplina. No calcula nada.
 */
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { ZoneOut } from '../api/types';
import { colors, fontSize, lines, spacing, typography } from './theme';
import { zoneColor, type ZoneModel } from './zoneModel';

/** Rango de una zona: «a–b», «< b» si empieza en 0 o «> a» si no tiene límite superior. */
export function zoneRange(zone: ZoneOut, model: ZoneModel): string {
  const f = model.format;
  if (zone.high == null) return `> ${f(zone.low)} ${model.unit}`;
  if (zone.low <= 0) return `< ${f(zone.high)} ${model.unit}`;
  return `${f(zone.low)}–${f(zone.high)} ${model.unit}`;
}

export function ZoneTable({ zones, model }: { zones: ZoneOut[]; model: ZoneModel }) {
  return (
    <View>
      {zones.map((z, i) => (
        <View
          key={z.code}
          style={[styles.row, i === 0 && styles.first]}
          accessible
          accessibilityLabel={`Zona ${z.number}, ${z.name}, ${zoneRange(z, model)}`}
        >
          <View style={[styles.swatch, { backgroundColor: zoneColor(z.code) }]} />
          <Text style={styles.number}>{z.number}</Text>
          <Text style={styles.name} numberOfLines={2}>
            {z.name}
          </Text>
          <Text style={styles.range}>{zoneRange(z, model)}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.sm + 2,
    borderTopWidth: lines.hairline,
    borderTopColor: colors.separator,
  },
  first: { borderTopWidth: 0 },
  swatch: { width: 3, alignSelf: 'stretch' },
  number: { ...typography.bodyBold, fontSize: fontSize.heading - 4, width: 18, color: colors.text, fontVariant: ['tabular-nums'] },
  name: { ...typography.bodyBold, fontSize: fontSize.small, flex: 1, color: colors.text },
  range: { ...typography.bodyBold, color: colors.text, textAlign: 'right', fontVariant: ['tabular-nums'] },
});
