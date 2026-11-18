/**
 * Componentes base de la app, con el sistema visual de la propuesta v3 (#23): fondo plano,
 * jerarquía por tipografía y espacio, filetes de 1 px y esquinas de 1–2 px. Todos los valores
 * vienen de `theme.ts`.
 */
import React, { useEffect, useRef, useState } from 'react';
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

import { apiConfig } from '../api/config';
import { useUsingMock } from '../api/mockStatus';
import { Icon } from './Icon';
import { colors, fonts, layout, lines, radius, spacing, typography } from './theme';

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
  /** false en pantallas que no piden datos a la API (el aviso de datos de prueba no aplica). */
  mockBanner?: boolean;
};

/** Pantalla con barra sin fondo (volver y acciones) y título grande que se desplaza con el contenido. */
export function Screen({ title, onBack, right, children, refreshing, onRefresh, error, onDismissError, mockBanner = true }: ScreenProps) {
  const scroll = useRef<ScrollView>(null);
  useEffect(() => {
    if (error) scroll.current?.scrollTo({ y: 0, animated: true });
  }, [error]);
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {onBack || right ? (
        <View style={[styles.column, styles.topBar]}>
          {onBack ? (
            <Pressable onPress={onBack} accessibilityRole="button" accessibilityLabel="Volver" style={styles.iconButton} hitSlop={8}>
              <Icon name="back" size={24} />
            </Pressable>
          ) : (
            <View />
          )}
          {right ? <View style={styles.topBarRight}>{right}</View> : null}
        </View>
      ) : null}
      <ScrollView
        ref={scroll}
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={colors.accent} colors={[colors.accent]} /> : undefined
        }
      >
        <View style={[styles.column, styles.content, !(onBack || right) && styles.contentNoBar]}>
          <Text style={styles.title} accessibilityRole="header">
            {title}
          </Text>
          {mockBanner ? <MockBanner /> : null}
          <ErrorBanner message={error ?? null} onDismiss={onDismissError} />
          {children}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

/** Botón de icono para la barra de `Screen` (`right`). */
export function IconButton({ icon, label, onPress }: { icon: React.ComponentProps<typeof Icon>['name']; label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} style={styles.iconButton} hitSlop={8}>
      <Icon name={icon} size={24} />
    </Pressable>
  );
}

/** Aviso cuando los datos vienen de los ejemplos del contrato (backend sin implementar). */
export function MockBanner() {
  const usingMock = useUsingMock();
  if (!usingMock) return null;
  return (
    <View style={[styles.banner, styles.warning]}>
      <Text style={styles.warningText}>
        {apiConfig.mockMode === 'auto' && apiConfig.baseUrl
          ? 'Datos de prueba del contrato: la API aún no implementa este endpoint (501).'
          : 'Datos de prueba del contrato (EXPO_PUBLIC_API_MOCK=on o sin EXPO_PUBLIC_API_URL).'}{' '}
        Los cambios sólo duran hasta recargar la app.
      </Text>
    </View>
  );
}

export function ErrorBanner({ message, onDismiss }: { message: string | null; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <Pressable onPress={onDismiss} style={[styles.banner, styles.error]} accessibilityRole="alert">
      <Text style={styles.errorText}>{message}</Text>
    </Pressable>
  );
}

export function Loading() {
  return (
    <View style={styles.loading}>
      <ActivityIndicator size="large" color={colors.accent} />
    </View>
  );
}

type BlockProps = { title?: string; children: React.ReactNode; right?: React.ReactNode };

function BlockHeader({ title, right }: Omit<BlockProps, 'children'>) {
  if (!title && !right) return null;
  return (
    <View style={styles.blockHeader}>
      {title ? <Text style={styles.sectionLabel}>{title}</Text> : <View />}
      {right}
    </View>
  );
}

/**
 * Superficie destacada (celeste). Sólo para lo que debe resaltar en la pantalla, como el entreno
 * del día; el resto del contenido va en `Section`, directamente sobre el fondo.
 */
