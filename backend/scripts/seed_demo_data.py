from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Expense, Product, Sale, SaleItem  # noqa: E402


PRODUCTS = [
    ("P001", "Rice 5kg", "Grains", Decimal("240"), Decimal("290"), 120),
    ("P002", "Cooking Oil 1L", "Oils", Decimal("110"), Decimal("135"), 85),
    ("P003", "Sugar 1kg", "Grains", Decimal("38"), Decimal("45"), 200),
    ("P004", "Tea Powder 500g", "Beverages", Decimal("180"), Decimal("225"), 60),
    ("P005", "Detergent 1kg", "Household", Decimal("95"), Decimal("120"), 45),
]


def main(days: int = 365) -> int:
    rng = random.Random(42)
    start_date = date.today() - timedelta(days=days)

    with SessionLocal() as db:
        # Idempotent: clear demo data first
        db.query(SaleItem).delete()
        db.query(Sale).delete()
        db.query(Expense).delete()
        db.query(Product).delete()
        db.commit()

        for pid, name, cat, cost, price, stock in PRODUCTS:
            db.add(
                Product(
                    product_id=pid,
                    product_name=name,
                    category=cat,
                    cost_price=cost,
                    selling_price=price,
                    current_stock=stock,
                )
            )
        db.commit()

        sale_counter = 0
        expense_counter = 0

        for day_offset in range(days):
            current = start_date + timedelta(days=day_offset)
            weekday = current.weekday()
            # Base demand: weekends higher, weekdays lower
            base_sales = 2 if weekday >= 5 else 1
            num_sales = base_sales + rng.randint(0, 2)

            for _ in range(num_sales):
                sale_counter += 1
                sid = f"D{sale_counter:06d}"
                db.add(Sale(sale_id=sid, date=current, customer_id=f"C{rng.randint(1, 50):03d}"))

                # 1-3 line items per sale
                for _ in range(rng.randint(1, 3)):
                    pid = rng.choice([p[0] for p in PRODUCTS])
                    qty = rng.randint(1, 5)
                    discount = Decimal("0") if rng.random() > 0.15 else Decimal(rng.randint(1, 10))
                    db.add(
                        SaleItem(
                            sale_id=sid,
                            product_id=pid,
                            quantity=qty,
                            discount=discount,
                        )
                    )

            # Monthly expense entries
            if current.day == 1:
                expense_counter += 1
                db.add(
                    Expense(
                        expense_id=f"E{expense_counter:05d}",
                        date=current,
                        category="Rent",
                        amount=Decimal("12000"),
                        note="Monthly rent",
                    )
                )
            if current.day == 5:
                expense_counter += 1
                db.add(
                    Expense(
                        expense_id=f"E{expense_counter:05d}",
                        date=current,
                        category="Electricity",
                        amount=Decimal(rng.randint(1500, 2200)),
                        note="Electricity bill",
                    )
                )
            if current.day == 8:
                expense_counter += 1
                db.add(
                    Expense(
                        expense_id=f"E{expense_counter:05d}",
                        date=current,
                        category="Wages",
                        amount=Decimal("8000"),
                        note="Part-time helper",
                    )
                )

            if day_offset % 30 == 0:
                db.commit()

        db.commit()

    print(f"Seeded {days} days of data: {sale_counter} sales, {expense_counter} expenses.")
    return 0


if __name__ == "__main__":
    sys.exit(main())