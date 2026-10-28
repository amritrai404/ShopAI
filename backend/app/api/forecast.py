from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.ml.forecast import train_forecast
from app.ml.predict import find_latest_model, generate_forecast, load_model
from app.models import MLModelRun, Product, Sale, SaleItem
from app.schemas.ml import (
    ForecastPoint,
    ForecastResponse,
    ModelRunSummary,
    TrainRequest,
    TrainResponse,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _load_sales_df(db: Session) -> pd.DataFrame:
    stmt = (
        select(
            Sale.sale_id,
            Sale.date,
            SaleItem.quantity,
            Product.selling_price,
            SaleItem.discount,
        )
        .join(SaleItem, SaleItem.sale_id == Sale.sale_id)
        .join(Product, Product.product_id == SaleItem.product_id)
    )
    rows = db.execute(stmt).all()
    df = pd.DataFrame(
        rows, columns=["sale_id", "date", "quantity", "selling_price", "discount"]
    )
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["revenue"] = df["quantity"] * df["selling_price"] - df["discount"]
    return df.rename(columns={"quantity": "units"})


@router.post("/train", response_model=TrainResponse)
def train(db: Session = Depends(get_db), payload: TrainRequest | None = None):
    test_ratio = payload.test_ratio if payload else 0.2
    df = _load_sales_df(db)

    if df.empty:
        raise HTTPException(status_code=400, detail="No sales data available for training.")

    try:
        result = train_forecast(df, test_ratio=test_ratio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Training failed: {exc}") from exc

    try:
        run = MLModelRun(
            model_name="sales_forecast_rf",
            version=result["version"],
            n_samples=result["n_samples"],
            metrics={
                "model": result["model"],
                "baseline": result["baseline"],
                "beats_baseline": result["beats_baseline"],
                "train_size": result["train_size"],
                "test_size": result["test_size"],
            },
            artifact_path=result["artifact_path"],
        )
        db.add(run)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log run: {exc}") from exc

    return TrainResponse(
        success=True,
        message="Model trained successfully.",
        metrics={
            "model": result["model"],
            "baseline": result["baseline"],
            "beats_baseline": result["beats_baseline"],
        },
        version=result["version"],
        artifact_path=result["artifact_path"],
    )


@router.get("", response_model=ForecastResponse)
def forecast(db: Session = Depends(get_db), days: int = Query(7, ge=1, le=30)):
    model_path = find_latest_model()
    if model_path is None:
        return ForecastResponse(
            status="no_model",
            message="No trained model found. Train one via POST /forecast/train first.",
        )

    try:
        bundle = load_model(model_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {exc}") from exc

    df = _load_sales_df(db)
    if df.empty:
        return ForecastResponse(
            status="insufficient_data",
            message="No sales history available in database.",
        )

    # Explicit column naming to avoid groupby index naming surprises
    daily = (
        df.assign(day=df["date"].dt.normalize())
        .groupby("day", as_index=False)["revenue"]
        .sum()
        .rename(columns={"day": "date"})
    )

    if len(daily) < 14:
        return ForecastResponse(
            status="insufficient_data",
            message=f"Need at least 14 days of history for prediction; have {len(daily)}.",
        )

    try:
        raw_points = generate_forecast(bundle, daily, days=days)
    except ValueError as exc:
        return ForecastResponse(status="insufficient_data", message=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Forecast generation failed: {exc}"
        ) from exc

    return ForecastResponse(
        status="ok",
        message=None,
        model_version=bundle.get("version"),
        generated_at=datetime.now(timezone.utc),
        points=[
            ForecastPoint(date=p["date"], predicted_revenue=p["predicted_revenue"])
            for p in raw_points
        ],
    )


@router.get("/history", response_model=list[ModelRunSummary])
def history(db: Session = Depends(get_db), limit: int = Query(10, ge=1, le=100)):
    stmt = select(MLModelRun).order_by(MLModelRun.trained_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())