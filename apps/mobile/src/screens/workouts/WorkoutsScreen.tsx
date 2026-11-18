import React from 'react';
import type { NavigationProp, ParamListBase } from '@react-navigation/native';

import { Button, PendingFeature, Screen } from '../../ui/components';

type Props = { navigation: NavigationProp<ParamListBase> };

/**
 * Pestaña Rendimiento (por ahora, la antigua pantalla de Entrenos; se recompone en la fase 1). La API todavía no expone el plan ni las actividades sincronizadas (la tabla
 * `activities` existe, pero sin endpoint), así que la pantalla sólo explica qué falta.
 */
export default function WorkoutsScreen({ navigation }: Props) {
  return (
    <Screen title="Rendimiento" mockBanner={false}>
      <PendingFeature title="Plan de entrenamiento">
        La generación y consulta del plan semanal todavía no existe en la API. Cuando esté, aquí verás las sesiones planificadas.
      </PendingFeature>
      <PendingFeature title="Actividades realizadas">
        Las actividades importadas de Wahoo se guardan ya en la API, pero aún no hay un endpoint para consultarlas desde la app.
      </PendingFeature>
      <Button title="Conectar o sincronizar Wahoo" variant="secondary" onPress={() => navigation.navigate('Integrations')} />
    </Screen>
  );
}
