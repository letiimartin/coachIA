"""Herramientas del coach: definiciones, validación de la entrada y ejecución.

Las de lectura devuelven resúmenes compactos (nunca SQL libre ni JSON crudo) y siempre están
filtradas por la atleta: el LLM no puede pedir datos de nadie más porque ninguna herramienta
recibe un id de atleta. Hay dos de registro, acotadas:

- `propose_memory`: el coach **propone** objetivos y preferencias; sólo pasan a la memoria
  cuando la atleta los confirma en la app.
- `record_missed_workout_reason`: guarda el motivo que la atleta ha dado de un entreno no hecho,
  sin cambiar su estado ni el plan.

Los datos los da un `CoachData`: el de la BD (`app.coach.data`) o uno simulado (evaluación).
"""

import json
import uuid
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.coach.llm.base import ToolCall, ToolResult, ToolSpec
from app.core.errors import AppError
from app.models.coach import MemoryKind

# --- Entradas --------------------------------------------------------------------------------


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoInput(_Input):
    pass


class FitnessInput(_Input):
    days: int = Field(default=14, ge=1, le=90, description="Días hacia atrás desde hoy.")


class ActivitiesInput(_Input):
    days: int = Field(default=14, ge=1, le=60, description="Días hacia atrás desde hoy.")


class CalendarInput(_Input):
    days_ahead: int = Field(default=60, ge=1, le=240, description="Días hacia delante.")


class PlannedWorkoutsInput(_Input):
    days_back: int = Field(default=7, ge=0, le=28, description="Días hacia atrás desde hoy.")
    days_ahead: int = Field(default=14, ge=0, le=42, description="Días hacia delante.")


class MemoryProposal(_Input):
    kind: MemoryKind = Field(description="goal (objetivo), preference (preferencia) u other.")
    content: str = Field(
        min_length=1, max_length=500, description="Frase breve, en segunda persona."
    )


class ProposeMemoryInput(_Input):
    items: list[MemoryProposal] = Field(min_length=1, max_length=10)


class MissedReasonInput(_Input):
    workout_id: uuid.UUID = Field(description="Id del entreno planificado.")
    reason: str = Field(
        min_length=1, max_length=1000, description="El motivo, con las palabras de la atleta."
    )


# --- Datos -----------------------------------------------------------------------------------


class CoachData(Protocol):
    """Fuente de datos de las herramientas, ya acotada a una atleta."""

    def profile(self) -> dict[str, Any]: ...
    def fitness(self, days: int) -> dict[str, Any]: ...
    def recent_activities(self, days: int) -> dict[str, Any]: ...
    def calendar(self, days_ahead: int) -> dict[str, Any]: ...
    def planned_workouts(self, days_back: int, days_ahead: int) -> dict[str, Any]: ...
    def availability(self) -> dict[str, Any]: ...
    def memory(self) -> dict[str, Any]: ...
    def propose_memory(self, items: list[MemoryProposal]) -> dict[str, Any]: ...
    def record_missed_reason(self, workout_id: uuid.UUID, reason: str) -> dict[str, Any]: ...


# --- Definiciones ----------------------------------------------------------------------------


class _Tool:
    def __init__(self, name: str, description: str, model: type[_Input], *, writes: bool):
        self.name = name
        self.description = description
        self.model = model
        self.writes = writes

    def spec(self) -> ToolSpec:
        schema = self.model.model_json_schema()
        schema.pop("title", None)
        schema.setdefault("properties", {})
        return ToolSpec(self.name, self.description, schema)


