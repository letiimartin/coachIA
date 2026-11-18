import React from 'react';

import { PendingFeature, Screen } from '../../ui/components';

/** Pestaña Coach. El coach (LLM con tools sobre la API) todavía no tiene endpoint. */
export default function CoachChatScreen() {
  return (
    <Screen title="Coach" mockBanner={false}>
      <PendingFeature title="Chat con el coach">
        El coach todavía no está disponible en la API de CoachIA. El chat del MVP usaba funciones de Supabase que ya no existen.
      </PendingFeature>
    </Screen>
  );
}
