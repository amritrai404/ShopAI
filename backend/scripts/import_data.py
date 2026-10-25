
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Expense, Product, Sale, SaleItem  # noqa: E402


BASE_DIR = Path(__file__).resolve().parents[2]
CSV_DIR = BASE_DIR / "data" / "samples"

REQUIRED_COLUMNS = {
    "products.csv": {
        "product_id",
        "product_name",
        "category",
        "cost_price",
        "selling_price",
        "current_stock",
    },
    "sales.csv": {
        "sale_id",
        "date",
        "product_id",
        "quantity",
        "discount",
        "customer_id",
    },
    "expenses.csv": {
        "expense_id",
        "date",
        "category",
        "amount",
        "note",
    },
}


class ImportValidationError(Exception):
    """Raised when CSV input is missing or invalid."""


def load_csv(filename: str) -> pd.DataFrame:
    path = CSV_DIR / filename
    if not path.is_file():
        raise ImportValidationError(f"Missing CSV file: {path}")

    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ImportValidationError(
            f"Could not read {filename}: {exc}"
        ) from exc

    df.columns = df.columns.str.strip()
    missing = REQUIRED_COLUMNS[filename] - set(df.columns)

    if missing:
        raise ImportValidationError(
            f"{filename} is missing columns: {sorted(missing)}"
        )

    for column in df.columns:
        df[column] = df[column].map(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )

    return df


def require_values(df, filename, columns, errors):
    for column in columns:
        bad = df.index[df[column].eq("")].tolist()
        if bad:
            rows = [int(index) + 2 for index in bad[:10]]
            errors.append(
                f"{filename}: blank '{column}' at CSV rows {rows}"
            )


def parse_number(
    df,
    filename,
    column,
    errors,
    *,
    integer=False,
    minimum=None,
):
    parsed = pd.to_numeric(df[column], errors="coerce")
    bad = parsed.isna()

    if integer:
        bad |= parsed.notna() & (parsed % 1 != 0)

    if minimum is not None:
        bad |= parsed.notna() & (parsed < minimum)

    if bad.any():
        rows = [int(index) + 2 for index in df.index[bad][:10]]
        errors.append(
            f"{filename}: invalid '{column}' at CSV rows {rows}"
        )
        return

    df[column] = parsed.astype(
        "int64" if integer else "float64"
    )


def parse_dates(df, filename, column, errors):
    parsed = pd.to_datetime(
        df[column],
        errors="coerce",
        format="mixed",
    )
    bad = parsed.isna()

    if bad.any():
        rows = [int(index) + 2 for index in df.index[bad][:10]]
        errors.append(
            f"{filename}: invalid '{column}' date at CSV rows {rows}"
        )
        return

    df[column] = parsed.dt.date


def check_unique(df, filename, column, errors):
    duplicates = df[column].duplicated(keep=False)

    if duplicates.any():
        values = df.loc[duplicates, column].unique().tolist()[:10]
        errors.append(
            f"{filename}: duplicate '{column}' values: {values}"
        )


def validate_data():
    errors: list[str] = []
    warnings: list[str] = []

    products = load_csv("products.csv")
    sales = load_csv("sales.csv")
    expenses = load_csv("expenses.csv")

    require_values(
        products,
        "products.csv",
        [
            "product_id",
            "product_name",
            "cost_price",
            "selling_price",
            "current_stock",
        ],
        errors,
    )
    require_values(
        sales,
        "sales.csv",
        [
            "sale_id",
            "date",
            "product_id",
            "quantity",
            "discount",
        ],
        errors,
    )
    require_values(
        expenses,
        "expenses.csv",
        ["expense_id", "date", "category", "amount"],
        errors,
    )

    check_unique(products, "products.csv", "product_id", errors)
    check_unique(expenses, "expenses.csv", "expense_id", errors)

    parse_number(
        products, "products.csv", "cost_price", errors, minimum=0
    )
    parse_number(
        products, "products.csv", "selling_price", errors, minimum=0
    )
    parse_number(
        products,
        "products.csv",
        "current_stock",
        errors,
        integer=True,
        minimum=0,
    )
    parse_number(
        sales,
        "sales.csv",
        "quantity",
        errors,
        integer=True,
        minimum=1,
    )
    parse_number(
        sales, "sales.csv", "discount", errors, minimum=0
    )
    parse_number(
        expenses, "expenses.csv", "amount", errors, minimum=0
    )

    parse_dates(sales, "sales.csv", "date", errors)
    parse_dates(expenses, "expenses.csv", "date", errors)

    products["category"] = products["category"].replace("", None)
    sales["customer_id"] = sales["customer_id"].replace("", None)
    expenses["note"] = expenses["note"].replace("", None)

    if errors:
        return products, sales, expenses, errors, warnings

    product_ids = set(products["product_id"])
    unknown = sorted(set(sales["product_id"]) - product_ids)

    if unknown:
        errors.append(
            f"sales.csv references unknown product IDs: {unknown[:10]}"
        )
    else:
        price_map = products.set_index("product_id")["selling_price"]
        excessive = []

        for index, row in sales.iterrows():
            gross = (
                float(price_map[row["product_id"]])
                * int(row["quantity"])
            )
            if float(row["discount"]) > gross:
                excessive.append(int(index) + 2)

        if excessive:
            warnings.append(
                "Discount exceeds line gross at sales.csv rows "
                f"{excessive[:10]}"
            )

    headers = sales[
        ["sale_id", "date", "customer_id"]
    ].drop_duplicates()

    conflicting = headers[
        headers.duplicated("sale_id", keep=False)
    ]

    if not conflicting.empty:
        errors.append(
            "Inconsistent date/customer_id for sale IDs: "
            f"{conflicting['sale_id'].unique().tolist()[:10]}"
        )

    if sales.duplicated(
        ["sale_id", "product_id"], keep=False
    ).any():
        warnings.append(
            "Repeated sale_id/product_id combinations found; "
            "each CSV row will be imported as a separate item."
        )

    headers = headers.drop_duplicates("sale_id")

    try:
        with SessionLocal() as check_db:
            existing_products = set(
                check_db.scalars(select(Product.product_id)).all()
            )
            existing_sales = set(
                check_db.scalars(select(Sale.sale_id)).all()
            )
            existing_expenses = set(
                check_db.scalars(select(Expense.expense_id)).all()
            )

        for label, incoming, existing in [
            (
                "product_id",
                set(products["product_id"]),
                existing_products,
            ),
            (
                "sale_id",
                set(headers["sale_id"]),
                existing_sales,
            ),
            (
                "expense_id",
                set(expenses["expense_id"]),
                existing_expenses,
            ),
        ]:
            overlap = sorted(incoming & existing)

            if overlap:
                errors.append(
                    f"Database already contains {label} values from "
                    "these CSV files: "
                    f"{overlap[:10]}. Import stopped to avoid duplicates."
                )

    except SQLAlchemyError as exc:
        errors.append(f"Database preflight check failed: {exc}")

    return products, sales, expenses, errors, warnings


