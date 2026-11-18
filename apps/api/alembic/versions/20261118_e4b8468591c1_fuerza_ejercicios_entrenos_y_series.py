"""Fuerza 1 (#30): catálogo de ejercicios, entrenos planificados y registro de series.

Añade cuatro tablas y el catálogo inicial de ejercicios del sistema (aprobado en #30):

- `exercises`: catálogo (`origin` system/coach/user). Los del sistema no tienen dueño
  (`user_id` null); los del coach y la atleta cuelgan de `athlete_profiles`.
- `planned_workouts`: entreno planificado genérico (disciplina, fecha, título, estado, motivo
  del coach y actividad que lo cumplió).
- `planned_strength_exercises`: ejercicios de una sesión de fuerza planificada.
- `strength_set_logs`: series hechas, ligadas a la sesión planificada y, al completarla, a la
  `activity`.

Como el resto de tablas: RLS activado y sin políticas, y sin privilegios para los roles del
Data API de Supabase (anon, authenticated), si existen. No toca ninguna tabla existente.

El catálogo es dato de la migración: está congelado aquí (con su propia normalización del
texto de búsqueda, idéntica a `app.core.text.search_text`; un test lo comprueba). Los cambios
posteriores del catálogo van en migraciones nuevas. El downgrade borra las tablas y el catálogo.

Revision ID: e4b8468591c1
Revises: 73d50e89ab8e
Create Date: 2026-11-18 22:40:51.583497+00:00
"""

import re
import unicodedata
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e4b8468591c1"
down_revision: str | None = "73d50e89ab8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATA_API_ROLES = ("anon", "authenticated")
NEW_TABLES = ("exercises", "planned_workouts", "planned_strength_exercises", "strength_set_logs")

