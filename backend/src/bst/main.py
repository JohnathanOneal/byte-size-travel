from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from bst.db import create_schema, get_connection
from bst.logging_config import configure_logging
from bst.settings import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    configure_logging(settings.log_level)
    logger.info("startup", log_level=settings.log_level)

    # create database schema on startup
    conn = get_connection()
    create_schema(conn)
    conn.close()

    yield


app = FastAPI(
    title="bst",
    description="Content curation dashboard for Daily Drop",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