export function Card({ title, children, right }: BlockProps) {
  return (
    <View style={styles.card}>
      <BlockHeader title={title} right={right} />
      {children}
    </View>
  );
}

/** Bloque de contenido sobre el fondo, con etiqueta de sección. Sin caja ni borde. */
export function Section({ title, children, right }: BlockProps) {
  return (
    <View style={styles.section}>
      <BlockHeader title={title} right={right} />
      {children}
    </View>
  );
}

/** Fila etiqueta–valor con filete superior. */
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
  const [focused, setFocused] = useState(false);
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, multiline && styles.multiline, focused && styles.inputFocused]}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.textDisabled}
        keyboardType={keyboardType}
        multiline={multiline}
        autoCapitalize="none"
        accessibilityLabel={label}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

export function SwitchField({ label, value, onValueChange }: { label: string; value: boolean; onValueChange: (v: boolean) => void }) {
  return (
    <View style={[styles.field, styles.switchRow]}>
      <Text style={styles.switchLabel}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ true: colors.accent, false: colors.separator }}
        thumbColor={colors.onPrimary}
        ios_backgroundColor={colors.separator}
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

/** Selector de vistas: texto con subrayado en la opción activa. */
export function SegmentedTabs<T extends string>({ options, value, onChange }: { options: Option<T>[]; value: T; onChange: (value: T) => void }) {
  return (
    <View style={styles.segmented} accessibilityRole="tablist">
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <Pressable
            key={o.value}
            onPress={() => onChange(o.value)}
            style={[styles.segment, selected && styles.segmentSelected]}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
          >
            <Text style={[styles.segmentText, selected && styles.segmentTextSelected]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  /**
   * `primary`: relleno oscuro. `secondary`: suave (lavanda). `text`: sólo texto activo.
   * `danger`: como `text`, en color de error, para acciones destructivas.
   */
  variant?: 'primary' | 'secondary' | 'text' | 'danger';
  disabled?: boolean;
  loading?: boolean;
};

export function Button({ title, onPress, variant = 'primary', disabled, loading }: ButtonProps) {
  const inactive = disabled || loading;
  const textStyle =
    variant === 'primary' ? styles.buttonTextPrimary : variant === 'text' ? styles.buttonTextLink : variant === 'danger' ? styles.buttonTextDanger : null;
  return (
    <Pressable
      onPress={onPress}
      disabled={inactive}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      style={({ pressed }) => [styles.button, buttonVariants[variant], pressed && styles.pressed, inactive && styles.disabled]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? colors.onPrimary : colors.text} />
      ) : (
        <Text style={[styles.buttonText, textStyle]}>{title}</Text>
      )}
    </Pressable>
  );
}