_TOOLS = (
    _Tool(
        "get_athlete_profile",
        "Perfil de la atleta (edad, deportes, zona horaria), umbrales vigentes (FTP, LTHR por "
        "disciplina, FC máx./reposo, ritmo umbral, peso) y zonas calculadas.",
        NoInput,
        writes=False,
    ),
    _Tool(
        "get_fitness",
        "Forma: CTL (forma física), ATL (fatiga) y TSB (frescura) de hoy, su tendencia y la "
        "carga diaria de los últimos días. Valores calculados por el sistema.",
        FitnessInput,
        writes=False,
    ),
    _Tool(
        "get_recent_activities",
        "Actividades hechas en los últimos días: fecha, deporte, duración, distancia, desnivel, "
        "carga, RPE y medias de FC y potencia.",
        ActivitiesInput,
        writes=False,
    ),
    _Tool(
        "get_calendar",
        "Calendario de los próximos días (carreras, viajes, salud, eventos, no disponibilidad, "
        "con su impacto en el entrenamiento) y la próxima carrera objetivo.",
        CalendarInput,
        writes=False,
    ),
    _Tool(
        "get_planned_workouts",
        "Entrenos planificados alrededor de hoy, con su estado (planned, done, skipped), "
        "duración, el motivo si no se hizo y, en los de fuerza, los ejercicios y el último "
        "registro de cada uno.",
        PlannedWorkoutsInput,
        writes=False,
    ),
    _Tool(
        "get_availability",
        "Disponibilidad habitual de cada día de la semana: minutos, deportes, franja preferida y "
        "si prefiere descansar.",
        NoInput,
        writes=False,
    ),
    _Tool(
        "get_memory",
        "Objetivos y preferencias que la atleta ha confirmado, con su fecha.",
        NoInput,
        writes=False,
    ),
    _Tool(
        "propose_memory",
        "Propone objetivos y preferencias para recordar, tras resumirlos en tu mensaje. No se "
        "guardan: la atleta los revisa y confirma en la app. Cada llamada sustituye a las "
        "propuestas pendientes de esta conversación.",
        ProposeMemoryInput,
        writes=True,
    ),
    _Tool(
        "record_missed_workout_reason",
        "Guarda el motivo por el que la atleta no hizo un entreno planificado de hoy o de días "
        "anteriores, cuando ella lo ha explicado. No cambia el plan ni el estado del entreno.",
        MissedReasonInput,
        writes=True,
    ),
)
_BY_NAME = {tool.name: tool for tool in _TOOLS}

TOOL_SPECS: tuple[ToolSpec, ...] = tuple(tool.spec() for tool in _TOOLS)
TOOL_NAMES: tuple[str, ...] = tuple(tool.name for tool in _TOOLS)


def dumps(value: Any) -> str:
    """JSON compacto y determinista (mismo resultado → mismos tokens)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)


def _dispatch(data: CoachData, name: str, args: _Input) -> dict[str, Any]:
    match args:
        case FitnessInput(days=days):
            return data.fitness(days)
        case ActivitiesInput(days=days):
            return data.recent_activities(days)
        case CalendarInput(days_ahead=days_ahead):
            return data.calendar(days_ahead)
        case PlannedWorkoutsInput(days_back=back, days_ahead=ahead):
            return data.planned_workouts(back, ahead)
        case ProposeMemoryInput(items=items):
            return data.propose_memory(items)
        case MissedReasonInput(workout_id=workout_id, reason=reason):
            return data.record_missed_reason(workout_id, reason.strip())
    if name == "get_athlete_profile":
        return data.profile()
    if name == "get_availability":
        return data.availability()
    return data.memory()


def execute(data: CoachData, call: ToolCall) -> ToolResult:
    """Ejecuta una llamada. Los errores de entrada o de negocio vuelven al LLM como error."""
    tool = _BY_NAME.get(call.name)
    if tool is None:
        return ToolResult(call.id, dumps({"error": f"Herramienta desconocida: {call.name}"}), True)
    try:
        args = tool.model.model_validate(call.input)
    except ValidationError as exc:
        errors = [
            {"loc": list(err["loc"]), "msg": err["msg"]}
            for err in exc.errors(include_url=False, include_input=False)
        ]
        return ToolResult(call.id, dumps({"error": "Entrada no válida", "details": errors}), True)
    try:
        result = _dispatch(data, call.name, args)
    except AppError as exc:
        return ToolResult(call.id, dumps({"error": exc.message}), True)
    return ToolResult(call.id, dumps(result))
