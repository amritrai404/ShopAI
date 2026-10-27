from __future__ import annotations

import pandas as pd


def build_daily_series(sales_df: pd.DataFrame) -> pd.DataFrame:
    required = {"date"}
    missing = required - set(sales_df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = sales_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    agg = df.groupby("date").agg(
        revenue=("revenue", "sum") if "revenue" in df.columns else ("date", "size"),
        units=("units", "sum") if "units" in df.columns else ("date", "size"),
        transactions=("sale_id", "nunique") if "sale_id" in df.columns else ("date", "size"),
    )

    full_idx = pd.date_range(agg.index.min(), agg.index.max(), freq="D")
    agg = agg.reindex(full_idx, fill_value=0).reset_index().rename(columns={"index": "date"})
    return agg


def add_time_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    df = daily_df.sort_values("date").reset_index(drop=True).copy()

    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    df["lag_1"] = df["revenue"].shift(1)
    df["lag_7"] = df["revenue"].shift(7)
    df["rolling_mean_7"] = df["revenue"].shift(1).rolling(7).mean()
    df["rolling_mean_14"] = df["revenue"].shift(1).rolling(14).mean()

    df = df.dropna().reset_index(drop=True)
    return df


FEATURE_COLUMNS = [
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "lag_1",
    "lag_7",
    "rolling_mean_7",
    "rolling_mean_14",
]

TARGET_COLUMN = "revenue"


def chronological_split(df: pd.DataFrame, test_ratio: float = 0.2):
    n = len(df)
    split_at = int(n * (1 - test_ratio))
    if split_at < 14:
        raise ValueError(f"Insufficient rows for split: {n}")
    return df.iloc[:split_at].copy(), df.iloc[split_at:].copy()