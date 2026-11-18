"""Schemas de las propuestas de umbral salidas de un test (#42)."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.metrics.tests import QualityWarningCode, ThresholdProtocol
from app.models.threshold_proposal import ProposalStatus

_PROPOSAL_EXAMPLE: dict[str, Any] = {
    "id": "3f6c1d2e-8a4b-4c7d-9e1f-2a3b4c5d6e7f",
    "activity_id": "7a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
    "protocol": "ftp_20min",
    "status": "pending",
    "test_date": "2026-11-15",
    "interval_start_at": "2026-11-15T08:15:00Z",
    "interval_end_at": "2026-11-15T08:35:00Z",
    "metrics": {
        "start_offset_s": 900,
        "end_offset_s": 2100,
        "duration_s": 1200,
        "avg_power_w": 242.3,
        "normalized_power_w": 245.1,
        "variability_index": 1.012,
        "avg_hr_bpm": 168.4,
        "max_hr_bpm": 179.0,
        "valid_data_pct": 100.0,
        "warmup_s": 900,
    },
    "proposed_ftp_w": 230,
    "warnings": [],
    "decided_at": None,
    "threshold_id": None,
    "created_at": "2026-11-15T10:00:00Z",
    "updated_at": "2026-11-15T10:00:00Z",
}


class ThresholdProposalCreate(BaseModel):
    """Analiza el test hecho en una actividad de ciclismo y crea una propuesta pendiente."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"activity_id": _PROPOSAL_EXAMPLE["activity_id"], "protocol": "ftp_20min"}]
        },
    )

    activity_id: UUID
    protocol: ThresholdProtocol = ThresholdProtocol.FTP_20MIN


class ProposalMetricsOut(BaseModel):
    """Métricas del bloque detectado. Offsets en segundos desde el primer registro del FIT.

    La FC (`avg_hr_bpm`, `max_hr_bpm`) es sólo informativa: con este test no se propone FC
    umbral. `variability_index` = potencia normalizada / potencia media del bloque.
    """

    start_offset_s: int
    end_offset_s: int
    duration_s: int
    avg_power_w: float
    normalized_power_w: float
    variability_index: float
    avg_hr_bpm: float | None
    max_hr_bpm: float | None
    valid_data_pct: float = Field(description="Porcentaje del bloque con dato de potencia.")
    warmup_s: int = Field(description="Segundos registrados antes del bloque.")


class QualityWarningOut(BaseModel):
    """Aviso de calidad del test. No impide aceptar la propuesta."""

    code: QualityWarningCode = Field(
        description=(
            "`data_gaps`: faltan datos dentro del bloque; `pauses`: tramos a 0 W dentro del"
            " bloque; `high_variability`: esfuerzo poco constante; `no_warmup`: sin"
            " calentamiento previo suficiente."
        )
    )
    message: str


class ThresholdProposalOut(BaseModel):
    """Propuesta de umbral salida de un test. Es sólo una propuesta hasta que se acepta.

    - `pending`: no cambia ningún umbral.
    - `accepted`: se creó un umbral nuevo (`threshold_id`) vigente desde `test_date`, con
      `source = test`, el FTP propuesto y el resto de valores copiados del umbral vigente ese
      día.
    - `rejected`: no se tocó nada.
    """

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"examples": [_PROPOSAL_EXAMPLE]}
    )

    id: UUID
    activity_id: UUID
    protocol: ThresholdProtocol
    status: ProposalStatus
    test_date: date = Field(
        description="Día local de la actividad: `effective_from` del umbral si se acepta."
    )
    interval_start_at: datetime
    interval_end_at: datetime
    metrics: ProposalMetricsOut
    proposed_ftp_w: int = Field(description="FTP propuesto: 95 % de la potencia media del bloque.")
    warnings: list[QualityWarningOut]
    decided_at: datetime | None
    threshold_id: UUID | None = Field(description="Umbral creado al aceptar la propuesta.")
    created_at: datetime
    updated_at: datetime
