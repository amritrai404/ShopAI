from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models import Product, Sale, SaleItem


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


def seed_sales(db, days: int = 90):
    db.add(
        Product(
            product_id="P1",
            product_name="A",
            cost_price=10,
            selling_price=15,
            current_stock=100,
        )
    )
    start = date(2026, 1, 1)
    rng = np.random.default_rng(42)
    for i in range(days):
        d = start + timedelta(days=i)
        sid = f"S{i}"
        db.add(Sale(sale_id=sid, date=d, customer_id=None))
        qty = int(10 + rng.integers(-2, 3))
        db.add(SaleItem(sale_id=sid, product_id="P1", quantity=qty, discount=0))
    db.commit()


@pytest.fixture()
def isolated_models_dir(tmp_path, monkeypatch):
    import app.ml.predict as predict_module
    import app.ml.forecast as forecast_module

    test_models = tmp_path / "models"
    test_models.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(predict_module, "MODELS_DIR", test_models)
    monkeypatch.setattr(forecast_module, "MODELS_DIR", test_models)
    yield test_models


@pytest.fixture()
def client_empty(isolated_models_dir):
    db, engine = make_test_db()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


@pytest.fixture()
def client_with_sales(isolated_models_dir):
    db, engine = make_test_db()
    seed_sales(db, days=90)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_forecast_no_model(client_empty):
    r = client_empty.get("/forecast")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_model", f"Got: {body}"
    assert "Train one" in body["message"]


def test_train_insufficient_history(client_empty):
    r = client_empty.post("/forecast/train", json={"test_ratio": 0.2})
    assert r.status_code == 400
    assert "No sales data" in r.json()["detail"]


def test_train_and_forecast(client_with_sales):
    r = client_with_sales.post("/forecast/train", json={"test_ratio": 0.2})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["success"] is True
    assert "model" in body["metrics"]
    assert "baseline" in body["metrics"]
    assert body["version"].startswith("v")

    r2 = client_with_sales.get("/forecast?days=7")
    assert r2.status_code == 200, r2.json()
    fbody = r2.json()
    assert fbody["status"] == "ok", f"Got: {fbody}"
    assert len(fbody["points"]) == 7
    for pt in fbody["points"]:
        assert "date" in pt
        assert pt["predicted_revenue"] >= 0

    r3 = client_with_sales.get("/forecast/history?limit=5")
    assert r3.status_code == 200
    hist = r3.json()
    assert len(hist) >= 1
    assert hist[0]["model_name"] == "sales_forecast_rf"