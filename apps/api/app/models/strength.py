"""Fuerza (#30): catálogo de ejercicios, ejercicios de una sesión planificada y series hechas.

- `exercises`: catálogo con un identificador estable por ejercicio, de modo que «el peso de la
  última sentadilla» es una consulta relacional y no depende del texto que escriba el LLM. Los
  del sistema (`origin = system`) son comunes y no tienen dueño; los que creen el coach o la
  atleta (`coach`, `user`) cuelgan de su `athlete_profiles`.
- `planned_strength_exercises`: los ejercicios de un `planned_workouts` de fuerza, en orden.
- `strength_set_logs`: cada serie hecha. Mientras la sesión está en curso cuelga del entreno
  planificado; al completarla se le asigna la `activity` creada. Una actividad de fuerza sin
  plan (p. ej. sincronizada) también podrá tener series, sólo con `activity_id`.
"""

import enum
import uuid
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin, str_enum, user_fk, uuid_pk


class MuscleGroup(enum.StrEnum):
    """Grupo muscular principal del ejercicio."""

    QUADRICEPS = "quadriceps"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    HIPS = "hips"  # Aductores y abductores.
    CALVES = "calves"
    CORE = "core"
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    FULL_BODY = "full_body"


class ExerciseMode(enum.StrEnum):
    """Cómo se mide cada serie: repeticiones o segundos (isométricos, cargadas…)."""

    REPS = "reps"
    SECONDS = "seconds"


class ExerciseOrigin(enum.StrEnum):
    SYSTEM = "system"
    COACH = "coach"
    USER = "user"


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Identificador legible y estable (`back_squat`). Único en el catálogo del sistema y entre
    # los ejercicios de cada atleta.
    slug: Mapped[str] = mapped_column(sa.String(64))
    name: Mapped[str] = mapped_column(sa.String(120))
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String(120)), server_default=sa.text("'{}'::varchar[]")
    )
    muscle_group: Mapped[MuscleGroup] = mapped_column(str_enum(MuscleGroup, "muscle_group"))
    mode: Mapped[ExerciseMode] = mapped_column(str_enum(ExerciseMode, "exercise_mode"))
    origin: Mapped[ExerciseOrigin] = mapped_column(str_enum(ExerciseOrigin, "exercise_origin"))
    # Dueño de los ejercicios `coach` y `user`; null en los del sistema.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("athlete_profiles.user_id", ondelete="CASCADE"),
        index=True,
    )
    # Nombre y alias normalizados (`app.core.text.search_text`), para buscar sin distinguir
    # mayúsculas ni acentos. Lo escribe siempre la aplicación (o la migración del catálogo).
    search_text: Mapped[str] = mapped_column(sa.Text)

    __table_args__ = (
        sa.CheckConstraint("(origin = 'system') = (user_id IS NULL)", name="owner"),
        sa.CheckConstraint("slug ~ '^[a-z0-9_]+$'", name="slug"),
        sa.Index(
            "uq_exercises_system_slug",
            "slug",
            unique=True,
            postgresql_where=sa.text("user_id IS NULL"),
        ),
        sa.Index(
            "uq_exercises_user_slug",
            "user_id",
            "slug",
            unique=True,
            postgresql_where=sa.text("user_id IS NOT NULL"),
        ),
    )


class PlannedStrengthExercise(TimestampMixin, Base):
    """Un ejercicio de una sesión de fuerza planificada: series y repeticiones o segundos.

    Peso, RPE y RIR objetivo son opcionales. Exactamente uno de `target_reps` y
    `target_seconds`, según el `mode` del ejercicio (lo comprueba el servicio).
    """

    __tablename__ = "planned_strength_exercises"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    planned_workout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("planned_workouts.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(sa.SmallInteger)
    # NO ACTION: un ejercicio usado no se puede borrar del catálogo.
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("exercises.id"), index=True
    )
    sets: Mapped[int] = mapped_column(sa.SmallInteger)
    target_reps: Mapped[int | None] = mapped_column(sa.SmallInteger)
    target_seconds: Mapped[int | None] = mapped_column(sa.SmallInteger)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    target_rpe: Mapped[int | None] = mapped_column(sa.SmallInteger)
    target_rir: Mapped[int | None] = mapped_column(sa.SmallInteger)
    notes: Mapped[str | None] = mapped_column(sa.Text)

    __table_args__ = (
        sa.UniqueConstraint("planned_workout_id", "position"),
        sa.CheckConstraint("position >= 1", name="position"),
        sa.CheckConstraint("sets BETWEEN 1 AND 20", name="sets"),
        sa.CheckConstraint("(target_reps IS NULL) <> (target_seconds IS NULL)", name="target"),
        sa.CheckConstraint(
            "target_reps IS NULL OR target_reps BETWEEN 1 AND 1000", name="target_reps"
        ),
        sa.CheckConstraint(
            "target_seconds IS NULL OR target_seconds BETWEEN 1 AND 3600", name="target_seconds"
        ),
        sa.CheckConstraint(
            "target_weight_kg IS NULL OR target_weight_kg >= 0", name="target_weight"
        ),
        sa.CheckConstraint("target_rpe IS NULL OR target_rpe BETWEEN 1 AND 10", name="target_rpe"),
        sa.CheckConstraint("target_rir IS NULL OR target_rir BETWEEN 0 AND 10", name="target_rir"),
    )


class StrengthSetLog(TimestampMixin, Base):
    """Una serie hecha: repeticiones o segundos, peso (opcional), RPE y RIR (opcionales)."""

    __tablename__ = "strength_set_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = user_fk()
    # Actividad de la sesión; null mientras la sesión planificada no se ha completado.
    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("activities.id", ondelete="CASCADE"), index=True
    )
    # Sesión planificada a la que pertenece la serie, si la hay.
    planned_workout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("planned_workouts.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("exercises.id"), index=True
    )
    # Ejercicio planificado que cumple la serie, si lo hay. SET NULL: la serie sigue siendo
    # historial aunque cambie el plan.
    planned_exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("planned_strength_exercises.id", ondelete="SET NULL"),
    )
    set_number: Mapped[int] = mapped_column(sa.SmallInteger)
    reps: Mapped[int | None] = mapped_column(sa.SmallInteger)
    seconds: Mapped[int | None] = mapped_column(sa.SmallInteger)
    weight_kg: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    rpe: Mapped[int | None] = mapped_column(sa.SmallInteger)
    rir: Mapped[int | None] = mapped_column(sa.SmallInteger)
    completed: Mapped[bool] = mapped_column(server_default=sa.true())

    __table_args__ = (
        sa.CheckConstraint(
            "activity_id IS NOT NULL OR planned_workout_id IS NOT NULL", name="session"
        ),
        sa.CheckConstraint("set_number BETWEEN 1 AND 50", name="set_number"),
        sa.CheckConstraint("(reps IS NULL) <> (seconds IS NULL)", name="amount"),
        sa.CheckConstraint("reps IS NULL OR reps BETWEEN 0 AND 1000", name="reps"),
        sa.CheckConstraint("seconds IS NULL OR seconds BETWEEN 0 AND 3600", name="seconds"),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg >= 0", name="weight"),
        sa.CheckConstraint("rpe IS NULL OR rpe BETWEEN 1 AND 10", name="rpe"),
        sa.CheckConstraint("rir IS NULL OR rir BETWEEN 0 AND 10", name="rir"),
    )
