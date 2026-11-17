import type { CalendarEventOut, ThresholdOut } from '../api/types';

/** Pantallas del stack principal que reciben parámetros (las de pestañas no los usan). */
export type RootStackParamList = {
  MainTabs: undefined;
  Thresholds: undefined;
  ThresholdForm: { current: ThresholdOut | null };
  Availability: undefined;
  EventForm: { event?: CalendarEventOut };
  WorkoutDetail: { id: string };
  CoachChat: undefined;
  WahooCallback: undefined;
};
