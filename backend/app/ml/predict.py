from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import joblib
import pandas as pd

from app.ml.features import FEATURE_COLUMNS


MODELS_DIR = Path(__file__).resolve().parents[3] / "models"


def find_latest_model() -> Path | None:
    if not MODELS_DIR.exists():
        return None
    models = sorted(MODELS_DIR.glob("forecast_v*.joblib"))
    return models[-1] if models else None


def load_model(path: Path) -> dict:
    return joblib.load(path)


def generate_forecast(
    model_bundle: dict,
    daily_history: pd.DataFrame,
    days: int = 7,
) -> list[dict]:
    if len(daily_history) < 14:
        raise ValueError(
            f"Insufficient history for prediction: need >=14 days, got {len(daily_history)}"
        )

    model = model_bundle["model"]
    history = daily_history.sort_values("date").reset_index(drop=True).copy()

    # Normalize date column to Timestamp for safe arithmetic
    history["date"] = pd.to_datetime(history["date"])
    history["revenue"] = history["revenue"].astype(float)

    predictions: list[dict] = []
    last_date = history["date"].max().date()

    for i in range(1, days + 1):
        next_date = last_date + timedelta(days=i)

        lag_1 = float(history["revenue"].iloc[-1])
        lag_7 = float(history["revenue"].iloc[-7]) if len(history) >= 7 else lag_1
        roll_7 = float(history["revenue"].tail(7).mean())
        roll_14 = float(history["revenue"].tail(14).mean())

        features_row = {
            "day_of_week": next_date.weekday(),
            "day_of_month": next_date.day,
            "month": next_date.month,
            "is_weekend": int(next_date.weekday() >= 5),
            "lag_1": lag_1,
            "lag_7": lag_7,
            "rolling_mean_7": roll_7,
            "rolling_mean_14": roll_14,
        }

        X = pd.DataFrame([features_row], columns=FEATURE_COLUMNS)
        pred = float(model.predict(X)[0])
        pred = max(pred, 0.0)

        predictions.append({"date": next_date, "predicted_revenue": round(pred, 2)})

        # Append prediction so next day's lag_1 and rolling_mean_7 use it
        history = pd.concat(
            [
                history,
                pd.DataFrame(
                    [{"date": pd.Timestamp(next_date), "revenue": pred}]
                ),
            ],
            ignore_index=True,
        )

    return predictions