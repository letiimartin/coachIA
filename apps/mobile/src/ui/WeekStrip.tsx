/**
 * Semana compacta de lunes a domingo para Hoy: una columna por día con su marca (icono del primer
 * entreno o evento, o un filete si no hay nada). Hoy, en `textActive` y subrayado. Sin estado.
 */
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Icon, type IconName } from './Icon';
import { colors, lines, spacing, typography } from './theme';

export type WeekStripDay = {
  date: string;
  /** «L». */
  letter: string;
  day: number;
  /** Icono del día (la carrera manda; después el entreno y el evento) o null si no hay nada. */
  icon: IconName | null;
  highlight?: boolean;
  /** Entrenos y eventos del día, para lectores de pantalla. */
  count: number;
};

export function WeekStrip({ days, today }: { days: WeekStripDay[]; today: string }) {
  return (
    <View style={styles.row}>
      {days.map((d) => {
        const isToday = d.date === today;
        return (
          <View
            key={d.date}
            style={[styles.col, isToday && styles.todayCol]}
            accessible
            accessibilityLabel={`${isToday ? 'Hoy, ' : ''}${d.letter} ${d.day}: ${d.count === 0 ? 'nada planificado' : d.count === 1 ? '1 elemento' : `${d.count} elementos`}`}
          >
            <View style={styles.mark}>
              {d.icon ? <Icon name={d.icon} size={18} color={d.highlight ? colors.textActive : colors.textSecondary} /> : <View style={styles.empty} />}
            </View>
            <Text style={[styles.letter, isToday && styles.todayText]}>{d.letter}</Text>
            <Text style={[styles.number, isToday && styles.todayText]}>{d.day}</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: spacing.xs + 2 },
  col: { flex: 1, alignItems: 'center', gap: spacing.xs, paddingBottom: spacing.xs, borderBottomWidth: lines.selection, borderBottomColor: 'transparent' },
  todayCol: { borderBottomColor: colors.accent },
  mark: { height: 24, width: '100%', alignItems: 'center', justifyContent: 'flex-end' },
  empty: { width: '100%', height: lines.selection, backgroundColor: colors.separatorStrong },
  letter: { ...typography.label, color: colors.textSecondary },
  number: { ...typography.smallBold, color: colors.text, fontVariant: ['tabular-nums'] },
  todayText: { color: colors.textActive },
});
