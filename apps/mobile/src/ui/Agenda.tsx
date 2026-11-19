/**
 * Agenda: una fila por día con filetes, sin tarjetas. A la izquierda el día (hoy, subrayado en
 * `textActive`) y a la derecha sus elementos, cada uno con un icono por tipo. Sin estado: recibe los
 * días ya agrupados y avisa al pulsar un elemento.
 */
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Icon, type IconName } from './Icon';
import { colors, lines, spacing, typography } from './theme';

export type AgendaEntry = {
  key: string;
  title: string;
  subtitle?: string;
  icon: IconName;
  /** Elemento destacado (la carrera): icono y título en `textActive`. */
  highlight?: boolean;
  /** Elemento ya hecho o saltado: título en `textSecondary`. */
  muted?: boolean;
  /** Elemento sin pantalla de detalle: no se puede pulsar. */
  disabled?: boolean;
};

export type AgendaDay = {
  /** YYYY-MM-DD. */
  date: string;
  /** «LUN». */
  weekday: string;
  /** «16». */
  day: string;
  items: AgendaEntry[];
};

type ItemsProps = { items: AgendaEntry[]; onPressItem?: (key: string) => void };

/** Lista de elementos de un día, sin la columna de fecha (también se usa bajo la rejilla del mes). */
export function AgendaItems({ items, onPressItem }: ItemsProps) {
  return (
    <View style={styles.items}>
      {items.map((item) => {
        const tint = item.highlight ? colors.textActive : colors.textSecondary;
        const pressable = !!onPressItem && !item.disabled;
        return (
          <Pressable
            key={item.key}
            onPress={pressable ? () => onPressItem(item.key) : undefined}
            disabled={!pressable}
            accessibilityRole={pressable ? 'button' : undefined}
            accessibilityLabel={[item.title, item.subtitle].filter(Boolean).join(', ')}
            style={({ pressed }) => [styles.item, pressed && styles.pressed]}
          >
            <View style={styles.itemIcon}>
              <Icon name={item.icon} size={16} color={tint} />
            </View>
            <View style={styles.itemText}>
              <Text style={[styles.itemTitle, item.highlight && styles.highlight, item.muted && styles.muted]}>{item.title}</Text>
              {item.subtitle ? <Text style={styles.itemSubtitle}>{item.subtitle}</Text> : null}
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

type Props = {
  days: AgendaDay[];
  /** YYYY-MM-DD de hoy, para marcarlo. */
  today: string;
  /** Texto de un día sin elementos. */
  emptyText: string;
  onPressItem?: (key: string) => void;
};

export function Agenda({ days, today, emptyText, onPressItem }: Props) {
  return (
    <View>
      {days.map((d, i) => {
        const isToday = d.date === today;
        return (
          <View key={d.date} style={[styles.day, i > 0 && styles.ruled]} accessibilityLabel={isToday ? `Hoy, ${d.weekday} ${d.day}` : undefined}>
            <View style={styles.dayLabel}>
              <Text style={[styles.weekday, isToday && styles.todayText]}>{d.weekday}</Text>
              <Text style={[styles.dayNumber, isToday && styles.todayNumber]}>{d.day}</Text>
            </View>
            {d.items.length > 0 ? (
              <AgendaItems items={d.items} onPressItem={onPressItem} />
            ) : (
              <Text style={styles.empty}>{emptyText}</Text>
            )}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  day: { flexDirection: 'row', gap: spacing.md, paddingVertical: spacing.md },
  ruled: { borderTopWidth: lines.hairline, borderTopColor: colors.separator },
  dayLabel: { width: 44, alignItems: 'flex-start' },
  weekday: { ...typography.label, color: colors.textSecondary },
  dayNumber: { ...typography.heading, color: colors.text, fontVariant: ['tabular-nums'] },
  todayText: { color: colors.textActive },
  todayNumber: { color: colors.textActive, borderBottomWidth: lines.selection, borderBottomColor: colors.textActive },
  items: { flex: 1, minWidth: 0, gap: spacing.sm, paddingTop: spacing.xxs },
  item: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start', paddingVertical: spacing.xxs },
  pressed: { backgroundColor: colors.surfaceSoft },
  itemIcon: { paddingTop: spacing.xxs },
  itemText: { flex: 1, minWidth: 0, gap: spacing.xxs },
  itemTitle: { ...typography.smallBold, color: colors.text },
  highlight: { color: colors.textActive },
  muted: { color: colors.textSecondary },
  itemSubtitle: { ...typography.caption, color: colors.textSecondary },
  empty: { ...typography.small, color: colors.textDisabled, flex: 1, paddingTop: spacing.xs },
});
