from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.ml.features import add_time_features, build_daily_series, chronological_split
from app.ml.forecast import train_forecast


def make_synthetic_sales(days: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2026-01-01", periods=days, freq="D")
    base = 100 + np.arange(days) * 0.5
    weekly = 20 * np.sin(2 * np.pi * np.arange(days) / 7)
    noise = rng.normal(0, 5, days)
    revenue = base + weekly + noise

    return pd.DataFrame({
        "date": dates,
        "revenue": revenue,
        "units": revenue / 10,
        "sale_id": [f"S{i}" for i in range(days)],
    })


def test_daily_series_fills_gaps():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-03", "2026-01-03"]),
        "revenue": [100, 50, 25],
        "units": [10, 5, 2],
        "sale_id": ["S1", "S2", "S3"],
    })
    daily = build_daily_series(df)
    assert len(daily) == 3
    assert daily.loc[daily["date"] == "2026-01-02", "revenue"].iloc[0] == 0


def test_time_features_have_no_nan():
    daily = build_daily_series(make_synthetic_sales(60))
    featured = add_time_features(daily)
    assert not featured.isna().any().any()
    assert "rolling_mean_7" in featured.columns
    assert "lag_7" in featured.columns


def test_chronological_split_ordered():
    daily = build_daily_series(make_synthetic_sales(60))
    featured = add_time_features(daily)
    train, test = chronological_split(featured, test_ratio=0.2)
    assert train["date"].max() < test["date"].min()


def test_train_forecast_succeeds():
    df = make_synthetic_sales(90)
    result = train_forecast(df)
    assert "model" in result
    assert "baseline" in result
    assert result["model"]["mae"] > 0
    assert result["n_samples"] > 0


def test_train_forecast_insufficient():
    df = make_synthetic_sales(10)
    with pytest.raises(ValueError, match="Insufficient history"):
        train_forecast(df)