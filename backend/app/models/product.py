from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
    )
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    cost_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    selling_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    current_stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
