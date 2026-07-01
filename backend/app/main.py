import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import auth, products, sellers, analytics, monitoring, scraping

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"startup env={settings.app_env} project={settings.project_name}")
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

prefix = settings.api_prefix
app.include_router(auth.router, prefix=prefix)
app.include_router(products.router, prefix=prefix)
app.include_router(sellers.router, prefix=prefix)
app.include_router(analytics.router, prefix=prefix)
app.include_router(monitoring.router, prefix=prefix)
app.include_router(scraping.router, prefix=prefix)


@app.get("/")
async def root():
    return {"project": settings.project_name, "docs": "/docs", "health": f"{prefix}/health"}
