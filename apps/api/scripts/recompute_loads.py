"""Recálculo histórico de la carga de las actividades y de la forma (#22).

**Sólo con autorización de la autora**, después de validar la migración y los umbrales por
disciplina. Por defecto es una **simulación** que no escribe nada e informa de:

- qué actividades cambiarían de carga o de método y en cuánto;
- cuánto cambiaría la curva (CTL/ATL/TSB) al excluir senderismo, natación y otros, y con el
  recálculo completo. Con `--curve-csv` se guarda la curva día a día para revisarla.

Uso (desde `apps/api`, con DATABASE_URL apuntando a la BD):

    uv run python -m scripts.recompute_loads --user <uuid> [--since AAAA-MM-DD] [--curve-csv f.csv]
    uv run python -m scripts.recompute_loads --user <uuid> [--since AAAA-MM-DD] --apply

Con `--apply` recalcula también las actividades que ya tienen carga (salvo las de RPE, que son
manuales) y regenera `daily_load`, en una sola transacción.
"""

import argparse
import csv
import sys
import uuid
from datetime import date
from pathlib import Path

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


def _peak(deltas: list[fitness.CurveDelta]) -> fitness.CurveDelta | None:
    return max(deltas, key=lambda d: abs(d.ctl), default=None)


def curve_report(simulation: fitness.CurveSimulation) -> None:
    if not simulation.current:
        print("Sin actividades: la curva no cambia.")
        return
    for item in simulation.excluded:
        print(
            f"Se excluirían de la curva {item.activities} actividad(es) de {item.sport}"
            f" con {item.load:.1f} de carga histórica (se conserva en la actividad)."
        )
    last = simulation.current[-1]
    print(
        f"Curva actual el {last.day}: CTL {last.ctl:.1f}, ATL {last.atl:.1f}, TSB {last.tsb:.1f}."
    )
    for title, deltas in (
        (
            "Excluyendo la carga histórica (senderismo, natación, otros y TSS de fuerza)",
            simulation.exclusion_deltas,
        ),
        ("Con el recálculo completo", simulation.recompute_deltas),
    ):
        peak = _peak(deltas)
        if peak is None:
            continue
        end = deltas[-1]
        print(
            f"{title}: el {end.day} ΔCTL {end.ctl:+.1f}, ΔATL {end.atl:+.1f}, ΔTSB {end.tsb:+.1f};"
            f" mayor ΔCTL {peak.ctl:+.1f} el {peak.day}."
        )


def write_curve_csv(simulation: fitness.CurveSimulation, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "day",
                "ctl_now",
                "atl_now",
                "tsb_now",
                "ctl_excluding",
                "atl_excluding",
                "tsb_excluding",
                "ctl_recompute",
                "atl_recompute",
                "tsb_recompute",
            ]
        )
        for now, excluding, after in zip(
            simulation.current,
            simulation.without_historical,
            simulation.after_recompute,
            strict=True,
        ):
            writer.writerow(
                [
                    now.day.isoformat(),
                    *(
                        f"{value:.1f}"
                        for day in (now, excluding, after)
                        for value in (day.ctl, day.atl, day.tsb)
                    ),
                ]
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", type=uuid.UUID, required=True, help="user_id del atleta")
    parser.add_argument("--since", type=date.fromisoformat, default=date.min)
    parser.add_argument("--apply", action="store_true", help="escribe en la BD")
    parser.add_argument("--curve-csv", type=Path, help="guarda la curva simulada día a día")
    args = parser.parse_args(argv)

    database = Database.from_settings(Settings())
    if database.engine is None:
        raise SystemExit("Falta DATABASE_URL.")
    try:
        with Session(database.engine) as session:
            report(session, args.user, args.since)
            simulation = fitness.simulate_curve(session, args.user)
            curve_report(simulation)
            if args.curve_csv is not None:
                write_curve_csv(simulation, args.curve_csv)
                print(f"Curva día a día en {args.curve_csv}.")
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
