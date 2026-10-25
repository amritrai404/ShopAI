
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Expense, Product, Sale, SaleItem
from app.analytics import (
    get_profit_summary,
    get_revenue_summary,
    get_top_products,
)


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    return testing_session()


def seed(db):
    db.add_all([
        Product(
            product_id="P1",
            product_name="A",
            cost_price=10,
            selling_price=15,
            current_stock=5,
        ),
        Product(
            product_id="P2",
            product_name="B",
            cost_price=5,
            selling_price=8,
            current_stock=20,
        ),
    ])

    db.add_all([
        Sale(
            sale_id="S1",
            date=date(2026, 1, 5),
            customer_id="C1",
        ),
        Sale(
            sale_id="S2",
            date=date(2026, 1, 10),
            customer_id="C2",
        ),
    ])

    db.add_all([
        SaleItem(
            sale_id="S1",
            product_id="P1",
            quantity=2,
            discount=1,
        ),
        SaleItem(
            sale_id="S2",
            product_id="P2",
            quantity=10,
            discount=0,
        ),
    ])

    db.add(
        Expense(
            expense_id="E1",
            date=date(2026, 1, 1),
            category="Rent",
            amount=50,
        )
    )

    db.commit()


def test_revenue_summary():
    db = make_db()
    try:
        seed(db)

        result = get_revenue_summary(
            db,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert result.gross_revenue == Decimal("110.00")
        assert result.total_discount == Decimal("1.00")
        assert result.net_revenue == Decimal("109.00")
        assert result.transaction_count == 2
        assert result.line_item_count == 2
    finally:
        db.close()


def test_profit_summary():
    db = make_db()
    try:
        seed(db)

        result = get_profit_summary(
            db,
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

        assert result.net_revenue == Decimal("109.00")
        assert result.cogs == Decimal("70.00")
        assert result.gross_profit == Decimal("39.00")
        assert result.operating_expenses == Decimal("50.00")
        assert result.operating_profit == Decimal("-11.00")
    finally:
        db.close()


def test_top_products():
    db = make_db()
    try:
        seed(db)

        top = get_top_products(db, limit=1, by="units")

        assert len(top) == 1
        assert top[0].product_id == "P2"
        assert top[0].units_sold == 10
        assert top[0].revenue == Decimal("80.00")
        assert top[0].gross_profit == Decimal("30.00")
    finally:
        db.close()
