"""Migración compatible de #22 (LTHR por disciplina, `rpe`, `session_rpe`) y LTHR antiguo.

La migración no renombra `lthr_bpm`: el código lo lee como `legacy_lthr_bpm`.
"""

import uuid
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.models import AthleteThreshold
from app.services.legacy_lthr import (
    Assignment,
    LegacyPlanError,
    LegacyTarget,
    apply_plan,
    pending_rows,
    plan_changes,
)
from scripts.assign_legacy_lthr import read_plan
from tests.conftest import requires_db

pytestmark = requires_db

BEFORE = "8d82e2645fa7"
REVISION = "5b1e9c3a7d24"


def _columns(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        return set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns"
                    " WHERE table_schema = 'public' AND table_name = 'athlete_thresholds'"
                )
            ).scalars()
        )


@pytest.fixture
def migrated_user(engine: Engine, alembic_config: Config) -> Iterator[uuid.UUID]:
    """Atleta con umbrales antiguos creados antes de la migración de #22."""
    user = uuid.uuid4()
    command.downgrade(alembic_config, BEFORE)
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO auth.users (id) VALUES (:u)"), {"u": user})
            conn.execute(text("INSERT INTO athlete_profiles (user_id) VALUES (:u)"), {"u": user})
            conn.execute(
                text(
                    "INSERT INTO athlete_thresholds (user_id, effective_from, lthr_bpm, ftp_w)"
                    " VALUES (:u, '2026-01-01', 168, 230), (:u, '2026-06-01', 177, NULL),"
                    " (:u, '2026-09-01', NULL, 240)"
                ),
                {"u": user},
            )
            conn.execute(
                text(
                    "INSERT INTO activities (user_id, source, external_id, sport, start_at,"
                    " moving_s, load, load_method) VALUES"
                    " (:u, 'wahoo', 'a1', 'cycling', '2026-02-01T08:00Z', 3600, 64.0, 'power'),"
                    " (:u, 'wahoo', 'a2', 'strength', '2026-02-02T08:00Z', 3600, 50.0,"
                    " 'heart_rate')"
                ),
                {"u": user},
            )
        command.upgrade(alembic_config, "head")
        yield user
    finally:
        command.upgrade(alembic_config, "head")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.users WHERE id = :u"), {"u": user})


def _rows(engine: Engine, user: uuid.UUID) -> list[tuple[object, ...]]:
    with engine.connect() as conn:
        return [
            tuple(row)
            for row in conn.execute(
                text(
                    "SELECT effective_from::text, lthr_bpm, cycling_lthr_bpm,"
                    " running_lthr_bpm FROM athlete_thresholds WHERE user_id = :u"
                    " ORDER BY effective_from"
                ),
                {"u": user},
            )
        ]


def test_migration_keeps_old_values_without_assigning_them(
    engine: Engine, migrated_user: uuid.UUID
) -> None:
    # Compatible: lthr_bpm sigue ahí con su nombre (el código desplegado lo usa).
    assert {"lthr_bpm", "cycling_lthr_bpm", "running_lthr_bpm"} <= _columns(engine)
    assert "legacy_lthr_bpm" not in _columns(engine)
    assert _rows(engine, migrated_user) == [
        ("2026-01-01", 168, None, None),
        ("2026-06-01", 177, None, None),
        ("2026-09-01", None, None, None),
    ]


def test_migration_downgrade_keeps_lthr_bpm(
    engine: Engine, alembic_config: Config, migrated_user: uuid.UUID
) -> None:
    command.downgrade(alembic_config, BEFORE)
    columns = _columns(engine)
    assert "lthr_bpm" in columns
    assert not {"legacy_lthr_bpm", "cycling_lthr_bpm", "running_lthr_bpm"} & columns
    with engine.connect() as conn:
        values = conn.execute(
            text(
                "SELECT lthr_bpm FROM athlete_thresholds WHERE user_id = :u ORDER BY effective_from"
            ),
            {"u": migrated_user},
        ).scalars()
        assert list(values) == [168, 177, None]
        constraints = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint"
                    " WHERE conrelid = 'public.athlete_thresholds'::regclass AND contype = 'c'"
                )
            ).scalars()
        )
    assert "ck_athlete_thresholds_lthr" in constraints
    command.upgrade(alembic_config, REVISION)
    assert _rows(engine, migrated_user)[0] == ("2026-01-01", 168, None, None)


