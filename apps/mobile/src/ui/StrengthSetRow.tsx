/**
 * Fila de una serie de fuerza (propuesta v3: filas con filete, sin tarjetas). A la izquierda la casilla
 * de hecha; después el número de serie y los campos compactos: repeticiones o segundos y peso, y, si se
 * piden, RPE y RIR en una segunda línea. Sin estado: avisa de cada cambio.
 */
import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { Icon } from './Icon';
import { colors, lines, radius, spacing, typography } from './theme';

export type SetRowField = 'value' | 'weight' | 'rpe' | 'rir';

type Props = {
  setNumber: number;
  done: boolean;
  /** Registrada como no completada (desde otro cliente): se indica junto al número. */
  failed?: boolean;
  /** «rep.» o «s». */
  unit: string;
  values: Record<SetRowField, string>;
  invalid: SetRowField[];
  showEffort: boolean;
  disabled?: boolean;
  onToggle: () => void;
  onChange: (field: SetRowField, text: string) => void;
};

function SmallInput({
  value,
  onChangeText,
  unit,
  label,
  invalid,
  disabled,
  placeholder,
  decimal,
}: {
  value: string;
  onChangeText: (t: string) => void;
  unit: string;
  label: string;
  invalid: boolean;
  disabled?: boolean;
  placeholder?: string;
  decimal?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.inputGroup}>
      <TextInput
        style={[styles.input, focused && styles.inputFocused, invalid && styles.inputInvalid, disabled && styles.inputDisabled]}
        value={value}
        onChangeText={onChangeText}
        editable={!disabled}
        placeholder={placeholder}
        placeholderTextColor={colors.textDisabled}
        keyboardType={decimal ? 'decimal-pad' : 'number-pad'}
        accessibilityLabel={label}
        accessibilityHint={invalid ? 'Valor no válido' : undefined}
        selectTextOnFocus
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      <Text style={styles.unit}>{unit}</Text>
    </View>
  );
}

export function StrengthSetRow({ setNumber, done, failed, unit, values, invalid, showEffort, disabled, onToggle, onChange }: Props) {
  const label = `Serie ${setNumber}`;
  return (
    <View style={styles.row}>
      <View style={styles.main}>
        <Pressable
          onPress={onToggle}
          disabled={disabled}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: done, disabled: !!disabled }}
          accessibilityLabel={`${label} hecha`}
          hitSlop={6}
          style={({ pressed }) => [styles.check, pressed && styles.pressed]}
        >
          <Icon name={done ? 'setDone' : 'setPending'} size={24} color={done ? colors.textActive : colors.textSecondary} />
        </Pressable>
        <View style={styles.number}>
          <Text style={[styles.numberText, done && styles.numberDone]}>{setNumber}</Text>
          {failed ? <Text style={styles.failed}>no hecha</Text> : null}
        </View>
        <SmallInput
          value={values.value}
          onChangeText={(t) => onChange('value', t)}
          unit={unit}
          label={`${label}: ${unit === 's' ? 'segundos' : 'repeticiones'}`}
          invalid={invalid.includes('value')}
          disabled={disabled}
        />
        <SmallInput
          value={values.weight}
          onChangeText={(t) => onChange('weight', t)}
          unit="kg"
          label={`${label}: peso en kg (opcional)`}
          invalid={invalid.includes('weight')}
          disabled={disabled}
          placeholder="—"
          decimal
        />
      </View>
      {showEffort ? (
        <View style={styles.effort}>
          <SmallInput
            value={values.rpe}
            onChangeText={(t) => onChange('rpe', t)}
            unit="RPE"
            label={`${label}: RPE de 1 a 10 (opcional)`}
            invalid={invalid.includes('rpe')}
            disabled={disabled}
            placeholder="—"
          />
          <SmallInput
            value={values.rir}
            onChangeText={(t) => onChange('rir', t)}
            unit="RIR"
            label={`${label}: repeticiones en reserva, de 0 a 10 (opcional)`}
            invalid={invalid.includes('rir')}
            disabled={disabled}
            placeholder="—"
          />
        </View>
      ) : null}
    </View>
  );
}

const CHECK_WIDTH = 32;
const NUMBER_WIDTH = 28;

const styles = StyleSheet.create({
  row: { paddingVertical: spacing.sm, borderTopWidth: lines.hairline, borderTopColor: colors.separator, gap: spacing.sm },
  main: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  check: { width: CHECK_WIDTH, height: 36, alignItems: 'center', justifyContent: 'center', borderRadius: radius.sm },
  pressed: { opacity: 0.6 },
  number: { width: NUMBER_WIDTH },
  numberText: { ...typography.bodyBold, color: colors.text, fontVariant: ['tabular-nums'] },
  numberDone: { color: colors.textActive },
  failed: { ...typography.caption, color: colors.danger },
  effort: { flexDirection: 'row', gap: spacing.md, paddingLeft: CHECK_WIDTH + NUMBER_WIDTH + 2 * spacing.md },
  inputGroup: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  input: {
    ...typography.bodyBold,
    fontVariant: ['tabular-nums'],
    color: colors.text,
    width: 64,
    textAlign: 'right',
    borderRadius: radius.sm,
    borderWidth: lines.hairline,
    borderColor: colors.separatorStrong,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs + 2,
  },
  inputFocused: { borderColor: colors.accent },
  inputInvalid: { borderColor: colors.danger },
  inputDisabled: { color: colors.textSecondary, borderColor: colors.separator },
  unit: { ...typography.small, color: colors.textSecondary, minWidth: 28 },
});
