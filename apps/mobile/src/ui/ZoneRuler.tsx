/**
 * Regla de zonas con la marca del umbral (propuesta v3, #29). De sólo lectura.
 *
 * Dibuja las zonas que devuelve la API (`ZoneOut`) de Z1 a la más intensa, con el ancho de cada
 * tramo proporcional a su rango. No calcula límites: sólo convierte valores de la API en posiciones.
 * Las zonas abiertas (sin `high`, o con 0 donde el 0 no tiene sentido) se dibujan con el ancho de su
 * vecina y su extremo no se rotula.
 */
import React, { useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';

import type { ZoneOut } from '../api/types';
import { colors, lines, radius, spacing, typography } from './theme';
import { zoneColor, type ZoneModel } from './zoneModel';

type Props = {
  zones: ZoneOut[];
  /** Valor del umbral (el que marca la regla), en las unidades de la API. */
  threshold: number | null;
  model: ZoneModel;
};

const GAP = 2;
const BAR_HEIGHT = 10;
const MARK_OVERHANG = 4;
const LABEL_WIDTH = 64;

type Segment = { zone: ZoneOut; from: number; to: number; width: number; realFrom: boolean; realTo: boolean };

/** Tramos de la regla en orden de dibujo (Z1 a la izquierda), con extremos y ancho en unidades de la API. */
function segments(zones: ZoneOut[], model: ZoneModel): Segment[] {
  const isReal = (v: number | null): v is number => v != null && (v !== 0 || model.zeroBased);
  const base = zones.map((zone) => {
    // En ritmo (invertido) Z1 es la más lenta: a la izquierda va `high` y a la derecha `low`.
    const from = model.inverted ? zone.high : zone.low;
    const to = model.inverted ? zone.low : zone.high;
    return { zone, from, to, realFrom: isReal(from), realTo: isReal(to) };
  });
  const widths = base.map((s) => (s.realFrom && s.realTo ? Math.abs((s.to as number) - (s.from as number)) : null));
  const dir = model.inverted ? -1 : 1;
  return base.map((s, i) => {
    const width = widths[i] ?? widths[i - 1] ?? widths[i + 1] ?? 1;
    const from = s.realFrom ? (s.from as number) : (s.to as number) - dir * width;
    const to = s.realTo ? (s.to as number) : from + dir * width;
    return { zone: s.zone, from, to, width, realFrom: s.realFrom, realTo: s.realTo };
  });
}

/** Posición en píxeles de un valor sobre la regla, o null si queda fuera. */
function position(value: number, segs: Segment[], scale: number): number | null {
  let x = 0;
  for (let i = 0; i < segs.length; i++) {
    const s = segs[i];
    const w = s.width * scale;
    const t = (value - s.from) / (s.to - s.from);
    // En el límite entre dos zonas, la marca va en el hueco que las separa.
    if (Math.abs(t - 1) < 1e-9 && i < segs.length - 1) return x + w + GAP / 2;
    if (t >= 0 && t < 1) return x + t * w;
    x += w + GAP;
  }
  return null;
}

export function ZoneRuler({ zones, threshold, model }: Props) {
  const [width, setWidth] = useState(0);
  const segs = segments(zones, model);
  const total = segs.reduce((sum, s) => sum + s.width, 0);
  const scale = width > 0 && total > 0 ? (width - GAP * (segs.length - 1)) / total : 0;
  const mark = threshold != null && scale > 0 ? position(threshold, segs, scale) : null;
  const first = segs[0];
  const last = segs[segs.length - 1];
  const withUnit = (v: number) => `${model.format(v)} ${model.unit}`;
  const label = [
    `Regla de zonas de ${model.label.toLowerCase()}`,
    threshold != null ? `${model.thresholdLabel} ${withUnit(threshold)}` : null,
  ]
    .filter(Boolean)
    .join(', ');

  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);
  // La etiqueta del umbral no se sale de la regla por los extremos.
  const labelLeft = mark == null ? 0 : Math.min(Math.max(mark - LABEL_WIDTH / 2, 0), Math.max(width - LABEL_WIDTH, 0));
  const labelAlign = mark == null ? 'center' : mark - LABEL_WIDTH / 2 < 0 ? 'left' : mark + LABEL_WIDTH / 2 > width ? 'right' : 'center';

  return (
    <View accessible accessibilityRole="image" accessibilityLabel={label}>
      <View style={styles.track} onLayout={onLayout}>
        <View style={styles.bar}>
          {segs.map((s) => (
            <View key={s.zone.code} style={[styles.segment, { flex: s.width, backgroundColor: zoneColor(s.zone.code) }]} />
          ))}
        </View>
        {mark != null ? <View style={[styles.mark, { left: mark - lines.selection / 2 }]} /> : null}
      </View>
      <View style={styles.axis}>
        <Text style={styles.axisText}>{first && first.realFrom ? withUnit(first.from) : ''}</Text>
        <Text style={styles.axisText}>{last && last.realTo ? withUnit(last.to) : ''}</Text>
        {mark != null && threshold != null ? (
          <Text style={[styles.axisText, styles.threshold, { left: labelLeft, textAlign: labelAlign }]} numberOfLines={1}>
            {model.format(threshold)}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  track: { height: BAR_HEIGHT + MARK_OVERHANG * 2, justifyContent: 'center' },
  bar: { flexDirection: 'row', gap: GAP, height: BAR_HEIGHT },
  segment: { height: BAR_HEIGHT, borderRadius: radius.sm },
  mark: { position: 'absolute', top: 0, bottom: 0, width: lines.selection, backgroundColor: colors.text },
  axis: { flexDirection: 'row', justifyContent: 'space-between', minHeight: 16, paddingTop: spacing.xxs },
  axisText: { ...typography.caption, color: colors.textSecondary, fontVariant: ['tabular-nums'] },
  threshold: { position: 'absolute', top: spacing.xxs, width: LABEL_WIDTH, ...typography.smallBold, fontSize: typography.caption.fontSize, color: colors.text },
});
