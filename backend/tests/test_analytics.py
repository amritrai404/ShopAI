from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import Expense, Product, Sale, SaleItem
from app.analytics import get_profit_summary, get_revenue_summary, get_top_products


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(db):
    db.add_all([
        Product(product_id="P1", product_name="A", cost_price=10, selling_price=15, current_stock=5),
        Product(product_id="P2", product_name="B", cost_price=5, selling_price=8, current_stock=20),
    ])
    db.add_all([
        Sale(sale_id="S1", date=date(2026, 1, 5), customer_id="C1"),
        Sale(sale_id="S2", date=date(2026, 1, 10), customer_id="C2"),
    ])
    db.add_all([
        SaleItem(sale_id="S1", product_id="P1", quantity=2, discount=1),
        SaleItem(sale_id="S2", product_id="P2", quantity=10, discount=0),
    ])
    db.add(Expense(expense_id="E1", date=date(2026, 1, 1), category="Rent", amount=50))
    db.commit()


def test_revenue_summary():
    db = make_db()
    seed(db)
    r = get_revenue_summary(db, date(2026, 1, 1), date(2026, 1, 31))
    assert r.gross_revenue == 110  # 2*15 + 10*8
    assert r.total_discount == 1
    assert r.net_revenue == 109
    assert r.transaction_count == 2


def test_profit_summary():
    db = make_db()
    seed(db)
    p = get_profit_summary(db, date(2026, 1, 1), date(2026, 1, 31))
    assert p.cogs == 70  # 2*10 + 10*5
    assert p.gross_profit == 39
    assert p.operating_profit == -11


def test_top_products():
    db = make_db()
    seed(db)
    top = get_top_products(db, limit=1, by="units")
    assert top[0].product_id == "P2"
    assert top[0].units_sold == 10