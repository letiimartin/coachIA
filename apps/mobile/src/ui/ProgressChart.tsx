/**
 * Progresión de un ejercicio (#33), en dos paneles como la gráfica de forma: una línea arriba (peso
 * máximo o mejor serie) y barras abajo (volumen o total). Una posición por sesión, en orden. Dibuja
 * tal cual los valores de `GET /v1/strength/exercises/{id}/progress`: sólo los escala.
 */
import React, { useState } from 'react';
import { StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';

import { shortDate } from './StrengthWeekChart';
import { colors, fonts, fontSize, lines, spacing, typography } from './theme';

export type ProgressPoint = { day: string; line: number | null; bar: number | null };

type Props = {
  points: ProgressPoint[];
  lineLabel: string;
  barLabel: string;
  height?: number;
};

const AXIS_W = 32;
const AXIS_H = 14;

function compact(v: number): string {
  return v >= 10000 ? `${Math.round(v / 1000)}k` : String(Math.round(v * 10) / 10).replace('.', ',');
}

export function ProgressChart({ points, lineLabel, barLabel, height = 200 }: Props) {
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(Math.round(e.nativeEvent.layout.width));

  const n = points.length;
  const plotW = Math.max(0, width - AXIS_W);
  const topH = Math.round((height - AXIS_H) * 0.62);
  const bottomH = height - AXIS_H - topH - spacing.sm;
  const bottomTop = topH + spacing.sm;

  const lineValues = points.map((p) => p.line).filter((v): v is number => v != null);
  const lMin = lineValues.length ? Math.min(...lineValues) : 0;
  const lMax = lineValues.length ? Math.max(...lineValues) : 1;
  const pad = Math.max(1, (lMax - lMin) * 0.15);
  const yMin = Math.max(0, lMin - pad);
  const yMax = lMax + pad;
  const x = (i: number) => (n <= 1 ? plotW / 2 : 6 + (i * (plotW - 12)) / (n - 1));
  const y = (v: number) => 8 + (1 - (v - yMin) / (yMax - yMin)) * (topH - 16);
  const linePoints = points
    .map((p, i) => (p.line == null ? null : `${x(i).toFixed(1)},${y(p.line).toFixed(1)}`))
    .filter(Boolean)
    .join(' ');

  const barMax = Math.max(1, ...points.map((p) => p.bar ?? 0));
  const barW = n > 1 ? Math.max(2, Math.min(14, ((plotW - 12) / (n - 1)) * 0.55)) : 14;
  const barH = (v: number) => Math.max(1, (v / barMax) * (bottomH - 2));
  const axisText = { fontSize: fontSize.micro, fontFamily: fonts.regular, fill: colors.textSecondary };
  const lastIndex = points.reduce((acc, p, i) => (p.line == null ? acc : i), -1);

  return (
    <View>
      <View onLayout={onLayout} style={{ height }} accessibilityRole="image" accessibilityLabel={`${lineLabel} y ${barLabel} por sesión`}>
        {width > 0 && n > 0 ? (
          <Svg width={width} height={height}>
            {lineValues.length ? (
              <>
                {[lMin, lMax].filter((v, i, all) => all.indexOf(v) === i).map((v) => (
                  <React.Fragment key={v}>
                    <Line x1={0} x2={plotW} y1={y(v)} y2={y(v)} stroke={colors.separator} strokeWidth={lines.hairline} />
                    <SvgText x={width} y={y(v) + 3} textAnchor="end" {...axisText}>
                      {compact(v)}
                    </SvgText>
                  </React.Fragment>
                ))}
                <Polyline points={linePoints} fill="none" stroke={colors.text} strokeWidth={2.2} strokeLinejoin="round" />
                {points.map((p, i) =>
                  p.line == null ? null : (
                    <Circle
                      key={`${p.day}-${i}`}
                      cx={x(i)}
                      cy={y(p.line)}
                      r={i === lastIndex ? 3.5 : 2.2}
                      fill={i === lastIndex ? colors.background : colors.text}
                      stroke={colors.text}
                      strokeWidth={i === lastIndex ? 2 : 0}
                    />
                  ),
                )}
              </>
            ) : null}

            <Line x1={0} x2={plotW} y1={bottomTop + bottomH} y2={bottomTop + bottomH} stroke={colors.separatorStrong} strokeWidth={lines.hairline} />
            <SvgText x={width} y={bottomTop + 8} textAnchor="end" {...axisText}>
              {compact(barMax)}
            </SvgText>
            {points.map((p, i) =>
              p.bar == null ? null : (
                <Rect
                  key={`${p.day}-${i}`}
                  x={x(i) - barW / 2}
                  y={bottomTop + bottomH - barH(p.bar)}
                  width={barW}
                  height={barH(p.bar)}
                  fill={colors.text}
                  fillOpacity={0.35}
                />
              ),
            )}

            <SvgText x={2} y={height - 2} {...axisText}>
              {shortDate(points[0].day)}
            </SvgText>
            {n > 1 ? (
              <SvgText x={plotW} y={height - 2} textAnchor="end" {...axisText}>
                {shortDate(points[n - 1].day)}
              </SvgText>
            ) : null}
          </Svg>
        ) : null}
      </View>
      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={styles.markLine} />
          <Text style={styles.legendText}>{lineLabel}</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={styles.markBar} />
          <Text style={styles.legendText}>{barLabel}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg, paddingTop: spacing.sm },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs + 2 },
  legendText: { ...typography.caption, color: colors.textSecondary },
  markLine: { width: 14, height: 2, backgroundColor: colors.text },
  markBar: { width: 4, height: 10, backgroundColor: colors.text, opacity: 0.35 },
});
