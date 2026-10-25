from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, SaleItem
from app.schemas.analytics import LowStockItem, ProductPerformance


def get_top_products(db: Session, limit: int = 5, by: str = "revenue") -> list[ProductPerformance]:
    """Top products by revenue (default) or units sold."""
    revenue_expr = func.sum(SaleItem.quantity * Product.selling_price - SaleItem.discount)
    profit_expr = func.sum(
        (Product.selling_price - Product.cost_price) * SaleItem.quantity - SaleItem.discount
    )
    units_expr = func.sum(SaleItem.quantity)

    order_col = revenue_expr.desc() if by == "revenue" else units_expr.desc()

    stmt = (
        select(
            Product.product_id,
            Product.product_name,
            units_expr.label("units"),
            revenue_expr.label("revenue"),
            profit_expr.label("profit"),
        )
        .select_from(SaleItem)
        .join(Product, Product.product_id == SaleItem.product_id)
        .group_by(Product.product_id, Product.product_name)
        .order_by(order_col)
        .limit(limit)
    )
    return [
        ProductPerformance(
            product_id=r.product_id,
            product_name=r.product_name,
            units_sold=int(r.units or 0),
            revenue=Decimal(str(r.revenue or 0)).quantize(Decimal("0.01")),
            gross_profit=Decimal(str(r.profit or 0)).quantize(Decimal("0.01")),
        )
        for r in db.execute(stmt).all()
    ]


def get_low_stock(db: Session, threshold: int = 50) -> list[LowStockItem]:
    stmt = (
        select(Product.product_id, Product.product_name, Product.current_stock, Product.selling_price)
        .where(Product.current_stock < threshold)
        .order_by(Product.current_stock.asc())
    )
    return [
        LowStockItem(
            product_id=r.product_id,
            product_name=r.product_name,
            current_stock=int(r.current_stock),
            selling_price=Decimal(str(r.selling_price)).quantize(Decimal("0.01")),
        )
        for r in db.execute(stmt).all()
    ]