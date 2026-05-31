from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_pool, init_pool
from app.logging_config import setup_logging
from app.routers import homeassistant

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="data-ingestion-api",
    description="API gateway between homelab applications and PostgreSQL.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(homeassistant.router)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok"}
