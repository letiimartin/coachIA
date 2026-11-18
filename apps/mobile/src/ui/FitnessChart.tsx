/**
 * Gráfica de forma en dos paneles (propuesta v3, #25): forma (CTL) y fatiga (ATL) arriba y
 * balance (TSB) en barras abajo. Dibuja tal cual la serie de `GET /v1/athlete/fitness`: no
 * calcula ninguna métrica, sólo escala los valores al tamaño de la gráfica.
 */
import React, { useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Polygon, Polyline, Rect, Text as SvgText } from 'react-native-svg';

import type { FitnessDayOut } from '../api/fitnessApi';
import { colors, fonts, fontSize, lines, spacing, typography } from './theme';

type Props = {
  days: FitnessDayOut[];
  height?: number;
  /** Texto bajo el final del eje X (p. ej. «Hoy»). Por defecto, la fecha del último día. */
  endLabel?: string;
};

const AXIS_W = 28; // columna derecha con los valores de la rejilla
const AXIS_H = 14; // fila inferior con las fechas

function shortDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }).replace('.', '').toUpperCase();
}

/** Tres líneas de rejilla en múltiplos de 10 dentro del rango [min, max]. */
function gridValues(min: number, max: number): number[] {
  const step = Math.max(10, Math.ceil((max - min) / 3 / 10) * 10);
  const values: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max; v += step) values.push(v);
  return values;
}

export function FitnessChart({ days, height = 220, endLabel }: Props) {
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(Math.round(e.nativeEvent.layout.width));

  const n = days.length;
  const plotW = Math.max(0, width - AXIS_W);
  const topH = Math.round((height - AXIS_H) * 0.66);
  const bottomH = height - AXIS_H - topH;

  const values = days.flatMap((d) => [d.ctl, d.atl]);
  const rawMin = values.length ? Math.min(...values) : 0;
  const rawMax = values.length ? Math.max(...values) : 1;
  const pad = Math.max(4, (rawMax - rawMin) * 0.1);
  const yMin = Math.max(0, Math.floor(rawMin - pad));
  const yMax = Math.ceil(rawMax + pad);
  const span = Math.max(1, yMax - yMin);

  const x = (i: number) => (n <= 1 ? plotW / 2 : 4 + (i * (plotW - 8)) / (n - 1));
  const y = (v: number) => 8 + (1 - (v - yMin) / span) * (topH - 16);
  const points = (key: 'ctl' | 'atl') => days.map((d, i) => `${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(' ');

  const tsbMax = Math.max(5, ...days.map((d) => Math.abs(d.tsb)));
  const y0 = topH + bottomH / 2;
  const tsbScale = (bottomH / 2 - 3) / tsbMax;
  const barW = n > 1 ? Math.max(1, Math.min(6, ((plotW - 8) / (n - 1)) * 0.6)) : 6;

  const last = days[n - 1];
  const axisText = { fontSize: fontSize.micro, fontFamily: fonts.regular, fill: colors.textSecondary };

  return (
    <View>
      <View onLayout={onLayout} style={{ height }} accessibilityRole="image" accessibilityLabel={describe(days)}>
        {width > 0 && n > 0 ? (
          <Svg width={width} height={height}>
            {gridValues(yMin, yMax).map((v) => (
              <React.Fragment key={v}>
                <Line x1={0} x2={plotW} y1={y(v)} y2={y(v)} stroke={colors.separator} strokeWidth={lines.hairline} />
                <SvgText x={width} y={y(v) + 3} textAnchor="end" {...axisText}>
                  {v}
                </SvgText>
              </React.Fragment>
            ))}
            <Polygon points={`${x(0)},${topH - 8} ${points('ctl')} ${x(n - 1)},${topH - 8}`} fill={colors.text} fillOpacity={0.07} />
            <Polyline points={points('atl')} fill="none" stroke={colors.textSecondary} strokeWidth={1.2} strokeDasharray="3 2" strokeLinejoin="round" />
            <Polyline points={points('ctl')} fill="none" stroke={colors.text} strokeWidth={2.2} strokeLinejoin="round" />
            <Circle cx={x(n - 1)} cy={y(last.ctl)} r={3.5} fill={colors.background} stroke={colors.text} strokeWidth={2} />

            <Line x1={0} x2={plotW} y1={y0} y2={y0} stroke={colors.separatorStrong} strokeWidth={lines.hairline} />
            <SvgText x={width} y={y0 + 3} textAnchor="end" {...axisText}>
              TSB
            </SvgText>
            {days.map((d, i) => {
              const h = Math.max(0.6, Math.abs(d.tsb) * tsbScale);
              return (
                <Rect
                  key={d.day}
                  x={x(i) - barW / 2}
                  y={d.tsb >= 0 ? y0 - h : y0}
                  width={barW}
                  height={h}
                  fill={colors.text}
                  fillOpacity={d.tsb >= 0 ? 0.6 : 0.28}
                />
              );
            })}

            <SvgText x={2} y={height - 2} {...axisText}>
              {shortDate(days[0].day)}
            </SvgText>
            <SvgText x={plotW} y={height - 2} textAnchor="end" {...axisText}>
              {endLabel ?? shortDate(last.day)}
            </SvgText>
          </Svg>
        ) : null}
      </View>
      <View style={styles.legend}>
        <LegendItem mark="line" text="Forma (CTL)" />
        <LegendItem mark="dash" text="Fatiga (ATL)" />
        <LegendItem mark="bar" text="Balance (TSB)" />
      </View>
    </View>
  );
}

function LegendItem({ mark, text }: { mark: 'line' | 'dash' | 'bar'; text: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.mark, mark === 'dash' && styles.markDash, mark === 'bar' && styles.markBar]} />
      <Text style={styles.legendText}>{text}</Text>
    </View>
  );
}

function describe(days: FitnessDayOut[]): string {
  const last = days[days.length - 1];
  if (!last) return 'Gráfica de forma sin datos';
  return `Forma, fatiga y balance del ${shortDate(days[0].day)} al ${shortDate(last.day)}. Último día: forma ${last.ctl}, fatiga ${last.atl}, balance ${last.tsb}.`;
}

const styles = StyleSheet.create({
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg, paddingTop: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs + 2 },
  legendText: { ...typography.caption, color: colors.textSecondary },
  mark: { width: 14, height: 2, backgroundColor: colors.text },
  markDash: { height: 0, backgroundColor: 'transparent', borderTopWidth: 1.2, borderStyle: 'dashed', borderColor: colors.textSecondary },
  markBar: { width: 4, height: 10, backgroundColor: colors.text, opacity: 0.6 },
});
