/** Conversaciones anteriores con el coach (#56), de la más reciente a la más antigua. */
import React, { useCallback } from 'react';
import { Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { coachApi } from '../../api/coachApi';
import type { ConversationOut } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Loading, Screen, styles } from '../../ui/components';
import { formatDateTime } from '../../ui/dates';
import { Row, RowGroup } from '../../ui/Row';
import { useFocusLoad } from '../../ui/useAsync';

type Props = NativeStackScreenProps<RootStackParamList, 'CoachConversations'>;

function conversationTitle(c: ConversationOut): string {
  return c.title ?? (c.kind === 'intake' ? 'Toma de contacto' : 'Conversación sin mensajes');
}

function conversationSubtitle(c: ConversationOut): string {
  const when = formatDateTime(c.last_message_at ?? c.created_at, false);
  if (c.kind !== 'intake') return when;
  return `${when} · ${c.intake_completed_at ? 'toma de contacto hecha' : 'toma de contacto en curso'}`;
}

export default function CoachConversationsScreen({ navigation }: Props) {
  const load = useCallback(() => coachApi.listConversations(100), []);
  const { data, loading, error, setError, reload } = useFocusLoad(load);
  const open = (conversationId: string) => navigation.navigate('MainTabs', { screen: 'Coach', params: { conversationId } });

  return (
    <Screen
      title="Conversaciones"
      eyebrow="Coach"
      onBack={() => navigation.goBack()}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={reload}
    >
      <View style={styles.titleBlock}>
        <Button title="Nueva conversación" onPress={() => open('new')} />
      </View>
      {loading && !data ? <Loading /> : null}
      {data && data.length === 0 ? <Text style={styles.muted}>Todavía no has hablado con el coach.</Text> : null}
      {data && data.length > 0 ? (
        <RowGroup title="Anteriores">
          {data.map((c) => (
            <Row
              key={c.id}
              icon={c.kind === 'intake' ? 'coachMemory' : 'coach'}
              title={conversationTitle(c)}
              subtitle={conversationSubtitle(c)}
              onPress={() => open(c.id)}
            />
          ))}
        </RowGroup>
      ) : null}
    </Screen>
  );
}
