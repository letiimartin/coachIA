import type { NavigatorScreenParams } from '@react-navigation/native';

import type { CalendarEventOut, ThresholdOut } from '../api/types';

/** Pantallas del stack principal que reciben parámetros (las de pestañas no los usan). */
export type RootStackParamList = {
  /** Pestañas; con `screen` se abre una concreta (p. ej. una conversación del coach). */
  MainTabs: NavigatorScreenParams<MainTabParamList> | undefined;
  Thresholds: undefined;
  ThresholdForm: { current: ThresholdOut | null };
  Availability: undefined;
  EventForm: { event?: CalendarEventOut };
  EventDetail: { event: CalendarEventOut };
  /** Vuelta del OAuth de Wahoo: la API redirige a `…/integrations?provider=wahoo&status=…&reason=…`. */
  Integrations: { provider?: string; status?: string; reason?: string } | undefined;
  /** Sesión de fuerza planificada (`planned_workouts.id`). */
  StrengthSession: { id: string };
  /** Ejercicios de fuerza hechos (Rendimiento, #33). */
  StrengthExercises: undefined;
  /** Progresión de un ejercicio (`exercises.id`); `name` sólo para el título mientras carga. */
  ExerciseProgress: { id: string; name?: string };
  /** Conversaciones anteriores con el coach (#56). */
  CoachConversations: undefined;
  /** «Lo que el coach sabe de mí»: memoria confirmada y propuestas pendientes (#56). */
  CoachMemory: undefined;
};

/** Las cinco pestañas (#23). Coach es una pestaña, no una pantalla de la pila. */
export type MainTabParamList = {
  Hoy: undefined;
  Plan: undefined;
  /** `conversationId`: una conversación concreta o `new` (nueva, se crea al enviar el primer mensaje). */
  Coach: { conversationId?: string } | undefined;
  Rendimiento: undefined;
  Perfil: undefined;
};
