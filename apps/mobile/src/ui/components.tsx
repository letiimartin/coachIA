import React, { useEffect, useRef } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
  type KeyboardTypeOptions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ChevronLeft } from 'lucide-react-native';

import { useUsingMock } from '../api/mockStatus';
import { colors, spacing } from './theme';

type ScreenProps = {
  title: string;
  onBack?: () => void;
  right?: React.ReactNode;
  children: React.ReactNode;
  refreshing?: boolean;
  onRefresh?: () => void;
  /** Error a mostrar arriba; al aparecer, la pantalla vuelve al principio para que se vea. */
  error?: string | null;
  onDismissError?: () => void;
};

export function Screen({ title, onBack, right, children, refreshing, onRefresh, error, onDismissError }: ScreenProps) {
  const scroll = useRef<ScrollView>(null);
  useEffect(() => {
    if (error) scroll.current?.scrollTo({ y: 0, animated: true });
  }, [error]);
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        {onBack ? (
          <Pressable onPress={onBack} accessibilityRole="button" accessibilityLabel="Volver" style={styles.back}>
            <ChevronLeft size={24} color={colors.text} />
          </Pressable>
        ) : null}
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        {right}
      </View>
      <MockBanner />
      <ScrollView
        ref={scroll}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={colors.primary} /> : undefined
        }
      >
        <ErrorBanner message={error ?? null} onDismiss={onDismissError} />
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

/** Aviso cuando los datos vienen de los ejemplos del contrato (backend sin implementar). */
export function MockBanner() {
  const usingMock = useUsingMock();
  if (!usingMock) return null;
  return (
    <View style={[styles.banner, styles.warning]}>
      <Text style={styles.warningText}>
        Datos de prueba del contrato: la API aún no implementa este endpoint. Los cambios sólo duran hasta recargar la app.
      </Text>
    </View>
  );
}

export function ErrorBanner({ message, onDismiss }: { message: string | null; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <Pressable onPress={onDismiss} style={[styles.banner, styles.error, { marginHorizontal: 0, marginTop: 0 }]} accessibilityRole="alert">
      <Text style={styles.errorText}>{message}</Text>
    </Pressable>
  );
}

export function Loading() {
  return (
    <View style={styles.loading}>
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  );
}

export function Card({ title, children, right }: { title?: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <View style={styles.card}>
      {title || right ? (
        <View style={styles.cardHeader}>
          {title ? <Text style={styles.cardTitle}>{title}</Text> : <View />}
          {right}
        </View>
      ) : null}
      {children}
    </View>
  );
}

export function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

type FieldProps = {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  multiline?: boolean;
  hint?: string;
};

export function Field({ label, value, onChangeText, placeholder, keyboardType, multiline, hint }: FieldProps) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline]}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        keyboardType={keyboardType}
        multiline={multiline}
        autoCapitalize="none"
        accessibilityLabel={label}
      />
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

export function SwitchField({ label, value, onValueChange }: { label: string; value: boolean; onValueChange: (v: boolean) => void }) {
  return (
    <View style={[styles.field, styles.switchRow]}>
      <Text style={styles.label}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ true: colors.primary, false: colors.surfaceAlt }}
        accessibilityLabel={label}
      />
    </View>
  );
}

type Option<T extends string> = { value: T; label: string };

type ChipsProps<T extends string> = {
  label?: string;
  options: Option<T>[];
} & (
  | { multiple?: false; value: T | null; onChange: (value: T) => void; allowNone?: false }
  | { multiple?: false; value: T | null; onChange: (value: T | null) => void; allowNone: true }
  | { multiple: true; value: T[]; onChange: (value: T[]) => void; allowNone?: never }
);

export function Chips<T extends string>(props: ChipsProps<T>) {
  const isSelected = (v: T) => (props.multiple ? props.value.includes(v) : props.value === v);
  const toggle = (v: T) => {
    if (props.multiple) {
      props.onChange(props.value.includes(v) ? props.value.filter((x) => x !== v) : [...props.value, v]);
    } else if (props.allowNone) {
      props.onChange(props.value === v ? null : v);
    } else {
      props.onChange(v);
    }
  };
  return (
    <View style={styles.field}>
      {props.label ? <Text style={styles.label}>{props.label}</Text> : null}
      <View style={styles.chips}>
        {props.options.map((o) => {
          const selected = isSelected(o.value);
          return (
            <Pressable
              key={o.value}
              onPress={() => toggle(o.value)}
              style={[styles.chip, selected && styles.chipSelected]}
              accessibilityRole={props.multiple ? 'checkbox' : 'radio'}
              accessibilityState={{ checked: selected }}
            >
              <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{o.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  loading?: boolean;
};

export function Button({ title, onPress, variant = 'primary', disabled, loading }: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <Pressable
      onPress={onPress}
      disabled={inactive}
      accessibilityRole="button"
      style={[styles.button, styles[variant], inactive && styles.disabled]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? colors.onPrimary : colors.text} />
      ) : (
        <Text style={[styles.buttonText, variant === 'primary' && styles.buttonTextPrimary, variant === 'danger' && styles.buttonTextDanger]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  back: { padding: spacing.xs, marginLeft: -spacing.xs },
  title: { flex: 1, color: colors.text, fontSize: 22, fontWeight: '700' },
  content: { padding: spacing.lg, gap: spacing.lg, paddingBottom: 48 },
  banner: { marginHorizontal: spacing.lg, marginTop: spacing.md, padding: spacing.md, borderRadius: 10 },
  warning: { backgroundColor: colors.warningBg },
  warningText: { color: colors.warning, fontSize: 13 },
  error: { backgroundColor: colors.dangerBg },
  errorText: { color: colors.danger, fontSize: 14 },
  loading: { paddingVertical: 48, alignItems: 'center' },
  card: { backgroundColor: colors.surface, borderRadius: 14, padding: spacing.lg, gap: spacing.sm, borderWidth: 1, borderColor: colors.border },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.xs },
  cardTitle: { color: colors.text, fontSize: 16, fontWeight: '700' },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  infoLabel: { color: colors.muted, fontSize: 14 },
  infoValue: { color: colors.text, fontSize: 14, flexShrink: 1, textAlign: 'right' },
  field: { gap: spacing.xs },
  label: { color: colors.muted, fontSize: 13 },
  hint: { color: colors.muted, fontSize: 12 },
  input: {
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    borderRadius: 10,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 15,
    borderWidth: 1,
    borderColor: colors.border,
  },
  multiline: { minHeight: 80, textAlignVertical: 'top' },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: { paddingHorizontal: spacing.md, paddingVertical: 6, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surfaceAlt },
  chipSelected: { borderColor: colors.primary, backgroundColor: 'rgba(0,242,255,0.12)' },
  chipText: { color: colors.muted, fontSize: 13 },
  chipTextSelected: { color: colors.primary, fontWeight: '600' },
  button: { borderRadius: 12, paddingVertical: 12, paddingHorizontal: spacing.lg, alignItems: 'center', justifyContent: 'center' },
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.surfaceAlt, borderWidth: 1, borderColor: colors.border },
  danger: { backgroundColor: colors.dangerBg },
  disabled: { opacity: 0.5 },
  buttonText: { color: colors.text, fontSize: 15, fontWeight: '600' },
  buttonTextPrimary: { color: colors.onPrimary },
  buttonTextDanger: { color: colors.danger },
  muted: { color: colors.muted, fontSize: 14 },
  text: { color: colors.text, fontSize: 14 },
});
