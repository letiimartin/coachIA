"""Serie diaria de carga y forma (CTL/ATL/TSB), regenerada por `services.fitness`.

Es un dato derivado: se recalcula desde una fecha con `recompute_from` y nunca se edita a mano.
La serie es continua desde el día de la primera actividad hasta hoy (o la última actividad).
"""

import uuid
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.common import TimestampMixin


class DailyLoad(TimestampMixin, Base):
    """Carga total de un día (suma de sus actividades) y CTL/ATL/TSB al final de ese día.

    El TSB es el de TrainingPeaks: CTL − ATL del día anterior. El día es el local en la zona
    horaria del atleta.
    """

    __tablename__ = "daily_load"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("athlete_profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    day: Mapped[date] = mapped_column(primary_key=True)
    load: Mapped[Decimal] = mapped_column(sa.Numeric(7, 1))
    # Sin redondear (double precision): un recálculo parcial continúa desde el valor guardado
    # del día anterior y así da exactamente lo mismo que regenerar la serie entera.
    ctl: Mapped[float] = mapped_column(sa.Double)
    atl: Mapped[float] = mapped_column(sa.Double)
    tsb: Mapped[float] = mapped_column(sa.Double)

    __table_args__ = (
        sa.CheckConstraint("load >= 0", name="load"),
        sa.CheckConstraint("ctl >= 0 AND atl >= 0", name="ctl_atl"),
    )
