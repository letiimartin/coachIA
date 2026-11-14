"""Tests del esquema v1 contra un Postgres real.

Necesitan TEST_DATABASE_URL apuntando a una base de datos DESECHABLE: se borran y recrean los
esquemas public y auth. Sin la variable, se omiten (en CI se usa un contenedor de Postgres).
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.models import (
    Activity,
    ActivitySource,
    AthleteProfile,
    AthleteThreshold,
    CalendarEvent,
    EventKind,
    Race,
    Sport,
)
from tests.conftest import requires_db

pytestmark = requires_db


def _activity(user_id: uuid.UUID, external_id: str = "123") -> Activity:
    return Activity(
        user_id=user_id,
        source=ActivitySource.WAHOO,
        external_id=external_id,
        sport=Sport.CYCLING,
        start_at=datetime(2026, 11, 1, 8, 0, tzinfo=UTC),
        elapsed_s=3600,
    )


def test_migrations_upgrade_downgrade_roundtrip(engine: Engine, alembic_config: Config) -> None:
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    head = ScriptDirectory.from_config(alembic_config).get_current_head()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == head


def test_models_match_migrations(engine: Engine, alembic_config: Config) -> None:
    command.check(alembic_config)  # falla si los modelos y las migraciones divergen


def test_row_level_security_is_enabled_on_every_table(engine: Engine) -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT relname FROM pg_class "
                "WHERE relnamespace = 'public'::regnamespace AND relkind = 'r' "
                "AND NOT relrowsecurity"
            )
        ).all()
    assert rows == []


def test_data_api_roles_have_no_privileges(engine: Engine) -> None:
    with engine.connect() as conn:
        grants = conn.execute(
            text(
                """
                SELECT grantee, table_name, privilege_type
                FROM information_schema.role_table_grants
                WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
                """
            )
        ).all()
    assert grants == []


def test_profile_requires_existing_auth_user(session: Session) -> None:
    session.add(AthleteProfile(user_id=uuid.uuid4()))

    with pytest.raises(IntegrityError):
        session.flush()


def test_profile_defaults(session: Session, athlete_id: uuid.UUID) -> None:
    profile = session.get(AthleteProfile, athlete_id)

    assert profile is not None
    assert profile.timezone == "Europe/Madrid"
    assert profile.sports == []
    assert profile.preferences == {}


def test_deleting_auth_user_cascades_to_all_data(engine: Engine, athlete_id: uuid.UUID) -> None:
    with Session(engine) as session:
        session.add(_activity(athlete_id))
        session.add(
            AthleteThreshold(user_id=athlete_id, effective_from=date(2026, 1, 1), ftp_w=220)
        )
        session.commit()

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": athlete_id})
        remaining = conn.execute(
            text(
                "SELECT (SELECT count(*) FROM athlete_profiles WHERE user_id = :id)"
                " + (SELECT count(*) FROM activities WHERE user_id = :id)"
                " + (SELECT count(*) FROM athlete_thresholds WHERE user_id = :id)"
            ),
            {"id": athlete_id},
        ).scalar()
    assert remaining == 0


def test_activity_is_unique_per_source_and_external_id(
    session: Session, athlete_id: uuid.UUID
) -> None:
    session.add(_activity(athlete_id, "abc"))
    session.flush()
    session.add(_activity(athlete_id, "abc"))

    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO athlete_thresholds (user_id, effective_from, ftp_w) "
        "VALUES (:u, '2026-01-01', 5)",
        "INSERT INTO activities (user_id, source, sport, start_at) "
        "VALUES (:u, 'wahoo', 'kayak', now())",
        "INSERT INTO availability_slots (user_id, weekday) VALUES (:u, 7)",
        "INSERT INTO calendar_events (user_id, kind, title, start_at, end_at) "
        "VALUES (:u, 'race', 'x', '2026-06-02', '2026-06-01')",
    ],
    ids=["ftp_fuera_de_rango", "deporte_no_valido", "dia_no_valido", "fin_antes_de_inicio"],
)
def test_check_constraints_reject_invalid_data(
    session: Session, athlete_id: uuid.UUID, statement: str
) -> None:
    with pytest.raises(IntegrityError):
        session.execute(text(statement), {"u": athlete_id})


def test_race_is_deleted_with_its_calendar_event(session: Session, athlete_id: uuid.UUID) -> None:
    start = datetime(2027, 6, 20, tzinfo=UTC)
    event = CalendarEvent(
        user_id=athlete_id,
        kind=EventKind.RACE,
        title="Quebrantahuesos",
        start_at=start,
        end_at=start + timedelta(hours=8),
    )
    session.add(event)
    session.flush()
    session.add(Race(event_id=event.id, user_id=athlete_id))
    session.flush()

    session.delete(event)
    session.flush()
    session.expire_all()

    assert session.get(Race, event.id) is None
