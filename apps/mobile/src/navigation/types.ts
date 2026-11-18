import type { CalendarEventOut, ThresholdOut } from '../api/types';

/** Pantallas del stack principal que reciben parámetros (las de pestañas no los usan). */
export type RootStackParamList = {
  MainTabs: undefined;
  Thresholds: undefined;
  ThresholdForm: { current: ThresholdOut | null };
  Availability: undefined;
  EventForm: { event?: CalendarEventOut };
  CoachChat: undefined;
  /** Vuelta del OAuth de Wahoo: la API redirige a `…/integrations?provider=wahoo&status=…&reason=…`. */
  Integrations: { provider?: string; status?: string; reason?: string } | undefined;
};
