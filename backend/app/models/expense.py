from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Expense(Base):
    __tablename__ = "expenses"

    expense_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )
