"""Schemas de las propuestas de umbral salidas de un test (#42, #45)."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.metrics.tests import Comparison, QualityCriterion, ThresholdProtocol
from app.models.threshold_proposal import AcceptAction, PreviewWarningCode, ProposalStatus

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
    "warnings": [
        {
            "code": "no_warmup",
            "passed": False,
            "blocking": False,
            "measured": 300,
            "threshold": 600,
            "comparison": "ge",
            "unit": "s",
            "message": "El bloque empieza a los 5 min: no hay un calentamiento previo de al menos"
            " 10 min.",
        }
    ],
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


class QualityCheckOut(BaseModel):
    """Evaluación de un criterio de calidad del test.

    El criterio se cumple (`passed`) si `measured <comparison> threshold`. Si no se cumple y
    es `blocking`, no se puede proponer el umbral (error 422 con este mismo objeto en
    `error.details`); si no es `blocking`, sólo avisa.
    """

    model_config = ConfigDict(from_attributes=True)

    code: QualityCriterion = Field(
        description=(
            "Bloquean: `test_too_short` (duración de la actividad), `no_power_data` (potencia"
            " media del bloque), `insufficient_data` (% de datos válidos del bloque). Avisan:"
            " `data_gaps` (hueco sin potencia más largo del bloque), `pauses` (tramo a 0 W más"
            " largo del bloque), `high_variability` (NP / potencia media), `no_warmup`"
            " (segundos antes del bloque)."
        )
    )
    passed: bool
    blocking: bool = Field(description="Si no se cumple, impide la propuesta (si no, avisa).")
    measured: float = Field(description="Valor medido.")
    threshold: float = Field(description="Umbral del criterio.")
    comparison: Comparison = Field(
        description="Condición para cumplirlo: `measured` gt/ge/lt/le `threshold`."
    )
    unit: str = Field(description="`s`, `W`, `%` o vacío (adimensional).")
    message: str = Field(description="Explicación legible.")


class ThresholdProposalOut(BaseModel):
    """Propuesta de umbral salida de un test. Es sólo una propuesta hasta que se acepta.

    - `pending`: no cambia ningún umbral.
    - `accepted`: `threshold_id` es el umbral con el FTP del test. Si no había umbrales en
      `test_date`, una fila nueva con `source = test` y el resto de valores copiados del umbral
      vigente ese día; si ya había una fila en esa fecha, la misma fila con sólo `ftp_w`
      cambiado.
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
    warnings: list[QualityCheckOut] = Field(
        description="Criterios que no bloquean y no se cumplen (avisos)."
    )
    decided_at: datetime | None
    threshold_id: UUID | None = Field(
        description="Umbral creado o actualizado al aceptar la propuesta."
    )
    created_at: datetime
    updated_at: datetime


class ThresholdTestAnalysisOut(BaseModel):
    """Análisis de prueba (`dry-run`): lo que saldría del test, **sin crear ninguna propuesta**.

    `checks` tiene todos los criterios de calidad evaluados; `warnings`, los que avisan y no se
    cumplen (los mismos que tendría la propuesta).
    """

    activity_id: UUID
    protocol: ThresholdProtocol
    test_date: date = Field(description="Día local de la actividad.")
    interval_start_at: datetime
    interval_end_at: datetime
    metrics: ProposalMetricsOut
    proposed_ftp_w: int
    checks: list[QualityCheckOut]
    warnings: list[QualityCheckOut]


class NextThresholdOut(BaseModel):
    """Siguiente registro de umbrales después de `test_date`. No se toca al aceptar."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    effective_from: date
    ftp_w: int | None = Field(description="FTP que seguirá vigente desde `effective_from`.")


class PreviewWarningOut(BaseModel):
    code: PreviewWarningCode = Field(
        description=(
            "`later_thresholds`: hay umbrales registrados después de `test_date`; el FTP"
            " nuevo sólo rige hasta `effective_until`."
        )
    )
    message: str


class AcceptancePreviewOut(BaseModel):
    """Qué cambiaría al aceptar la propuesta. No guarda nada.

    - `create_row`: no hay umbrales en `test_date`; se crearía una fila con `source = test`,
      el FTP propuesto y el resto de valores copiados del umbral vigente ese día.
    - `update_ftp`: ya hay una fila en `test_date` (`threshold_id`); sólo cambiaría su
      `ftp_w`, el resto de valores se conservan.

    El FTP nuevo regiría desde `effective_from` (= `test_date`) hasta `effective_until`
    (el día anterior al siguiente registro, `next_threshold`), o sin fin si es null. Los
    registros posteriores no se tocan nunca.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "proposal_id": _PROPOSAL_EXAMPLE["id"],
                    "action": "update_ftp",
                    "threshold_id": "5d2c1b0a-9e8f-4a7b-8c6d-5e4f3a2b1c0d",
                    "previous_ftp_w": 220,
                    "proposed_ftp_w": 230,
                    "effective_from": "2026-11-15",
                    "effective_until": "2026-11-30",
                    "next_threshold": {
                        "id": "6e3d2c1b-0a9f-4b8c-9d7e-6f5a4b3c2d1e",
                        "effective_from": "2026-12-01",
                        "ftp_w": 235,
                    },
                    "warnings": [
                        {
                            "code": "later_thresholds",
                            "message": "Hay umbrales registrados desde el 2026-12-01: el FTP"
                            " nuevo sólo regirá hasta el 2026-11-30 y después seguirá"
                            " vigente el de ese registro (235 W).",
                        }
                    ],
                }
            ]
        }
    )

    proposal_id: UUID
    action: AcceptAction
    threshold_id: UUID | None = Field(description="Fila que se actualizaría (`update_ftp`).")
    previous_ftp_w: int | None = Field(
        description=(
            "FTP de `test_date` antes de aceptar: el de la fila de esa fecha (`update_ftp`) o"
            " el vigente ese día (`create_row`). Null si no había."
        )
    )
    proposed_ftp_w: int
    effective_from: date
    effective_until: date | None = Field(description="Último día de vigencia; null = sin fin.")
    next_threshold: NextThresholdOut | None
    warnings: list[PreviewWarningOut]


class ThresholdProposalAccept(BaseModel):
    """Confirma lo que mostró la vista previa. Si ya no coincide, 409 con la vista nueva."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"action": "update_ftp", "previous_ftp_w": 220}]},
    )

    action: AcceptAction
    previous_ftp_w: int | None = Field(
        description="`previous_ftp_w` de la vista previa (null si no había FTP)."
    )
