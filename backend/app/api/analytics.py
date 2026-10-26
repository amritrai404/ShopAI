from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analytics import (
    get_low_stock,
    get_monthly_revenue,
    get_profit_summary,
    get_revenue_summary,
    get_top_products,
)
from app.api.deps import get_db
from app.schemas.analytics import (
    LowStockItem,
    ProductPerformance,
    ProfitSummary,
    RevenueSummary,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _check_range(start: date, end: date) -> None:
    if start > end:
        raise HTTPException(
            status_code=400, detail="start date must be on or before end date"
        )


@router.get("/revenue", response_model=RevenueSummary)
def revenue(
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    _check_range(start, end)
    try:
        return get_revenue_summary(db, start, end)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.get("/profit", response_model=ProfitSummary)
def profit(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
):
    _check_range(start, end)
    try:
        return get_profit_summary(db, start, end)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.get("/top-products", response_model=list[ProductPerformance])
def top_products(
    limit: int = Query(5, ge=1, le=50),
    by: str = Query("revenue", pattern="^(revenue|units)$"),
    db: Session = Depends(get_db),
):
    try:
        return get_top_products(db, limit=limit, by=by)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.get("/low-stock", response_model=list[LowStockItem])
def low_stock(
    threshold: int = Query(50, ge=0, le=10000),
    db: Session = Depends(get_db),
):
    try:
        return get_low_stock(db, threshold=threshold)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.get("/monthly-trend")
def monthly_trend(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
):
    _check_range(start, end)
    try:
        return get_monthly_revenue(db, start, end)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc