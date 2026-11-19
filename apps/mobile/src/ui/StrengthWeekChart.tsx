/**
 * Carga de fuerza por semana (#33): una barra por semana con la carga `session_rpe` que devuelve
 * `GET /v1/strength/weekly`. Va aparte de la gráfica de forma porque no es TSS ni suma en CTL/ATL/TSB.
 * No calcula nada: sólo escala los valores al tamaño de la gráfica.
 */
import React, { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Line, Rect, Text as SvgText } from 'react-native-svg';

import type { StrengthWeekOut } from '../api/types';
import { colors, fonts, fontSize, lines } from './theme';

type Props = {
  weeks: StrengthWeekOut[];
  height?: number;
  /** Lunes de la semana en curso, que se marca con el acento. */
  currentWeek?: string;
};

const AXIS_W = 28;
const AXIS_H = 14;

export function shortDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }).replace('.', '').toUpperCase();
}

export function StrengthWeekChart({ weeks, height = 110, currentWeek }: Props) {
  const [width, setWidth] = useState(0);
  const onLayout = (e: LayoutChangeEvent) => setWidth(Math.round(e.nativeEvent.layout.width));

  const n = weeks.length;
  const plotW = Math.max(0, width - AXIS_W);
  const plotH = height - AXIS_H;
  const max = Math.max(1, ...weeks.map((w) => w.load));
  const slot = n > 0 ? plotW / n : 0;
  const barW = Math.max(2, Math.min(18, slot * 0.6));
  const y = (v: number) => plotH - (v / max) * (plotH - 6);
  const axisText = { fontSize: fontSize.micro, fontFamily: fonts.regular, fill: colors.textSecondary };
  const last = weeks[n - 1];

  return (
    <View onLayout={onLayout} style={{ height }} accessibilityRole="image" accessibilityLabel={describe(weeks)}>
      {width > 0 && n > 0 ? (
        <Svg width={width} height={height}>
          <Line x1={0} x2={plotW} y1={y(max)} y2={y(max)} stroke={colors.separator} strokeWidth={lines.hairline} />
          <SvgText x={width} y={y(max) + 3} textAnchor="end" {...axisText}>
            {Math.round(max)}
          </SvgText>
          <Line x1={0} x2={plotW} y1={plotH} y2={plotH} stroke={colors.separatorStrong} strokeWidth={lines.hairline} />
          {weeks.map((w, i) => {
            const h = Math.max(w.sessions > 0 ? 1.5 : 0, plotH - y(w.load));
            const current = w.week_start === currentWeek;
            return h > 0 ? (
              <Rect
                key={w.week_start}
                x={i * slot + (slot - barW) / 2}
                y={plotH - h}
                width={barW}
                height={h}
                fill={current ? colors.accent : colors.text}
                fillOpacity={current ? 1 : 0.6}
              />
            ) : null;
          })}
          <SvgText x={2} y={height - 2} {...axisText}>
            {shortDate(weeks[0].week_start)}
          </SvgText>
          {n > 1 ? (
            <SvgText x={plotW} y={height - 2} textAnchor="end" {...axisText}>
              {last.week_start === currentWeek ? 'ESTA SEMANA' : shortDate(last.week_start)}
            </SvgText>
          ) : null}
        </Svg>
      ) : null}
    </View>
  );
}

function describe(weeks: StrengthWeekOut[]): string {
  const last = weeks[weeks.length - 1];
  if (!last) return 'Carga de fuerza por semana sin datos';
  return `Carga de fuerza por semana desde el ${shortDate(weeks[0].week_start)}. Última semana: ${last.sessions} sesiones, carga ${Math.round(last.load)}.`;
}
