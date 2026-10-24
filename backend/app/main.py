
from fastapi import FastAPI

app = FastAPI(
    title="ShopAI API",
    description="Your AI Business Partner for small retail shops",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "ShopAI"}