def test_migration_is_compatible_with_code_that_still_uses_lthr_bpm(
    engine: Engine, migrated_user: uuid.UUID
) -> None:
    # El código desplegado antes de #22 escribe y lee `lthr_bpm`: sigue funcionando.
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO athlete_thresholds (user_id, effective_from, lthr_bpm)"
                " VALUES (:u, '2026-10-01', 171)"
            ),
            {"u": migrated_user},
        )
        conn.execute(
            text(
                "INSERT INTO activities (user_id, source, external_id, sport, start_at, load,"
                " load_method) VALUES (:u, 'wahoo', 'old', 'cycling', '2026-10-02T08:00Z', 50,"
                " 'heart_rate')"
            ),
            {"u": migrated_user},
        )
    # Y el código nuevo lo lee como `legacy_lthr_bpm`.
    with Session(engine) as session:
        row = session.scalars(
            select(AthleteThreshold).where(
                AthleteThreshold.user_id == migrated_user,
                AthleteThreshold.legacy_lthr_bpm == 171,
            )
        ).one()
        assert (row.cycling_lthr_bpm, row.running_lthr_bpm) == (None, None)


@pytest.mark.parametrize("column", ["cycling_lthr_bpm", "running_lthr_bpm", "lthr_bpm"])
@pytest.mark.parametrize("value", [79, 231])
def test_lthr_columns_have_the_same_check(
    session: Session, athlete_id: uuid.UUID, column: str, value: int
) -> None:
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                f"INSERT INTO athlete_thresholds (user_id, effective_from, {column})"  # noqa: S608
                " VALUES (:u, '2026-01-01', :v)"
            ),
            {"u": athlete_id, "v": value},
        )


def _activity_loads(engine: Engine, user: uuid.UUID) -> list[tuple[object, ...]]:
    with engine.connect() as conn:
        return [
            tuple(row)
            for row in conn.execute(
                text(
                    "SELECT external_id, load, load_method FROM activities"
                    " WHERE user_id = :u ORDER BY external_id"
                ),
                {"u": user},
            )
        ]


def test_migration_adds_rpe_and_session_rpe_keeping_existing_loads(
    engine: Engine, alembic_config: Config, migrated_user: uuid.UUID
) -> None:
    # Las cargas existentes no cambian (tampoco la TSS antigua de fuerza).
    assert _activity_loads(engine, migrated_user) == [
        ("a1", Decimal("64.0"), "power"),
        ("a2", Decimal("50.0"), "heart_rate"),
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO activities (user_id, source, external_id, sport, start_at, rpe,"
                " load, load_method) VALUES"
                " (:u, 'manual', 'a3', 'strength', '2026-02-03T08:00Z', 7, 420.0, 'session_rpe')"
            ),
            {"u": migrated_user},
        )
        with pytest.raises(IntegrityError), conn.begin_nested():
            conn.execute(
                text(
                    "UPDATE activities SET load_method = 'inventado'"
                    " WHERE user_id = :u AND external_id = 'a3'"
                ),
                {"u": migrated_user},
            )

    # Downgrade con datos: la carga session_rpe se vacía (su origen, rpe, desaparece).
    command.downgrade(alembic_config, BEFORE)
    with engine.connect() as conn:
        activity_columns = set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns"
                    " WHERE table_schema = 'public' AND table_name = 'activities'"
                )
            ).scalars()
        )
    assert "rpe" not in activity_columns
    assert _activity_loads(engine, migrated_user) == [
        ("a1", Decimal("64.0"), "power"),
        ("a2", Decimal("50.0"), "heart_rate"),
        ("a3", None, None),
    ]
    with engine.begin() as conn, pytest.raises(IntegrityError):
        conn.execute(
            text(
                "UPDATE activities SET load_method = 'session_rpe'"
                " WHERE user_id = :u AND external_id = 'a3'"
            ),
            {"u": migrated_user},
        )
    command.upgrade(alembic_config, REVISION)


