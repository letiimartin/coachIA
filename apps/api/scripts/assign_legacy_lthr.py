"""Asigna el LTHR antiguo (`legacy_lthr_bpm`) a ciclismo, a carrera o a ninguna, fila a fila.

**Sólo con autorización de la autora.** Por defecto no escribe nada.

Uso (desde `apps/api`, con DATABASE_URL apuntando a la BD):

    # 1. Plantilla CSV con las filas que tienen LTHR antiguo (columna assign_to vacía):
    uv run python -m scripts.assign_legacy_lthr template > plan.csv
    # 2. La autora rellena assign_to con cycling, running o none en cada fila.
    # 3. Simulación: valida el plan y dice qué cambiaría.
    uv run python -m scripts.assign_legacy_lthr plan plan.csv
    # 4. Aplicación (una transacción; si una fila falla, no se aplica nada):
    uv run python -m scripts.assign_legacy_lthr plan plan.csv --apply

No recalcula cargas. Después, `scripts.recompute_loads` (primero en simulación).
"""

import argparse
import csv
import sys
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import Database
from app.services.legacy_lthr import (
    Assignment,
    LegacyPlanError,
    LegacyTarget,
    apply_plan,
    pending_rows,
    plan_changes,
)

FIELDS = ("threshold_id", "user_id", "effective_from", "legacy_lthr_bpm", "assign_to")


def read_plan(path: Path) -> list[Assignment]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    plan: list[Assignment] = []
    for number, row in enumerate(rows, start=2):
        target = (row.get("assign_to") or "").strip()
        if not target:
            raise SystemExit(f"Línea {number}: falta assign_to (cycling, running o none)")
        try:
            plan.append(Assignment(uuid.UUID(row["threshold_id"]), LegacyTarget(target)))
        except (KeyError, ValueError) as exc:
            raise SystemExit(f"Línea {number}: {exc}") from exc
    return plan


def _template(session: Session) -> None:
    writer = csv.writer(sys.stdout)
    writer.writerow(FIELDS)
    for row in pending_rows(session):
        writer.writerow(
            [row.id, row.user_id, row.effective_from.isoformat(), row.legacy_lthr_bpm, ""]
        )


def _plan(session: Session, path: Path, *, apply: bool) -> int:
    plan = read_plan(path)
    try:
        changes = apply_plan(session, plan) if apply else plan_changes(session, plan)
    except LegacyPlanError as exc:
        session.rollback()
        print("Plan rechazado, no se ha escrito nada:", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    for change in changes:
        action = (
            "sin cambios"
            if change.already_applied
            else f"{change.column} = {change.legacy_lthr_bpm}"
        )
        print(f"{change.threshold_id} {change.effective_from} → {change.target}: {action}")
    if apply:
        session.commit()
        print("Aplicado.")
    else:
        session.rollback()
        print("Simulación: no se ha escrito nada. Añade --apply para aplicarlo.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("template", help="CSV con las filas que tienen LTHR antiguo")
    plan = sub.add_parser("plan", help="valida (y con --apply aplica) un plan CSV")
    plan.add_argument("path", type=Path)
    plan.add_argument("--apply", action="store_true", help="escribe en la BD")
    args = parser.parse_args(argv)

    database = Database.from_settings(Settings())
    if database.engine is None:
        raise SystemExit("Falta DATABASE_URL.")
    try:
        with Session(database.engine) as session:
            if args.command == "template":
                _template(session)
                return 0
            return _plan(session, args.path, apply=args.apply)
    finally:
        database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