export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  /** Columna centrada: en web el contenido no pasa de `layout.contentMaxWidth`. */
  column: { width: '100%', maxWidth: layout.contentMaxWidth, alignSelf: 'center', paddingHorizontal: spacing.lg },
  topBar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 48 },
  topBarRight: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  iconButton: { padding: spacing.xs, marginHorizontal: -spacing.xs, borderRadius: radius.sm },
  scroll: { flexGrow: 1, paddingBottom: spacing.xxxl },
  content: { gap: spacing.xl },
  contentNoBar: { paddingTop: spacing.xl },
  title: { ...typography.display, color: colors.text },
  banner: { padding: spacing.md, borderRadius: radius.sm },
  warning: { backgroundColor: colors.warningSurface },
  warningText: { ...typography.small, color: colors.warning },
  error: { backgroundColor: colors.dangerSurface },
  errorText: { ...typography.small, color: colors.danger },
  loading: { paddingVertical: spacing.xxxl, alignItems: 'center' },
  card: { backgroundColor: colors.surfaceHighlight, borderRadius: radius.sm, padding: spacing.lg, gap: spacing.sm },
  section: { gap: spacing.md },
  blockHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: spacing.md, minHeight: 24 },
  sectionLabel: { ...typography.label, color: colors.textSecondary, flexShrink: 1 },
  /** Compatibilidad: título de bloque. */
  cardTitle: { ...typography.label, color: colors.textSecondary },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: spacing.md,
    paddingVertical: spacing.sm + 2,
    borderTopWidth: lines.hairline,
    borderTopColor: colors.separator,
  },
  infoLabel: { ...typography.small, color: colors.textSecondary, flexShrink: 1 },
  infoValue: { ...typography.bodyBold, color: colors.text, flexShrink: 1, textAlign: 'right' },
  field: { gap: spacing.xs },
  label: { ...typography.small, color: colors.textSecondary },
  hint: { ...typography.caption, color: colors.textSecondary },
  input: {
    ...typography.body,
    color: colors.text,
    backgroundColor: colors.background,
    borderRadius: radius.sm,
    borderWidth: lines.hairline,
    borderColor: colors.separatorStrong,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
  },
  inputFocused: { borderColor: colors.accent },
  multiline: { minHeight: 88, textAlignVertical: 'top' },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.md },
  switchLabel: { ...typography.body, color: colors.text, flexShrink: 1 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 7,
    borderRadius: radius.sm,
    borderWidth: lines.hairline,
    borderColor: colors.separator,
  },
  chipSelected: { borderColor: colors.accent, backgroundColor: colors.surfaceSoft },
  chipText: { ...typography.small, color: colors.textSecondary },
  chipTextSelected: { ...typography.smallBold, color: colors.textActive },
  segmented: { flexDirection: 'row', gap: spacing.lg + 2, borderBottomWidth: lines.hairline, borderBottomColor: colors.separator },
  segment: { paddingTop: spacing.sm, paddingBottom: spacing.sm + 1, marginBottom: -lines.hairline, borderBottomWidth: lines.selection, borderBottomColor: 'transparent' },
  segmentSelected: { borderBottomColor: colors.accent },
  segmentText: { ...typography.smallBold, color: colors.textSecondary },
  segmentTextSelected: { color: colors.text },
  button: {
    minHeight: 44,
    borderRadius: radius.sm,
    paddingVertical: 10,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { opacity: 0.8 },
  disabled: { opacity: 0.45 },
  buttonText: { ...typography.smallBold, color: colors.text },
  buttonTextPrimary: { color: colors.onPrimary },
  buttonTextLink: { color: colors.textActive },
  buttonTextDanger: { color: colors.danger },
  muted: { ...typography.small, color: colors.textSecondary },
  text: { ...typography.body, color: colors.text },
  /** Texto destacado dentro de un bloque (nombre de un evento, de una carrera…). */
  textStrong: { ...typography.bodyBold, color: colors.text },
  /** Texto activo (enlaces, tipo de evento, códigos). */
  textActive: { ...typography.smallBold, color: colors.textActive },
  /** Error dentro de un bloque. */
  errorInline: { ...typography.small, color: colors.danger },
  pendingTitle: { fontFamily: fonts.bold, fontSize: typography.body.fontSize, color: colors.text },
  pending: { gap: spacing.xs, paddingTop: spacing.md, borderTopWidth: lines.hairline, borderTopColor: colors.separator },
});

const buttonVariants = StyleSheet.create({
  primary: { backgroundColor: colors.primary },
  secondary: { backgroundColor: colors.surfaceSoft },
  text: { backgroundColor: 'transparent', paddingHorizontal: spacing.xs, alignSelf: 'flex-start' },
  danger: { backgroundColor: 'transparent', paddingHorizontal: spacing.xs, alignSelf: 'flex-start' },
});

/** Funcionalidad todavía sin endpoint en la API: estado vacío explícito, sin datos inventados. */
export function PendingFeature({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.pending}>
      <Text style={styles.pendingTitle}>{title}</Text>
      <Text style={styles.muted}>{children}</Text>
    </View>
  );
}
