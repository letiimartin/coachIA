"""Modelos SQLAlchemy del esquema v1. Importarlos aquí los registra en Base.metadata."""

from app.models.activity import Activity, ActivitySource, LoadMethod
from app.models.athlete import AthleteProfile, AthleteThreshold, AvailabilitySlot
from app.models.calendar import CalendarEvent, EventKind, Race, RacePriority, TrainingImpact
from app.models.coach import (
    CoachConversation,
    CoachLlmCall,
    CoachMemory,
    CoachMessage,
    ConversationKind,
    LlmCallPurpose,
    MemoryKind,
    MemorySource,
    MemoryStatus,
    MessageOrigin,
    MessageRole,
)
from app.models.common import Sport
from app.models.fitness import DailyLoad
from app.models.integration import Integration, IntegrationStatus, Provider
from app.models.plan import PlannedWorkout, PlannedWorkoutStatus
from app.models.strength import (
    Exercise,
    ExerciseMode,
    ExerciseOrigin,
    MuscleGroup,
    PlannedStrengthExercise,
    StrengthSetLog,
)
from app.models.threshold_proposal import ProposalStatus, ThresholdProposal

__all__ = [
    "Activity",
    "ActivitySource",
    "AthleteProfile",
    "AthleteThreshold",
    "AvailabilitySlot",
    "CalendarEvent",
    "CoachConversation",
    "CoachLlmCall",
    "CoachMemory",
    "CoachMessage",
    "ConversationKind",
    "DailyLoad",
    "EventKind",
    "Exercise",
    "ExerciseMode",
    "ExerciseOrigin",
    "Integration",
    "IntegrationStatus",
    "LlmCallPurpose",
    "LoadMethod",
    "MemoryKind",
    "MemorySource",
    "MemoryStatus",
    "MessageOrigin",
    "MessageRole",
    "MuscleGroup",
    "PlannedStrengthExercise",
    "PlannedWorkout",
    "PlannedWorkoutStatus",
    "ProposalStatus",
    "Provider",
    "Race",
    "RacePriority",
    "Sport",
    "StrengthSetLog",
    "ThresholdProposal",
    "TrainingImpact",
]
