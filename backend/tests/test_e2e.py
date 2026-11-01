from __future__ import annotations

from datetime import date, timedelta

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
    return Session(), engine


def seed_minimal(db, days: int = 60):
    db.add(Product(product_id="P1", product_name="A", cost_price=10, selling_price=15, current_stock=100))
    start = date(2026, 1, 1)
    for i in range(days):
        d = start + timedelta(days=i)
        sid = f"S{i}"
        db.add(Sale(sale_id=sid, date=d, customer_id=None))
        db.add(SaleItem(sale_id=sid, product_id="P1", quantity=3, discount=0))
    db.add(Expense(expense_id="E1", date=start, category="Rent", amount=100))
    db.commit()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import app.ml.forecast as forecast_module
    import app.ml.predict as predict_module
    import app.core.config as config_module

    test_models = tmp_path / "models"
    test_models.mkdir()
    monkeypatch.setattr(forecast_module, "MODELS_DIR", test_models)
    monkeypatch.setattr(predict_module, "MODELS_DIR", test_models)
    monkeypatch.setattr(config_module.settings, "faiss_index_dir", str(tmp_path / "faiss"))
    monkeypatch.setattr(config_module.settings, "upload_dir", str(tmp_path / "uploads"))

    db, engine = make_test_db()
    seed_minimal(db)

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_health_and_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "x-request-id" in {k.lower() for k in r.headers}


def test_analytics_flow(client):
    r = client.get("/analytics/revenue", params={"start": "2026-01-01", "end": "2026-02-28"})
    assert r.status_code == 200
    body = r.json()
    assert float(body["net_revenue"]) > 0


def test_forecast_end_to_end(client):
    r = client.post("/forecast/train", json={"test_ratio": 0.2})
    assert r.status_code == 200, r.json()
    assert r.json()["success"] is True

    r2 = client.get("/forecast?days=7")
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "ok"
    assert len(body["points"]) == 7


def test_document_upload_and_search(client, tmp_path):
    import fitz

    pdf_path = tmp_path / "supplier.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Supplier price list. Product P001 costs 240 rupees.")
    doc.save(pdf_path)
    doc.close()

    with open(pdf_path, "rb") as f:
        r = client.post(
            "/documents/upload",
            files={"file": ("supplier.pdf", f, "application/pdf")},
        )

    assert r.status_code == 200, r.json()
    doc_id = r.json()["id"]

    r2 = client.post("/documents/search", json={"document_id": doc_id, "query": "P001 price"})
    assert r2.status_code == 200
    hits = r2.json()["hits"]
    assert len(hits) > 0
    assert hits[0]["page"] == 1