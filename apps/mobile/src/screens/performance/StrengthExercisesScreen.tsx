/** Todos los ejercicios de fuerza hechos (#33), del último hecho al más antiguo (`GET /v1/strength/progress`). */
import React from 'react';
import { Text } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { strengthProgressApi } from '../../api/strengthProgressApi';
import type { RootStackParamList } from '../../navigation/types';
import { Loading, Screen, styles } from '../../ui/components';
import { Row, RowGroup } from '../../ui/Row';
import { useFocusLoad } from '../../ui/useAsync';
import { exerciseRowProps } from './StrengthBlock';

type Props = NativeStackScreenProps<RootStackParamList, 'StrengthExercises'>;

export default function StrengthExercisesScreen({ navigation }: Props) {
  const { data, loading, error, setError, reload } = useFocusLoad(strengthProgressApi.performed);

  return (
    <Screen
      title="Ejercicios"
      eyebrow="Fuerza · progresión"
      onBack={() => navigation.goBack()}
      error={error}
      onDismissError={() => setError(null)}
      refreshing={loading && !!data}
      onRefresh={reload}
    >
      {loading && !data ? <Loading /> : null}
      {data && data.length === 0 ? <Text style={styles.muted}>Todavía no has completado ninguna sesión de fuerza.</Text> : null}
      {data && data.length > 0 ? (
        <RowGroup>
          {data.map((item) => (
            <Row key={item.exercise.id} {...exerciseRowProps(item)} onPress={() => navigation.navigate('ExerciseProgress', { id: item.exercise.id, name: item.exercise.name })} />
          ))}
        </RowGroup>
      ) : null}
    </Screen>
  );
}
