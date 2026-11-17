import React from 'react';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../navigation/types';
import { PendingFeature, Screen } from '../../ui/components';

type Props = NativeStackScreenProps<RootStackParamList, 'CoachChat'>;

/** El coach (LLM con tools sobre la API) todavía no tiene endpoint. */
export default function CoachChatScreen({ navigation }: Props) {
  return (
    <Screen title="Coach" onBack={navigation.goBack} mockBanner={false}>
      <PendingFeature title="Chat con el coach">
        El coach todavía no está disponible en la API de CoachIA. El chat del MVP usaba funciones de Supabase que ya no existen.
      </PendingFeature>
    </Screen>
  );
}
