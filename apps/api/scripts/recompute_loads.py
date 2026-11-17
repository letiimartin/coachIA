"""Recálculo histórico de la carga de las actividades y de la forma (#22).

**Sólo con autorización de la autora**, después de validar la migración y los umbrales por
disciplina. Por defecto es una **simulación**: informa de qué actividades cambiarían de carga o
de método y en cuánto, sin escribir nada.

Uso (desde `apps/api`, con DATABASE_URL apuntando a la BD):

    uv run python -m scripts.recompute_loads --user <uuid> [--since AAAA-MM-DD]
    uv run python -m scripts.recompute_loads --user <uuid> [--since AAAA-MM-DD] --apply

Con `--apply` recalcula también las actividades que ya tienen carga (salvo las de RPE, que son
manuales) y regenera `daily_load`, en una sola transacción.
"""

import argparse
import sys
import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import Database
from app.models import AthleteThreshold
from app.services import fitness


def _fmt(value: object) -> str:
    return "—" if value is None else str(value)


def report(session: Session, user_id: uuid.UUID, since: date) -> list[fitness.LoadChange]:
    pending = session.scalar(
        sa.select(sa.func.count())
        .select_from(AthleteThreshold)
        .where(
            AthleteThreshold.user_id == user_id,
            AthleteThreshold.legacy_lthr_bpm.is_not(None),
            AthleteThreshold.cycling_lthr_bpm.is_(None),
            AthleteThreshold.running_lthr_bpm.is_(None),
        )
    )
    if pending:
        print(
            f"Aviso: {pending} umbral(es) con LTHR antiguo sin asignar a ninguna disciplina"
            " (scripts.assign_legacy_lthr).",
            file=sys.stderr,
        )
    changes = fitness.simulate_recompute(session, user_id, since)
    for change in changes:
        print(
            f"{change.start_at:%Y-%m-%d %H:%M} {change.sport:<14} {change.activity_id}"
            f"  {_fmt(change.old_load)} ({_fmt(change.old_method)})"
            f" → {_fmt(change.new_load)} ({_fmt(change.new_method)})"
            f"  Δ {_fmt(change.delta)}"
        )
    print(f"{len(changes)} actividad(es) cambiarían de carga o de método.")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", type=uuid.UUID, required=True, help="user_id del atleta")
    parser.add_argument("--since", type=date.fromisoformat, default=date.min)
    parser.add_argument("--apply", action="store_true", help="escribe en la BD")
    args = parser.parse_args(argv)

    database = Database.from_settings(Settings())
    if database.engine is None:
        raise SystemExit("Falta DATABASE_URL.")
    try:
        with Session(database.engine) as session:
            report(session, args.user, args.since)
            session.rollback()
            if not args.apply:
                print("Simulación: no se ha escrito nada. Añade --apply para aplicarlo.")
                return 0
            fitness.recompute_from(session, args.user, args.since, overwrite_existing=True)
            session.commit()
            print("Recálculo aplicado.")
            return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
