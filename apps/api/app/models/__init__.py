"""Modelos SQLAlchemy del esquema v1. Importarlos aquí los registra en Base.metadata."""

from app.models.activity import Activity, ActivitySource, LoadMethod
from app.models.athlete import AthleteProfile, AthleteThreshold, AvailabilitySlot
from app.models.calendar import CalendarEvent, EventKind, Race, RacePriority, TrainingImpact
from app.models.common import Sport
from app.models.integration import Integration, IntegrationStatus, Provider

__all__ = [
    "Activity",
    "ActivitySource",
    "AthleteProfile",
    "AthleteThreshold",
    "AvailabilitySlot",
    "CalendarEvent",
    "EventKind",
    "Integration",
    "IntegrationStatus",
    "LoadMethod",
    "Provider",
    "Race",
    "RacePriority",
    "Sport",
    "TrainingImpact",
]
