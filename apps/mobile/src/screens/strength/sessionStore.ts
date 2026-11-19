// Copia local de la sesión de fuerza en curso, para retomarla sin perder datos aunque se cierre la
// app sin conexión: los borradores de las series, si quedan cambios sin enviar a la API y la hora a la
// que se marcó la primera serie (para proponer la hora de inicio y la duración al terminar).
import AsyncStorage from '@react-native-async-storage/async-storage';

import type { Drafts } from './strengthSets';

export type StoredSession = {
  drafts: Drafts;
  /** true si hay cambios que la API aún no ha confirmado. */
  unsaved: boolean;
  /** `updated_at` del entreno en la API cuando se guardaron los borradores. */
  serverUpdatedAt: string;
  /** Instante ISO en que se marcó la primera serie. */
  startedAt: string | null;
};

const key = (workoutId: string) => `coachia.strength-session.${workoutId}`;

export async function readSession(workoutId: string): Promise<StoredSession | null> {
  try {
    const raw = await AsyncStorage.getItem(key(workoutId));
    return raw ? (JSON.parse(raw) as StoredSession) : null;
  } catch {
    return null;
  }
}

export async function writeSession(workoutId: string, session: StoredSession): Promise<void> {
  try {
    await AsyncStorage.setItem(key(workoutId), JSON.stringify(session));
  } catch {
    // Sin almacenamiento local (p. ej. navegación privada): la API sigue siendo la fuente.
  }
}

export async function clearSession(workoutId: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(key(workoutId));
  } catch {
    // Ídem.
  }
}
