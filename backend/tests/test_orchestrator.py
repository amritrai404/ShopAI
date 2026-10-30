from __future__ import annotations

from datetime import date
from unittest.mock import patch

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
    return db, engine


def seed(db):
    db.add(Product(product_id="P1", product_name="Rice", cost_price=10, selling_price=15, current_stock=5))
    db.add(Sale(sale_id="S1", date=date(2026, 1, 15), customer_id="C1"))
    db.add(SaleItem(sale_id="S1", product_id="P1", quantity=4, discount=0))
    db.add(Expense(expense_id="E1", date=date(2026, 1, 10), category="Rent", amount=50))
    db.commit()


@pytest.fixture()
def client_with_data():
    db, engine = make_test_db()
    seed(db)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c, db
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_chat_tool_calling_flow(client_with_data):
    client, _ = client_with_data

    fake_tool_response = {
        "message": {
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_revenue",
                        "arguments": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
                    }
                }
            ],
        }
    }
    fake_final_response = {
        "message": {
            "content": "Your revenue in January 2026 was ₹60.",
            "tool_calls": [],
        }
    }

    with patch("app.llm.orchestrator.get_ollama_client") as mock_get:
        mock_client = mock_get.return_value
        mock_client.chat.side_effect = [fake_tool_response, fake_final_response]

        r = client.post("/chat", json={"message": "What was my revenue in January?"})
        assert r.status_code == 200, r.json()
        body = r.json()
        assert "get_revenue" in body["tools_used"]
        assert body["session_id"]
        assert "₹60" in body["answer"] or "60" in body["answer"]


def test_chat_no_tool_needed(client_with_data):
    client, _ = client_with_data

    fake_response = {
        "message": {
            "content": "Hello! I'm ShopAI, your business assistant.",
            "tool_calls": [],
        }
    }

    with patch("app.llm.orchestrator.get_ollama_client") as mock_get:
        mock_client = mock_get.return_value
        mock_client.chat.return_value = fake_response

        r = client.post("/chat", json={"message": "Hi"})
        assert r.status_code == 200
        body = r.json()
        assert "ShopAI" in body["answer"]
        assert body["tools_used"] == []