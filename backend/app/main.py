from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.forecast import router as forecast_router

app = FastAPI(
    title="ShopAI API",
    description="Your AI Business Partner for small retail shops",
    version="0.1.0",
)

app.include_router(analytics_router)
app.include_router(forecast_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "ShopAI"}