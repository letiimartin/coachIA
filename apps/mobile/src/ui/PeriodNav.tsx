/** Navegación entre periodos (semana o mes): anterior, etiqueta centrada y siguiente. Sin estado. */
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Icon } from './Icon';
import { colors, radius, spacing, typography } from './theme';

type Props = {
  label: string;
  caption?: string;
  onPrevious: () => void;
  onNext: () => void;
  previousLabel: string;
  nextLabel: string;
};

export function PeriodNav({ label, caption, onPrevious, onNext, previousLabel, nextLabel }: Props) {
  return (
    <View style={styles.row}>
      <Pressable onPress={onPrevious} accessibilityRole="button" accessibilityLabel={previousLabel} hitSlop={8} style={styles.button}>
        <Icon name="back" size={22} />
      </Pressable>
      <View style={styles.center}>
        <Text style={styles.label} accessibilityRole="header">
          {label}
        </Text>
        {caption ? <Text style={styles.caption}>{caption}</Text> : null}
      </View>
      <Pressable onPress={onNext} accessibilityRole="button" accessibilityLabel={nextLabel} hitSlop={8} style={styles.button}>
        <Icon name="forward" size={22} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  button: { padding: spacing.xs, marginHorizontal: -spacing.xs, borderRadius: radius.sm },
  center: { alignItems: 'center', gap: spacing.xxs },
  label: { ...typography.bodyBold, color: colors.text },
  caption: { ...typography.caption, color: colors.textSecondary },
});
