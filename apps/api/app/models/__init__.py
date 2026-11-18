"""Modelos SQLAlchemy del esquema v1. Importarlos aquí los registra en Base.metadata."""

from app.models.activity import Activity, ActivitySource, LoadMethod
from app.models.athlete import AthleteProfile, AthleteThreshold, AvailabilitySlot
from app.models.calendar import CalendarEvent, EventKind, Race, RacePriority, TrainingImpact
from app.models.common import Sport
from app.models.fitness import DailyLoad
from app.models.integration import Integration, IntegrationStatus, Provider
from app.models.threshold_proposal import ProposalStatus, ThresholdProposal

__all__ = [
    "Activity",
    "ActivitySource",
    "AthleteProfile",
    "AthleteThreshold",
    "AvailabilitySlot",
    "CalendarEvent",
    "DailyLoad",
    "EventKind",
    "Integration",
    "IntegrationStatus",
    "LoadMethod",
    "ProposalStatus",
    "Provider",
    "Race",
    "RacePriority",
    "Sport",
    "ThresholdProposal",
    "TrainingImpact",
]
