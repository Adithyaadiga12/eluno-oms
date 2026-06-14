from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.routes import api as api_routes
from app.routes import pages as page_routes

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Eluno OMS",
    description="AI-Powered Order Management System for Eyewear",
    version="0.1.0",
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(page_routes.router)
app.include_router(api_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
