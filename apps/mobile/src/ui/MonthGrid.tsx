/**
 * Rejilla de un mes de lunes a domingo, a todo el ancho y con filetes. El día seleccionado va en
 * lavanda (`surfaceSoft`) con la cifra subrayada; hoy, en `textActive`. Cada día puede llevar una
 * marca: la bandera de carrera o un punto si tiene otros eventos. Sin estado.
 */
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Icon } from './Icon';
import { colors, lines, spacing, typography } from './theme';

export type MonthGridDay = {
  /** YYYY-MM-DD. */
  date: string;
  /** Número del día. */
  day: number;
  /** false en los días de relleno del mes anterior o siguiente. */
  inMonth: boolean;
  marker: 'race' | 'event' | null;
  /** Texto para lectores de pantalla («Martes 17, 2 eventos»). */
  accessibilityLabel: string;
};

type Props = {
  weekdayLetters: string[];
  days: MonthGridDay[];
  selected: string;
  today: string;
  onSelect: (date: string) => void;
};

export function MonthGrid({ weekdayLetters, days, selected, today, onSelect }: Props) {
  const weeks: MonthGridDay[][] = [];
  for (let i = 0; i < days.length; i += 7) weeks.push(days.slice(i, i + 7));
  return (
    <View style={styles.grid}>
      <View style={styles.row}>
        {weekdayLetters.map((l) => (
          <Text key={l} style={[styles.cell, styles.header]}>
            {l}
          </Text>
        ))}
      </View>
      {weeks.map((week) => (
        <View key={week[0].date} style={styles.row}>
          {week.map((d, i) => {
            const isSelected = d.date === selected;
            const isToday = d.date === today;
            return (
              <Pressable
                key={d.date}
                onPress={() => onSelect(d.date)}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                accessibilityLabel={d.accessibilityLabel}
                style={({ pressed }) => [styles.cell, styles.day, i > 0 && styles.divided, (isSelected || pressed) && styles.selected]}
              >
                <View style={styles.dayTop}>
                  <Text
                    style={[
                      styles.number,
                      !d.inMonth && styles.outside,
                      isToday && styles.today,
                      isSelected && styles.numberSelected,
                    ]}
                  >
                    {d.day}
                  </Text>
                  {d.marker === 'race' ? <Icon name="race" size={12} color={colors.textActive} /> : null}
                  {d.marker === 'event' ? <View style={styles.dot} /> : null}
                </View>
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: { borderTopWidth: lines.hairline, borderTopColor: colors.separator },
  row: { flexDirection: 'row', borderBottomWidth: lines.hairline, borderBottomColor: colors.separator },
  cell: { flex: 1, minWidth: 0 },
  header: { ...typography.label, color: colors.textSecondary, paddingVertical: spacing.sm, paddingLeft: spacing.sm },
  day: { height: 52, padding: spacing.xs + 2 },
  divided: { borderLeftWidth: lines.hairline, borderLeftColor: colors.separator },
  selected: { backgroundColor: colors.surfaceSoft },
  dayTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  number: { ...typography.smallBold, color: colors.text, fontVariant: ['tabular-nums'] },
  outside: { color: colors.textDisabled },
  today: { color: colors.textActive },
  numberSelected: { borderBottomWidth: lines.selection, borderBottomColor: colors.accent },
  dot: { width: 5, height: 5, marginTop: spacing.xs, marginRight: spacing.xxs, backgroundColor: colors.textSecondary },
});