# Catálogo inicial: (slug, nombre, alias, grupo muscular principal, modo).
CATALOG: tuple[tuple[str, str, tuple[str, ...], str, str], ...] = (
    # Rodilla dominante
    (
        "back_squat",
        "Sentadilla trasera",
        ("Sentadilla con barra", "Back squat"),
        "quadriceps",
        "reps",
    ),
    ("front_squat", "Sentadilla frontal", ("Front squat",), "quadriceps", "reps"),
    (
        "goblet_squat",
        "Sentadilla goblet",
        ("Sentadilla copa", "Goblet squat"),
        "quadriceps",
        "reps",
    ),
    (
        "bodyweight_squat",
        "Sentadilla sin carga",
        ("Sentadilla libre", "Air squat"),
        "quadriceps",
        "reps",
    ),
    (
        "bulgarian_split_squat",
        "Sentadilla búlgara",
        ("Bulgarian split squat",),
        "quadriceps",
        "reps",
    ),
    (
        "split_squat",
        "Sentadilla dividida",
        ("Zancada estática", "Split squat"),
        "quadriceps",
        "reps",
    ),
    (
        "box_single_leg_squat",
        "Sentadilla a una pierna al cajón",
        ("Box pistol squat",),
        "quadriceps",
        "reps",
    ),
    ("forward_lunge", "Zancada adelante", ("Zancada", "Lunge"), "quadriceps", "reps"),
    ("reverse_lunge", "Zancada atrás", ("Zancada inversa", "Reverse lunge"), "glutes", "reps"),
    ("walking_lunge", "Zancadas caminando", ("Walking lunges",), "quadriceps", "reps"),
    ("lateral_lunge", "Zancada lateral", ("Lateral lunge",), "hips", "reps"),
    ("step_up", "Step-up", ("Subida al cajón", "Subida al banco"), "quadriceps", "reps"),
    ("leg_press", "Prensa de piernas", ("Prensa", "Leg press"), "quadriceps", "reps"),
    ("leg_extension", "Extensión de cuádriceps", ("Leg extension",), "quadriceps", "reps"),
    (
        "wall_sit",
        "Sentadilla isométrica en pared",
        ("Wall sit", "Silla en pared"),
        "quadriceps",
        "seconds",
    ),
    # Cadera dominante
    ("deadlift", "Peso muerto", ("Peso muerto convencional", "Deadlift"), "glutes", "reps"),
    ("romanian_deadlift", "Peso muerto rumano", ("RDL", "Romanian deadlift"), "hamstrings", "reps"),
    (
        "single_leg_romanian_deadlift",
        "Peso muerto rumano a una pierna",
        ("Single leg RDL",),
        "hamstrings",
        "reps",
    ),
    ("good_morning", "Buenos días", ("Good morning",), "hamstrings", "reps"),
    ("hip_thrust", "Hip thrust", ("Empuje de cadera",), "glutes", "reps"),
    ("glute_bridge", "Puente de glúteo", ("Puente", "Glute bridge"), "glutes", "reps"),
    (
        "single_leg_glute_bridge",
        "Puente de glúteo a una pierna",
        ("Puente a una pierna", "Single leg glute bridge"),
        "glutes",
        "reps",
    ),
    (
        "kettlebell_swing",
        "Swing con kettlebell",
        ("Swing ruso", "Kettlebell swing"),
        "glutes",
        "reps",
    ),
    ("nordic_curl", "Curl nórdico", ("Nordic hamstring curl", "Nórdicos"), "hamstrings", "reps"),
    ("leg_curl", "Curl femoral", ("Curl de isquios", "Leg curl"), "hamstrings", "reps"),
    # Gemelo y sóleo
    (
        "standing_calf_raise",
        "Elevación de gemelos de pie",
        ("Gemelo de pie", "Calf raise"),
        "calves",
        "reps",
    ),
    (
        "single_leg_calf_raise",
        "Elevación de gemelo a una pierna",
        ("Gemelo a una pierna", "Single leg calf raise"),
        "calves",
        "reps",
    ),
    (
        "seated_calf_raise",
        "Elevación de gemelos sentado",
        ("Sóleo sentado", "Seated calf raise"),
        "calves",
        "reps",
    ),
    # Aductores y abductores
    (
        "copenhagen_plank",
        "Plancha Copenhague",
        ("Copenhagen plank", "Aductor Copenhague"),
        "hips",
        "seconds",
    ),
    (
        "lateral_band_walk",
        "Paso lateral con banda",
        ("Monster walk", "Lateral band walk"),
        "hips",
        "reps",
    ),
    ("clamshell", "Almeja", ("Clamshell",), "hips", "reps"),
    # Empuje
    ("push_up", "Flexiones", ("Push-up", "Lagartijas"), "chest", "reps"),
    ("bench_press", "Press de banca", ("Press banca", "Bench press"), "chest", "reps"),
    (
        "dumbbell_bench_press",
        "Press de banca con mancuernas",
        ("Dumbbell bench press",),
        "chest",
        "reps",
    ),
    ("dips", "Fondos", ("Fondos en paralelas", "Dips"), "chest", "reps"),
    (
        "overhead_press",
        "Press militar",
        ("Press de hombros con barra", "Overhead press"),
        "shoulders",
        "reps",
    ),
    (
        "dumbbell_shoulder_press",
        "Press de hombros con mancuernas",
        ("Dumbbell shoulder press",),
        "shoulders",
        "reps",
    ),
    # Tirón
    ("pull_up", "Dominadas", ("Pull-up", "Chin-up"), "back", "reps"),
    ("lat_pulldown", "Jalón al pecho", ("Lat pulldown",), "back", "reps"),
    ("barbell_row", "Remo con barra", ("Remo inclinado", "Bent-over row"), "back", "reps"),
    ("dumbbell_row", "Remo con mancuerna", ("Remo a una mano", "Dumbbell row"), "back", "reps"),
    ("inverted_row", "Remo invertido", ("Remo australiano", "Inverted row"), "back", "reps"),
    ("face_pull", "Face pull", ("Tirón a la cara",), "shoulders", "reps"),
    ("biceps_curl", "Curl de bíceps", ("Biceps curl",), "arms", "reps"),
    # Core
    ("plank", "Plancha", ("Plancha frontal", "Plank"), "core", "seconds"),
    ("side_plank", "Plancha lateral", ("Side plank",), "core", "seconds"),
    ("dead_bug", "Dead bug", ("Bicho muerto",), "core", "reps"),
    ("bird_dog", "Bird dog", ("Perro de caza",), "core", "reps"),
    ("pallof_press", "Press Pallof", ("Antirrotación con banda", "Pallof press"), "core", "reps"),
    ("hollow_hold", "Hollow hold", ("Posición hueca",), "core", "seconds"),
    (
        "hanging_knee_raise",
        "Elevación de rodillas colgado",
        ("Hanging knee raise",),
        "core",
        "reps",
    ),
    (
        "farmers_carry",
        "Paseo del granjero",
        ("Farmer's walk", "Farmer carry"),
        "full_body",
        "seconds",
    ),
    # Pliometría
    ("box_jump", "Salto al cajón", ("Box jump",), "quadriceps", "reps"),
    ("squat_jump", "Sentadilla con salto", ("Jump squat",), "quadriceps", "reps"),
    ("jump_lunge", "Zancadas con salto", ("Split jump", "Jumping lunges"), "quadriceps", "reps"),
    ("pogo_jumps", "Saltos pogo", ("Pogos", "Saltos de tobillo"), "calves", "reps"),
    ("skater_jump", "Saltos de patinador", ("Skater jumps",), "glutes", "reps"),
    ("bounding", "Multisaltos", ("Bounding", "Zancadas saltadas"), "full_body", "reps"),
    ("burpee", "Burpee", ("Burpees",), "full_body", "reps"),
)