def print_report(products, sales, expenses, errors, warnings):
    print("\n========== DATA QUALITY REPORT ==========")
    print(f"Products CSV rows: {len(products)}")
    print(f"Sales CSV line items: {len(sales)}")
    print(f"Distinct sales: {sales['sale_id'].nunique()}")
    print(f"Expenses CSV rows: {len(expenses)}")
    print(f"Validation errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    for warning in warnings:
        print(f"WARNING: {warning}")

    for error in errors:
        print(f"ERROR: {error}")

    print("==========================================")


def import_data(products, sales, expenses):
    sale_headers = sales[
        ["sale_id", "date", "customer_id"]
    ].drop_duplicates("sale_id")

    product_records = [
        Product(
            product_id=row.product_id,
            product_name=row.product_name,
            category=row.category,
            cost_price=float(row.cost_price),
            selling_price=float(row.selling_price),
            current_stock=int(row.current_stock),
        )
        for row in products.itertuples(index=False)
    ]

    sale_records = [
        Sale(
            sale_id=row.sale_id,
            date=row.date,
            customer_id=row.customer_id,
        )
        for row in sale_headers.itertuples(index=False)
    ]

    sale_item_records = [
        SaleItem(
            sale_id=row.sale_id,
            product_id=row.product_id,
            quantity=int(row.quantity),
            discount=float(row.discount),
        )
        for row in sales.itertuples(index=False)
    ]

    expense_records = [
        Expense(
            expense_id=row.expense_id,
            date=row.date,
            category=row.category,
            amount=float(row.amount),
            note=row.note,
        )
        for row in expenses.itertuples(index=False)
    ]

    with SessionLocal() as db:
        with db.begin():
            db.add_all(product_records)
            db.flush()

            db.add_all(sale_records)
            db.flush()

            db.add_all(sale_item_records)
            db.add_all(expense_records)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and import ShopAI sample CSV files."
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Import validated CSV data into PostgreSQL.",
    )
    args = parser.parse_args()

    print("ShopAI CSV Importer")
    print(f"CSV directory: {CSV_DIR}")
    print(f"Mode: {'IMPORT' if args.commit else 'DRY-RUN'}")

    try:
        products, sales, expenses, errors, warnings = validate_data()
    except (
        ImportValidationError,
        OSError,
        ValueError,
        SQLAlchemyError,
    ) as exc:
        print(f"\nVALIDATION FAILED: {exc}")
        return 1

    print_report(products, sales, expenses, errors, warnings)

    if errors:
        print("\nImport aborted. Fix the reported errors first.")
        return 1

    if not args.commit:
        print("\nDRY-RUN PASSED. Database was not modified.")
        print("Run with --commit after reviewing the report.")
        return 0

    try:
        import_data(products, sales, expenses)
    except Exception as exc:
        print(f"\nIMPORT FAILED: {exc}")
        return 1

    print("\nIMPORT SUCCESSFUL")
    print(f"Products imported: {len(products)}")
    print(f"Sales imported: {sales['sale_id'].nunique()}")
    print(f"Sale items imported: {len(sales)}")
    print(f"Expenses imported: {len(expenses)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
