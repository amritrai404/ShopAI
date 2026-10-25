from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Expense, Product, Sale, SaleItem
from app.schemas.analytics import ProfitSummary, RevenueSummary


def _money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def get_revenue_summary(db: Session, start: date, end: date) -> RevenueSummary:
    """Net revenue = gross (qty * selling_price) - discount, in [start, end]."""
    stmt = (
        select(
            func.coalesce(
                func.sum(SaleItem.quantity * Product.selling_price), 0
            ).label("gross"),
            func.coalesce(func.sum(SaleItem.discount), 0).label("discount"),
            func.count(func.distinct(Sale.sale_id)).label("tx"),
            func.count(SaleItem.id).label("li"),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.sale_id == SaleItem.sale_id)
        .join(Product, Product.product_id == SaleItem.product_id)
        .where(Sale.date >= start, Sale.date <= end)
    )
    gross, discount, tx, li = db.execute(stmt).one()
    return RevenueSummary(
        start_date=start,
        end_date=end,
        gross_revenue=_money(gross),
        total_discount=_money(discount),
        net_revenue=_money(Decimal(str(gross)) - Decimal(str(discount))),
        transaction_count=int(tx or 0),
        line_item_count=int(li or 0),
    )


def get_profit_summary(db: Session, start: date, end: date) -> ProfitSummary:
    """Profit with explicit 'data_complete' flags for missing inputs."""
    notes: list[str] = []
    data_complete = True

    rev = get_revenue_summary(db, start, end)

    cogs_stmt = (
        select(func.coalesce(func.sum(SaleItem.quantity * Product.cost_price), 0))
        .select_from(SaleItem)
        .join(Sale, Sale.sale_id == SaleItem.sale_id)
        .join(Product, Product.product_id == SaleItem.product_id)
        .where(Sale.date >= start, Sale.date <= end)
    )
    cogs_raw = db.execute(cogs_stmt).scalar()
    cogs = _money(cogs_raw)

    exp_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.date >= start, Expense.date <= end
    )
    op_ex_raw = db.execute(exp_stmt).scalar()
    op_ex = _money(op_ex_raw)

    if rev.transaction_count == 0:
        data_complete = False
        notes.append("No sales found in this date range.")

    if float(cogs) == 0.0 and float(rev.net_revenue) > 0:
        data_complete = False
        notes.append("COGS is zero — product cost prices may be missing.")

    if float(op_ex) == 0.0 and rev.transaction_count > 0:
        notes.append("No operating expenses recorded for this period.")

    gross_profit = _money(rev.net_revenue - cogs)
    operating_profit = _money(gross_profit - op_ex)

    gross_margin = (
        float(gross_profit / rev.net_revenue * 100) if float(rev.net_revenue) > 0 else 0.0
    )
    op_margin = (
        float(operating_profit / rev.net_revenue * 100) if float(rev.net_revenue) > 0 else 0.0
    )

    return ProfitSummary(
        start_date=start,
        end_date=end,
        net_revenue=rev.net_revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        operating_expenses=op_ex,
        operating_profit=operating_profit,
        gross_margin_pct=round(gross_margin, 2),
        operating_margin_pct=round(op_margin, 2),
        data_complete=data_complete,
        notes=notes,
    )


def get_monthly_revenue(db: Session, start: date, end: date) -> list[dict]:
    """Revenue grouped by calendar month, ordered ascending."""
    month = func.date_trunc("month", Sale.date).label("month")
    stmt = (
        select(
            month,
            func.coalesce(func.sum(SaleItem.quantity * Product.selling_price), 0),
            func.coalesce(func.sum(SaleItem.discount), 0),
        )
        .select_from(SaleItem)
        .join(Sale, Sale.sale_id == SaleItem.sale_id)
        .join(Product, Product.product_id == SaleItem.product_id)
        .where(Sale.date >= start, Sale.date <= end)
        .group_by(month)
        .order_by(month)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "month": row[0].date().isoformat() if row[0] else None,
            "gross": _money(row[1]),
            "discount": _money(row[2]),
            "net": _money(Decimal(str(row[1])) - Decimal(str(row[2]))),
        }
        for row in rows
    ]