_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _search_key(text: str) -> str:
    """Copia congelada de `app.core.text.search_key`."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NON_ALNUM.sub(" ", stripped).strip()


def _search_text(name: str, aliases: tuple[str, ...]) -> str:
    """Copia congelada de `app.core.text.search_text`."""
    keys = [_search_key(name), *(_search_key(alias) for alias in aliases)]
    return "|".join(key for key in keys if key)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "exercises",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.String(length=120)),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column(
            "muscle_group",
            sa.Enum(
                "quadriceps",
                "hamstrings",
                "glutes",
                "hips",
                "calves",
                "core",
                "chest",
                "back",
                "shoulders",
                "arms",
                "full_body",
                name="muscle_group",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "mode",
            sa.Enum(
                "reps",
                "seconds",
                name="exercise_mode",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "origin",
            sa.Enum(
                "system",
                "coach",
                "user",
                name="exercise_origin",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(origin = 'system') = (user_id IS NULL)", name=op.f("ck_exercises_owner")
        ),
        sa.CheckConstraint("slug ~ '^[a-z0-9_]+$'", name=op.f("ck_exercises_slug")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["athlete_profiles.user_id"],
            name=op.f("fk_exercises_user_id_athlete_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercises")),
    )
    op.create_index(op.f("ix_exercises_user_id"), "exercises", ["user_id"], unique=False)
    op.create_index(
        "uq_exercises_system_slug",
        "exercises",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_exercises_user_slug",
        "exercises",
        ["user_id", "slug"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_table(
        "planned_workouts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "sport",
            sa.Enum(
                "cycling",
                "running",
                "trail_running",
                "hiking",
                "strength",
                "swimming",
                "other",
                name="sport",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("scheduled_on", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "planned",
                "done",
                "skipped",
                name="planned_workout_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="planned",
            nullable=False,
        ),
        sa.Column("coach_reason", sa.Text(), nullable=True),
        sa.Column("activity_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "activity_id IS NULL OR status = 'done'", name=op.f("ck_planned_workouts_activity_done")
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_planned_workouts_activity_id_activities"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["athlete_profiles.user_id"],
            name=op.f("fk_planned_workouts_user_id_athlete_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_planned_workouts")),
        sa.UniqueConstraint("activity_id", name=op.f("uq_planned_workouts_activity_id")),
    )
    op.create_index(
        op.f("ix_planned_workouts_user_id"), "planned_workouts", ["user_id"], unique=False
    )
    op.create_index(
        "ix_planned_workouts_user_id_scheduled_on",
        "planned_workouts",
        ["user_id", "scheduled_on"],
        unique=False,
    )
    op.create_table(
        "planned_strength_exercises",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("planned_workout_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("sets", sa.SmallInteger(), nullable=False),
        sa.Column("target_reps", sa.SmallInteger(), nullable=True),
        sa.Column("target_seconds", sa.SmallInteger(), nullable=True),
        sa.Column("target_weight_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("target_rpe", sa.SmallInteger(), nullable=True),
        sa.Column("target_rir", sa.SmallInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(target_reps IS NULL) <> (target_seconds IS NULL)",
            name=op.f("ck_planned_strength_exercises_target"),
        ),
        sa.CheckConstraint("position >= 1", name=op.f("ck_planned_strength_exercises_position")),
        sa.CheckConstraint(
            "sets BETWEEN 1 AND 20", name=op.f("ck_planned_strength_exercises_sets")
        ),
        sa.CheckConstraint(
            "target_reps IS NULL OR target_reps BETWEEN 1 AND 1000",
            name=op.f("ck_planned_strength_exercises_target_reps"),
        ),
        sa.CheckConstraint(
            "target_rir IS NULL OR target_rir BETWEEN 0 AND 10",
            name=op.f("ck_planned_strength_exercises_target_rir"),
        ),
        sa.CheckConstraint(
            "target_rpe IS NULL OR target_rpe BETWEEN 1 AND 10",
            name=op.f("ck_planned_strength_exercises_target_rpe"),
        ),
        sa.CheckConstraint(
            "target_seconds IS NULL OR target_seconds BETWEEN 1 AND 3600",
            name=op.f("ck_planned_strength_exercises_target_seconds"),
        ),
        sa.CheckConstraint(
            "target_weight_kg IS NULL OR target_weight_kg >= 0",
            name=op.f("ck_planned_strength_exercises_target_weight"),
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_planned_strength_exercises_exercise_id_exercises"),
        ),
        sa.ForeignKeyConstraint(
            ["planned_workout_id"],
            ["planned_workouts.id"],
            name=op.f("fk_planned_strength_exercises_planned_workout_id_planned_workouts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["athlete_profiles.user_id"],
            name=op.f("fk_planned_strength_exercises_user_id_athlete_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_planned_strength_exercises")),
        sa.UniqueConstraint(
            "planned_workout_id",
            "position",
            name=op.f("uq_planned_strength_exercises_planned_workout_id_position"),
        ),
    )
    op.create_index(
        op.f("ix_planned_strength_exercises_exercise_id"),
        "planned_strength_exercises",
        ["exercise_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_planned_strength_exercises_user_id"),
        "planned_strength_exercises",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "strength_set_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("activity_id", sa.UUID(), nullable=True),
        sa.Column("planned_workout_id", sa.UUID(), nullable=True),
        sa.Column("exercise_id", sa.UUID(), nullable=False),
        sa.Column("planned_exercise_id", sa.UUID(), nullable=True),
        sa.Column("set_number", sa.SmallInteger(), nullable=False),
        sa.Column("reps", sa.SmallInteger(), nullable=True),
        sa.Column("seconds", sa.SmallInteger(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("rpe", sa.SmallInteger(), nullable=True),
        sa.Column("rir", sa.SmallInteger(), nullable=True),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(reps IS NULL) <> (seconds IS NULL)", name=op.f("ck_strength_set_logs_amount")
        ),
        sa.CheckConstraint(
            "activity_id IS NOT NULL OR planned_workout_id IS NOT NULL",
            name=op.f("ck_strength_set_logs_session"),
        ),
        sa.CheckConstraint(
            "reps IS NULL OR reps BETWEEN 0 AND 1000", name=op.f("ck_strength_set_logs_reps")
        ),
        sa.CheckConstraint(
            "rir IS NULL OR rir BETWEEN 0 AND 10", name=op.f("ck_strength_set_logs_rir")
        ),
        sa.CheckConstraint(
            "rpe IS NULL OR rpe BETWEEN 1 AND 10", name=op.f("ck_strength_set_logs_rpe")
        ),
        sa.CheckConstraint(
            "seconds IS NULL OR seconds BETWEEN 0 AND 3600",
            name=op.f("ck_strength_set_logs_seconds"),
        ),
        sa.CheckConstraint(
            "set_number BETWEEN 1 AND 50", name=op.f("ck_strength_set_logs_set_number")
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0", name=op.f("ck_strength_set_logs_weight")
        ),
        sa.ForeignKeyConstraint(
            ["activity_id"],
            ["activities.id"],
            name=op.f("fk_strength_set_logs_activity_id_activities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_strength_set_logs_exercise_id_exercises"),
        ),
        sa.ForeignKeyConstraint(
            ["planned_exercise_id"],
            ["planned_strength_exercises.id"],
            name=op.f("fk_strength_set_logs_planned_exercise_id_planned_strength_exercises"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["planned_workout_id"],
            ["planned_workouts.id"],
            name=op.f("fk_strength_set_logs_planned_workout_id_planned_workouts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["athlete_profiles.user_id"],
            name=op.f("fk_strength_set_logs_user_id_athlete_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strength_set_logs")),
    )
    op.create_index(
        op.f("ix_strength_set_logs_activity_id"), "strength_set_logs", ["activity_id"], unique=False
    )
    op.create_index(
        op.f("ix_strength_set_logs_exercise_id"), "strength_set_logs", ["exercise_id"], unique=False
    )
    op.create_index(
        op.f("ix_strength_set_logs_planned_workout_id"),
        "strength_set_logs",
        ["planned_workout_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_strength_set_logs_user_id"), "strength_set_logs", ["user_id"], unique=False
    )
    # ### end Alembic commands ###
    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        # Los nombres de tabla y de rol son constantes del módulo, no entrada de usuario.
        for role in DATA_API_ROLES:
            op.execute(
                f"""
                DO $$
                BEGIN
                  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    REVOKE ALL ON TABLE public.{table} FROM {role};
                  END IF;
                END $$;
                """
            )

    exercises = sa.table(
        "exercises",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("aliases", postgresql.ARRAY(sa.String)),
        sa.column("muscle_group", sa.String),
        sa.column("mode", sa.String),
        sa.column("origin", sa.String),
        sa.column("search_text", sa.Text),
    )
    op.bulk_insert(
        exercises,
        [
            {
                "slug": slug,
                "name": name,
                "aliases": list(aliases),
                "muscle_group": muscle_group,
                "mode": mode,
                "origin": "system",
                "search_text": _search_text(name, aliases),
            }
            for slug, name, aliases, muscle_group, mode in CATALOG
        ],
    )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_strength_set_logs_user_id"), table_name="strength_set_logs")
    op.drop_index(op.f("ix_strength_set_logs_planned_workout_id"), table_name="strength_set_logs")
    op.drop_index(op.f("ix_strength_set_logs_exercise_id"), table_name="strength_set_logs")
    op.drop_index(op.f("ix_strength_set_logs_activity_id"), table_name="strength_set_logs")
    op.drop_table("strength_set_logs")
    op.drop_index(
        op.f("ix_planned_strength_exercises_user_id"), table_name="planned_strength_exercises"
    )
    op.drop_index(
        op.f("ix_planned_strength_exercises_exercise_id"), table_name="planned_strength_exercises"
    )
    op.drop_table("planned_strength_exercises")
    op.drop_index("ix_planned_workouts_user_id_scheduled_on", table_name="planned_workouts")
    op.drop_index(op.f("ix_planned_workouts_user_id"), table_name="planned_workouts")
    op.drop_table("planned_workouts")
    op.drop_index(
        "uq_exercises_user_slug",
        table_name="exercises",
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index(
        "uq_exercises_system_slug",
        table_name="exercises",
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.drop_index(op.f("ix_exercises_user_id"), table_name="exercises")
    op.drop_table("exercises")
    # ### end Alembic commands ###
