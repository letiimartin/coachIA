// Alias de los schemas del contrato (generados en schema.d.ts a partir de apps/api/openapi.json).
import type { components } from './schema';

type S = components['schemas'];

export type ProfileOut = S['ProfileOut'];
export type ProfilePatch = S['ProfilePatch'];
export type Sex = S['Sex'];
export type Sport = S['Sport'];

export type ThresholdOut = S['ThresholdOut'];
export type ThresholdCreate = S['ThresholdCreate'];
export type ThresholdSource = S['ThresholdSource'];
export type CurrentThresholdOut = S['CurrentThresholdOut'];
export type ZonesOut = S['ZonesOut'];
export type ZoneOut = S['ZoneOut'];

export type WeekAvailability = S['WeekAvailability'];
export type AvailabilityDay = S['AvailabilityDay'];
export type PreferredTime = S['PreferredTime'];

export type CalendarEventOut = S['CalendarEventOut'];
export type CalendarEventCreate = S['CalendarEventCreate'];
export type CalendarEventPatch = S['CalendarEventPatch'];
export type EventKind = S['EventKind'];
export type TrainingImpact = S['TrainingImpact'];
export type RaceOut = S['RaceOut'];
export type RaceCreate = S['RaceCreate'];
export type RacePatch = S['RacePatch'];
export type RaceDiscipline = S['RaceDiscipline'];
export type RacePriority = S['RacePriority'];
export type EnrichmentStatus = S['EnrichmentStatus'];

export type ErrorResponse = S['ErrorResponse'];

export type IntegrationOut = S['IntegrationOut'];
export type Provider = S['Provider'];
export type SyncOut = S['SyncOut'];

// Fuerza (contrato de #30).
export type PlannedWorkoutOut = S['PlannedWorkoutOut'];
export type PlannedWorkoutStatus = S['PlannedWorkoutStatus'];
export type ExerciseOut = S['ExerciseOut'];
export type ExerciseMode = S['ExerciseMode'];
export type MuscleGroup = S['MuscleGroup'];
export type ExerciseLastLogOut = S['ExerciseLastLogOut'];
export type LastSetOut = S['LastSetOut'];
export type PlannedStrengthExerciseOut = S['PlannedStrengthExerciseOut'];
export type StrengthWorkoutOut = S['StrengthWorkoutOut'];
export type StrengthSetIn = S['StrengthSetIn'];
export type StrengthSetLogOut = S['StrengthSetLogOut'];
export type StrengthSetsPut = S['StrengthSetsPut'];
export type StrengthWorkoutComplete = S['StrengthWorkoutComplete'];
export type StrengthActivityOut = S['StrengthActivityOut'];

// Rendimiento de fuerza (#33).
export type StrengthWeeklyOut = S['StrengthWeeklyOut'];
export type StrengthWeekOut = S['StrengthWeekOut'];
export type PerformedExerciseOut = S['PerformedExerciseOut'];
export type ExerciseProgressOut = S['ExerciseProgressOut'];
export type ExerciseSessionOut = S['ExerciseSessionOut'];
