from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.ml.features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    add_time_features,
    build_daily_series,
    chronological_split,
)


MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _baseline_predict(test_df: pd.DataFrame) -> np.ndarray:
    return test_df["rolling_mean_7"].values


def _metrics(y_true, y_pred) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
    }


def train_forecast(sales_df: pd.DataFrame, test_ratio: float = 0.2) -> dict:
    daily = build_daily_series(sales_df)
    featured = add_time_features(daily)

    if len(featured) < 30:
        raise ValueError(
            f"Insufficient history: only {len(featured)} usable rows after feature engineering. "
            f"Need at least 30 for a stable model."
        )

    train_df, test_df = chronological_split(featured, test_ratio=test_ratio)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df[TARGET_COLUMN].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df[TARGET_COLUMN].values

    model = RandomForestRegressor(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred_rf = model.predict(X_test)
    y_pred_base = _baseline_predict(test_df)

    metrics = {
        "model": _metrics(y_test, y_pred_rf),
        "baseline": _metrics(y_test, y_pred_base),
        "train_size": int(len(train_df)),
        "test_size": int(len(test_df)),
        "beats_baseline": bool(
            _metrics(y_test, y_pred_rf)["mae"] < _metrics(y_test, y_pred_base)["mae"]
        ),
    }

    version = datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
    artifact_path = MODELS_DIR / f"forecast_{version}.joblib"
    joblib.dump(
        {"model": model, "features": FEATURE_COLUMNS, "version": version},
        artifact_path,
    )

    return {
        **metrics,
        "version": version,
        "artifact_path": str(artifact_path),
        "train_start": train_df["date"].min().date().isoformat(),
        "train_end": train_df["date"].max().date().isoformat(),
        "n_samples": int(len(featured)),
    }