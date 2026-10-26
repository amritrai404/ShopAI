
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Expense, Product, Sale, SaleItem


def make_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    db.add_all(
        [
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
                current_stock=100,
            ),
        ]
    )

    db.add_all(
        [
            Sale(sale_id="S1", date=date(2026, 1, 5), customer_id="C1"),
            Sale(sale_id="S2", date=date(2026, 1, 10), customer_id="C2"),
        ]
    )

    db.add_all(
        [
            SaleItem(sale_id="S1", product_id="P1", quantity=2, discount=1),
            SaleItem(sale_id="S2", product_id="P2", quantity=10, discount=0),
        ]
    )

    db.add(
        Expense(
            expense_id="E1",
            date=date(2026, 1, 1),
            category="Rent",
            amount=50,
        )
    )

    db.commit()
    return db, engine


@pytest.fixture()
def client():
    db, engine = make_test_db()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["app"] == "ShopAI"


def test_revenue_endpoint(client):
    response = client.get(
        "/analytics/revenue",
        params={"start": "2026-01-01", "end": "2026-01-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["net_revenue"]) == Decimal("109")
    assert body["transaction_count"] == 2


def test_profit_endpoint(client):
    response = client.get(
        "/analytics/profit",
        params={"start": "2026-01-01", "end": "2026-01-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["cogs"]) == Decimal("70")
    assert Decimal(body["gross_profit"]) == Decimal("39")
    assert Decimal(body["operating_profit"]) == Decimal("-11")


def test_top_products_endpoint(client):
    response = client.get(
        "/analytics/top-products",
        params={"limit": 1, "by": "units"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["product_id"] == "P2"
    assert body[0]["units_sold"] == 10


def test_low_stock_endpoint(client):
    response = client.get(
        "/analytics/low-stock",
        params={"threshold": 50},
    )

    assert response.status_code == 200
    body = response.json()
    ids = [item["product_id"] for item in body]

    assert "P1" in ids
    assert "P2" not in ids


def test_invalid_date_range(client):
    response = client.get(
        "/analytics/revenue",
        params={"start": "2026-02-01", "end": "2026-01-01"},
    )

    assert response.status_code == 400


def test_invalid_by_param(client):
    response = client.get(
        "/analytics/top-products",
        params={"by": "profit"},
    )

    assert response.status_code == 422
