import React, { useCallback, useState } from 'react';
import { Linking, Platform, Text } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { errorText } from '../../api/errors';
import { integrationsApi, integrationsAvailable } from '../../api/integrationsApi';
import type { IntegrationOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Section, InfoRow, Loading, Screen, styles } from '../../ui/components';
import { confirm } from '../../ui/confirm';
import { formatDateTime } from '../../ui/dates';
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

export default function IntegrationsScreen({ navigation, route }: Props) {
  const { data, loading, error, setError, reload } = useFocusLoad(integrationsApi.list);
  const [busy, setBusy] = useState<'connect' | 'sync' | 'disconnect' | null>(null);
  const [info, setInfo] = useState<string | null>(() => returnMessage(route.params));
  const wahoo = data?.find((i) => i.provider === 'wahoo') ?? null;
  const available = integrationsAvailable();

  const run = useCallback(
    async (kind: 'connect' | 'sync' | 'disconnect', action: () => Promise<void>) => {
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
    if (ok) await run('disconnect', async () => {
      await integrationsApi.wahooDisconnect();
      await reload();
    });
  };

  return (
    <Screen title="Integraciones" onBack={navigation.goBack} error={error} onDismissError={() => setError(null)} refreshing={loading && !!data} onRefresh={reload}>
      {info ? (
        <Section>
          <Text style={styles.text}>{info}</Text>
        </Section>
      ) : null}
      {loading && !data ? <Loading /> : null}
      {data ? (
        <Section title="Wahoo">
          {!available ? (
            <Text style={styles.muted}>
              Con datos de prueba (EXPO_PUBLIC_API_MOCK=on o sin EXPO_PUBLIC_API_URL) no se puede conectar Wahoo: necesita la API real.
            </Text>
          ) : null}
          {wahoo ? (
            <>
              <InfoRow label="Estado" value={STATUS_LABELS[wahoo.status]} />
              <InfoRow label="Conectada" value={formatDateTime(wahoo.connected_at, false)} />
              <InfoRow label="Última sincronización" value={wahoo.last_sync_at ? formatDateTime(wahoo.last_sync_at, false) : 'Nunca'} />
              {wahoo.last_error ? <Text style={styles.muted}>Último error: {wahoo.last_error}</Text> : null}
              {wahoo.status === 'active' ? (
                <Button title="Sincronizar actividades" onPress={sync} loading={busy === 'sync'} disabled={!!busy || !available} />
              ) : (
                <Button title="Volver a conectar" onPress={connect} loading={busy === 'connect'} disabled={!!busy || !available} />
              )}
              <Button title="Desconectar" variant="danger" onPress={disconnect} loading={busy === 'disconnect'} disabled={!!busy || !available} />
            </>
          ) : (
            <>
              <Text style={styles.muted}>Conecta Wahoo para importar tus actividades de ciclismo.</Text>
              <Button title="Conectar Wahoo" onPress={connect} loading={busy === 'connect'} disabled={!!busy || !available} />
            </>
          )}
        </Section>
      ) : null}
    </Screen>
  );
}
