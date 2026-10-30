from __future__ import annotations

from datetime import date
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.analytics import (
    get_low_stock,
    get_monthly_revenue,
    get_profit_summary,
    get_revenue_summary,
    get_top_products,
)
from app.ml.predict import find_latest_model, generate_forecast, load_model
import pandas as pd
from sqlalchemy import select
from app.models import Product, Sale, SaleItem


def _decimal_to_float(value) -> float:
    return float(value) if value is not None else 0.0


def _tool_get_revenue(db: Session, start_date: str, end_date: str) -> dict:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    summary = get_revenue_summary(db, start, end)
    return {
        "start_date": summary.start_date.isoformat(),
        "end_date": summary.end_date.isoformat(),
        "gross_revenue": _decimal_to_float(summary.gross_revenue),
        "total_discount": _decimal_to_float(summary.total_discount),
        "net_revenue": _decimal_to_float(summary.net_revenue),
        "transaction_count": summary.transaction_count,
        "line_item_count": summary.line_item_count,
    }


def _tool_get_profit(db: Session, start_date: str, end_date: str) -> dict:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    summary = get_profit_summary(db, start, end)
    return {
        "start_date": summary.start_date.isoformat(),
        "end_date": summary.end_date.isoformat(),
        "net_revenue": _decimal_to_float(summary.net_revenue),
        "cogs": _decimal_to_float(summary.cogs),
        "gross_profit": _decimal_to_float(summary.gross_profit),
        "operating_expenses": _decimal_to_float(summary.operating_expenses),
        "operating_profit": _decimal_to_float(summary.operating_profit),
        "gross_margin_pct": summary.gross_margin_pct,
        "operating_margin_pct": summary.operating_margin_pct,
        "data_complete": summary.data_complete,
        "notes": summary.notes,
    }


def _tool_get_top_products(db: Session, limit: int = 5, by: str = "revenue") -> list[dict]:
    products = get_top_products(db, limit=limit, by=by)
    return [
        {
            "product_id": p.product_id,
            "product_name": p.product_name,
            "units_sold": p.units_sold,
            "revenue": _decimal_to_float(p.revenue),
            "gross_profit": _decimal_to_float(p.gross_profit),
        }
        for p in products
    ]


def _tool_get_low_stock(db: Session, threshold: int = 50) -> list[dict]:
    items = get_low_stock(db, threshold=threshold)
    return [
        {
            "product_id": i.product_id,
            "product_name": i.product_name,
            "current_stock": i.current_stock,
            "selling_price": _decimal_to_float(i.selling_price),
        }
        for i in items
    ]


def _tool_get_monthly_trend(db: Session, start_date: str, end_date: str) -> list[dict]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    rows = get_monthly_revenue(db, start, end)
    return [
        {
            "month": r["month"],
            "gross": _decimal_to_float(r["gross"]),
            "discount": _decimal_to_float(r["discount"]),
            "net": _decimal_to_float(r["net"]),
        }
        for r in rows
    ]


def _tool_get_forecast(db: Session, days: int = 7) -> dict:
    model_path = find_latest_model()
    if model_path is None:
        return {"status": "no_model", "message": "No trained model available."}

    bundle = load_model(model_path)
    stmt = (
        select(Sale.date, SaleItem.quantity, Product.selling_price, SaleItem.discount)
        .join(SaleItem, SaleItem.sale_id == Sale.sale_id)
        .join(Product, Product.product_id == SaleItem.product_id)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return {"status": "insufficient_data", "message": "No sales history."}

    df = pd.DataFrame(rows, columns=["date", "quantity", "selling_price", "discount"])
    df["date"] = pd.to_datetime(df["date"])
    df["revenue"] = df["quantity"] * df["selling_price"] - df["discount"]

    daily = (
        df.assign(day=df["date"].dt.normalize())
        .groupby("day", as_index=False)["revenue"]
        .sum()
        .rename(columns={"day": "date"})
    )

    if len(daily) < 14:
        return {
            "status": "insufficient_data",
            "message": f"Need 14+ days of history, have {len(daily)}.",
        }

    points = generate_forecast(bundle, daily, days=days)
    return {
        "status": "ok",
        "model_version": bundle.get("version"),
        "points": [
            {"date": p["date"].isoformat(), "predicted_revenue": p["predicted_revenue"]}
            for p in points
        ],
    }


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_revenue": {
        "description": "Get total revenue, discounts, and transaction counts for a date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
            },
            "required": ["start_date", "end_date"],
        },
        "handler": _tool_get_revenue,
    },
    "get_profit": {
        "description": "Get profit breakdown: revenue, COGS, gross profit, operating expenses, operating profit.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
        "handler": _tool_get_profit,
    },
    "get_top_products": {
        "description": "Get top-selling products ranked by revenue or units sold.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of products (1-50).", "default": 5},
                "by": {"type": "string", "enum": ["revenue", "units"], "default": "revenue"},
            },
            "required": [],
        },
        "handler": _tool_get_top_products,
    },
    "get_low_stock": {
        "description": "Get products with stock below a threshold, for reordering decisions.",
        "parameters": {
            "type": "object",
            "properties": {
                "threshold": {"type": "integer", "description": "Stock threshold.", "default": 50},
            },
            "required": [],
        },
        "handler": _tool_get_low_stock,
    },
    "get_monthly_trend": {
        "description": "Get revenue grouped by calendar month for trend analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
        "handler": _tool_get_monthly_trend,
    },
    "get_forecast": {
        "description": "Get predicted future revenue using the trained ML model.",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days ahead (1-30).", "default": 7},
            },
            "required": [],
        },
        "handler": _tool_get_forecast,
    },
}


def get_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool schemas for the LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": meta["parameters"],
            },
        }
        for name, meta in TOOL_REGISTRY.items()
    ]


def execute_tool(name: str, arguments: dict, db: Session) -> dict:
    """Execute a tool by name with validated arguments. Returns JSON-serializable dict."""
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}

    meta = TOOL_REGISTRY[name]
    handler: Callable = meta["handler"]

    try:
        result = handler(db, **arguments)
        if isinstance(result, list):
            return {"result": result}
        return {"result": result} if not isinstance(result, dict) else result
    except Exception as exc:
        return {"error": f"Tool execution failed: {exc}"}