from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Sale(Base):
    __tablename__ = "sales"

    sale_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    sale_id: Mapped[str] = mapped_column(
        ForeignKey("sales.sale_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.product_id"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    discount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    sale: Mapped["Sale"] = relationship(
        back_populates="items",
    )
