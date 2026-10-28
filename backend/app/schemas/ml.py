from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class ForecastPoint(BaseModel):
    date: date
    predicted_revenue: float


class ForecastResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    message: str | None = None
    model_version: str | None = None
    generated_at: datetime | None = None
    points: list[ForecastPoint] = []


class ModelRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    model_name: str
    version: str
    trained_at: datetime
    n_samples: int
    metrics: dict
    artifact_path: str | None


class TrainRequest(BaseModel):
    test_ratio: float = 0.2


class TrainResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    message: str
    metrics: dict | None = None
    version: str | None = None
    artifact_path: str | None = None