# --- Asignación revisable de los valores antiguos ---------------------------------------------


def _ids(session: Session, user: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.scalars(
            AthleteThreshold.__table__.select()
            .with_only_columns(AthleteThreshold.id)
            .where(AthleteThreshold.user_id == user)
            .order_by(AthleteThreshold.effective_from)
        )
    )


def test_assign_legacy_plan_dry_run_then_apply(engine: Engine, migrated_user: uuid.UUID) -> None:
    with Session(engine) as session:
        first, second, without = _ids(session, migrated_user)
        assert [row.id for row in pending_rows(session)] == [first, second]
        plan = [
            Assignment(first, LegacyTarget.CYCLING),
            Assignment(second, LegacyTarget.RUNNING),
        ]

        changes = plan_changes(session, plan)
        assert [(c.column, c.legacy_lthr_bpm, c.already_applied) for c in changes] == [
            ("cycling_lthr_bpm", 168, False),
            ("running_lthr_bpm", 177, False),
        ]
        session.rollback()
        assert _rows(engine, migrated_user)[0] == ("2026-01-01", 168, None, None)

        apply_plan(session, [*plan, Assignment(without, LegacyTarget.NONE)][:2])
        session.commit()
    assert _rows(engine, migrated_user) == [
        ("2026-01-01", 168, 168, None),
        ("2026-06-01", 177, None, 177),
        ("2026-09-01", None, None, None),
    ]

    # Repetirlo no cambia nada; "none" no toca la fila.
    with Session(engine) as session:
        again = apply_plan(session, plan)
        assert all(change.already_applied for change in again)
        session.commit()
    assert _rows(engine, migrated_user)[1] == ("2026-06-01", 177, None, 177)


def test_assign_legacy_plan_rejects_invalid_rows_and_writes_nothing(
    engine: Engine, migrated_user: uuid.UUID
) -> None:
    with Session(engine) as session:
        first, second, without = _ids(session, migrated_user)
        session.execute(
            AthleteThreshold.__table__.update()
            .where(AthleteThreshold.id == second)
            .values(running_lthr_bpm=180)
        )
        session.commit()
        plan = [
            Assignment(first, LegacyTarget.CYCLING),
            Assignment(first, LegacyTarget.RUNNING),
            Assignment(second, LegacyTarget.RUNNING),
            Assignment(without, LegacyTarget.CYCLING),
            Assignment(uuid.uuid4(), LegacyTarget.NONE),
        ]
        with pytest.raises(LegacyPlanError) as error:
            apply_plan(session, plan)
        session.rollback()
    messages = error.value.errors
    assert len(messages) == 4
    assert any("más de una vez" in m for m in messages)
    assert any("ya vale 180" in m for m in messages)
    assert any("no tiene LTHR antiguo" in m for m in messages)
    assert any("no existe" in m for m in messages)
    assert _rows(engine, migrated_user)[0] == ("2026-01-01", 168, None, None)


def test_read_plan_csv(tmp_path: Path) -> None:
    path = tmp_path / "plan.csv"
    ident = uuid.uuid4()
    path.write_text(
        "threshold_id,user_id,effective_from,legacy_lthr_bpm,assign_to\n"
        f"{ident},x,2026-01-01,168,cycling\n",
        encoding="utf-8",
    )
    assert read_plan(path) == [Assignment(ident, LegacyTarget.CYCLING)]
    path.write_text(f"threshold_id,assign_to\n{ident},\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        read_plan(path)
    path.write_text(f"threshold_id,assign_to\n{ident},trail\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        read_plan(path)
