/**
 * Pestaña Coach (propuesta v3, #25): conversación sin contenedores, con el icono de globo de
 * conversación. El backend del coach llega en la fase 3; hasta entonces la pantalla tiene su
 * forma final con un estado vacío y la caja de texto deshabilitada.
 */
import React from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { styles as base } from '../../ui/components';
import { Icon } from '../../ui/Icon';
import { colors, lines, radius, spacing, typography } from '../../ui/theme';

export default function CoachChatScreen() {
  return (
    <SafeAreaView style={base.safe} edges={['top']}>
      <View style={[base.column, styles.body]}>
        <View style={styles.header}>
          <Text style={base.title} accessibilityRole="header">
            Coach
          </Text>
          <Text style={base.muted}>Conoce tu plan, tu calendario y tus sensaciones.</Text>
        </View>
        <View style={styles.empty}>
          <Icon name="coach" size={40} color={colors.textSecondary} />
          <Text style={styles.emptyTitle}>Disponible cuando se active el coach</Text>
          <Text style={[base.muted, styles.center]}>
            Podrás contarle cómo te encuentras o qué ha cambiado en tu agenda, y te propondrá ajustes del plan.
          </Text>
        </View>
      </View>
      <View style={styles.composeBar}>
        <View style={[base.column, styles.compose]}>
          <TextInput
            style={styles.input}
            placeholder="Cuéntame qué ha cambiado…"
            placeholderTextColor={colors.textDisabled}
            editable={false}
            accessibilityLabel="Mensaje al coach (no disponible todavía)"
          />
          <View style={styles.send} accessibilityRole="button" accessibilityLabel="Enviar" accessibilityState={{ disabled: true }}>
            <Icon name="send" size={18} color={colors.onPrimary} />
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  body: { flex: 1 },
  header: { paddingTop: spacing.xl, gap: spacing.xs },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md, paddingHorizontal: spacing.xl, paddingBottom: spacing.xxxl },
  emptyTitle: { ...typography.bodyBold, color: colors.text, textAlign: 'center' },
  center: { textAlign: 'center' },
  composeBar: { borderTopWidth: lines.hairline, borderTopColor: colors.separator, backgroundColor: colors.background },
  compose: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.sm + 2 },
  input: { ...typography.body, flex: 1, color: colors.text, paddingVertical: spacing.sm },
  send: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.primary, opacity: 0.35, borderRadius: radius.sm },
});
