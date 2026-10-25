from __future__ import annotations

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class DateRange(BaseModel):
    model_config = ConfigDict(frozen=True)
    start: date
    end: date


class RevenueSummary(BaseModel):
    start_date: date
    end_date: date
    gross_revenue: Decimal
    total_discount: Decimal
    net_revenue: Decimal
    transaction_count: int
    line_item_count: int


class ProfitSummary(BaseModel):
    start_date: date
    end_date: date
    net_revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    operating_profit: Decimal
    gross_margin_pct: float
    operating_margin_pct: float
    data_complete: bool
    notes: list[str] = []


class ProductPerformance(BaseModel):
    product_id: str
    product_name: str
    units_sold: int
    revenue: Decimal
    gross_profit: Decimal


class LowStockItem(BaseModel):
    product_id: str
    product_name: str
    current_stock: int
    selling_price: Decimal