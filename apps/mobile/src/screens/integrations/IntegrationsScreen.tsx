/**
 * Ajustes y conexiones (propuesta v3, #25). Se abre desde el engranaje del Perfil y es también la
 * pantalla a la que vuelve el OAuth de Wahoo (ruta `integrations`). Integra la gestión de Wahoo de
 * #20 (estado, sincronizar, desconectar), la zona horaria y cerrar sesión. Sin selector de
 * apariencia mientras no haya modo oscuro.
 */
import React, { useCallback, useState } from 'react';
import { Linking, Platform, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { athleteApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import { integrationsApi, integrationsAvailable } from '../../api/integrationsApi';
import type { IntegrationOut, ProfileOut } from '../../api/types';
import { supabase } from '../../lib/supabase';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Field, InfoRow, Loading, Screen, Section, styles as base } from '../../ui/components';
import { confirm } from '../../ui/confirm';
import { formatDateTime } from '../../ui/dates';
import { Row, RowGroup, StatusDot } from '../../ui/Row';
import { spacing } from '../../ui/theme';
import { useFocusLoad } from '../../ui/useAsync';

type Props = NativeStackScreenProps<RootStackParamList, 'Integrations'>;

const STATUS_LABELS: Record<IntegrationOut['status'], string> = {
  active: 'Conectada',
  revoked: 'Revocada',
  error: 'Con errores',
};

/** Motivos que devuelve la API en la redirección del callback OAuth. */
const RETURN_REASONS: Record<string, string> = {
  invalid_state: 'la solicitud ha caducado o no es válida. Vuelve a intentarlo.',
  access_denied: 'has denegado el acceso en Wahoo.',
  token_exchange: 'no se ha podido completar la autorización con Wahoo.',
};

function returnMessage(params: Props['route']['params']): string | null {
  if (params?.provider !== 'wahoo' || !params.status) return null;
  if (params.status === 'connected') return 'Wahoo conectado correctamente.';
  const reason = params.reason ? (RETURN_REASONS[params.reason] ?? params.reason) : 'error desconocido.';
  return `No se ha podido conectar Wahoo: ${reason}`;
}

type SettingsData = { integrations: IntegrationOut[]; profile: ProfileOut | null; profileError: string | null };

async function loadSettings(): Promise<SettingsData> {
  const [integrations, profile] = await Promise.all([
    integrationsApi.list(),
    athleteApi.getProfile().then(
      (p) => ({ ok: true as const, p }),
      (e: unknown) => ({ ok: false as const, e: errorText(e) }),
    ),
  ]);
  return { integrations, profile: profile.ok ? profile.p : null, profileError: profile.ok ? null : profile.e };
}

export default function IntegrationsScreen({ navigation, route }: Props) {
  const load = useCallback(loadSettings, []);
  const { data, setData, loading, error, setError, reload } = useFocusLoad(load);
  const [busy, setBusy] = useState<'connect' | 'sync' | 'disconnect' | 'timezone' | null>(null);
  const [info, setInfo] = useState<string | null>(() => returnMessage(route.params));
  const [timezone, setTimezone] = useState<string | null>(null);
  const wahoo = data?.integrations.find((i) => i.provider === 'wahoo') ?? null;
  const available = integrationsAvailable();

  const run = useCallback(
    async (kind: NonNullable<typeof busy>, action: () => Promise<void>) => {
      setBusy(kind);
      setError(null);
      setInfo(null);
      try {
        await action();
      } catch (e) {
        setError(errorText(e));
      } finally {
        setBusy(null);
      }
    },
    [setError],
  );

  const connect = () =>
    run('connect', async () => {
      // La API firma el `state`, recibe el callback y redirige de vuelta a esta pantalla.
      const { authorize_url } = await integrationsApi.wahooAuthorizeUrl(Platform.OS === 'web' ? 'web' : 'mobile');
      if (Platform.OS === 'web' && typeof window !== 'undefined') window.location.assign(authorize_url);
      else await Linking.openURL(authorize_url);
    });

  const sync = () =>
    run('sync', async () => {
      const r = await integrationsApi.wahooSync();
      setInfo(`Sincronización completada: ${r.created} nuevas, ${r.updated} actualizadas, ${r.unchanged} sin cambios.`);
      await reload();
    });

  const disconnect = async () => {
    const ok = await confirm('Desconectar Wahoo', 'CoachIA dejará de importar tus actividades de Wahoo.', 'Desconectar');
    if (ok)
      await run('disconnect', async () => {
        await integrationsApi.wahooDisconnect();
        await reload();
      });
  };

  const saveTimezone = () => {
    if (timezone === null || !data?.profile) return;
    const tz = timezone.trim();
    if (!tz || tz.length > 64) return setError('Indica una zona horaria válida (p. ej. Europe/Madrid).');
    if (tz === data.profile.timezone) return setTimezone(null);
    void run('timezone', async () => {
      const profile = await athleteApi.updateProfile({ timezone: tz });
      setData({ ...data, profile });
      setTimezone(null);
    });
  };

  const logout = async () => {
    const ok = await confirm('Cerrar sesión', '¿Quieres cerrar la sesión en este dispositivo?', 'Cerrar sesión');
    if (ok) await supabase.auth.signOut();
  };

  return (
    <Screen title="Ajustes" onBack={navigation.goBack} error={error} onDismissError={() => setError(null)} refreshing={loading && !!data} onRefresh={reload}>
      {info ? <Text style={base.text}>{info}</Text> : null}
      {loading && !data ? <Loading /> : null}

      {data ? (
        <Section title="Conexiones">
          <Row
            first
            icon="sync"
            title="Wahoo"
            subtitle={wahoo ? STATUS_LABELS[wahoo.status] : 'Sin conectar. Importa tus actividades de ciclismo.'}
            value={wahoo ? <StatusDot active={wahoo.status === 'active'} /> : undefined}
          />
          {!available ? (
            <Text style={base.muted}>
              Con datos de prueba (EXPO_PUBLIC_API_MOCK=on o sin EXPO_PUBLIC_API_URL) no se puede conectar Wahoo: necesita la API real.
            </Text>
          ) : null}
          {wahoo ? (
            <>
              <InfoRow label="Conectada" value={formatDateTime(wahoo.connected_at, false)} />
              <InfoRow label="Última sincronización" value={wahoo.last_sync_at ? formatDateTime(wahoo.last_sync_at, false) : 'Nunca'} />
              {wahoo.last_error ? <Text style={base.muted}>Último error: {wahoo.last_error}</Text> : null}
              {wahoo.status === 'active' ? (
                <Button title="Sincronizar actividades" onPress={sync} loading={busy === 'sync'} disabled={!!busy || !available} />
              ) : (
                <Button title="Volver a conectar" onPress={connect} loading={busy === 'connect'} disabled={!!busy || !available} />
              )}
              <Button title="Desconectar" variant="danger" onPress={disconnect} loading={busy === 'disconnect'} disabled={!!busy || !available} />
            </>
          ) : (
            <Button title="Conectar Wahoo" onPress={connect} loading={busy === 'connect'} disabled={!!busy || !available} />
          )}
        </Section>
      ) : null}

      {data ? (
        <RowGroup title="Aplicación">
          {data.profileError ? <Text style={base.errorInline}>{data.profileError}</Text> : null}
          {data.profile && timezone === null ? (
            <Row icon="timezone" title="Zona horaria" value={data.profile.timezone} onPress={() => setTimezone(data.profile?.timezone ?? '')} />
          ) : null}
          {data.profile && timezone !== null ? (
            <View style={styles.edit}>
              <Field
                label="Zona horaria"
                value={timezone}
                onChangeText={setTimezone}
                placeholder="Europe/Madrid"
                hint="Identificador IANA, p. ej. Europe/Madrid o Atlantic/Canary."
              />
              <View style={styles.actions}>
                <View style={styles.action}>
                  <Button title="Cancelar" variant="secondary" onPress={() => setTimezone(null)} disabled={busy === 'timezone'} />
                </View>
                <View style={styles.action}>
                  <Button title="Guardar" onPress={saveTimezone} loading={busy === 'timezone'} disabled={!!busy && busy !== 'timezone'} />
                </View>
              </View>
            </View>
          ) : null}
          <Row icon="logout" title="Cerrar sesión" danger onPress={logout} />
        </RowGroup>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  edit: { gap: spacing.md, paddingVertical: spacing.sm },
  actions: { flexDirection: 'row', gap: spacing.sm },
  action: { flex: 1 },
});
