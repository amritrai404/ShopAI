from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.ml.forecast import train_forecast  # noqa: E402
from app.models import MLModelRun, Product, Sale, SaleItem  # noqa: E402


def load_sales_from_db() -> pd.DataFrame:
    with SessionLocal() as db:
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

    df = pd.DataFrame(rows, columns=["sale_id", "date", "quantity", "selling_price", "discount"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["revenue"] = df["quantity"] * df["selling_price"] - df["discount"]
    return df.rename(columns={"quantity": "units"})


def log_run(result: dict) -> None:
    with SessionLocal() as db:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Train ShopAI sales forecasting model.")
    parser.add_argument("--test-ratio", type=float, default=0.2)
    args = parser.parse_args()

    print("Loading sales data from database...")
    df = load_sales_from_db()
    print(f"Loaded {len(df)} line items.")

    if df.empty:
        print("ERROR: No sales data in database.")
        return 1

    try:
        result = train_forecast(df, test_ratio=args.test_ratio)
    except ValueError as exc:
        print(f"TRAINING FAILED: {exc}")
        return 1

    print("\n=== TRAINING RESULT ===")
    print(f"Version:         {result['version']}")
    print(f"Samples:         {result['n_samples']}")
    print(f"Train period:    {result['train_start']} to {result['train_end']}")
    print(f"Train/Test size: {result['train_size']} / {result['test_size']}")
    print(f"Model MAE:       {result['model']['mae']}")
    print(f"Model RMSE:      {result['model']['rmse']}")
    print(f"Baseline MAE:    {result['baseline']['mae']}")
    print(f"Baseline RMSE:   {result['baseline']['rmse']}")
    print(f"Beats baseline:  {result['beats_baseline']}")
    print(f"Artifact:        {result['artifact_path']}")

    log_run(result)
    print("\nRun logged to ml_model_runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())