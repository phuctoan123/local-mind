from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, collections, documents, health, openai_compat, research, retrieval
from app.config import ensure_data_dirs, settings
from app.database import init_db
from app.middleware.auth import ApiKeyMiddleware


def create_app() -> FastAPI:
    ensure_data_dirs()
    init_db()
    app = FastAPI(
        title="LocalMind",
        version="0.1.0",
        description="Document Q&A with local and hosted model providers.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ApiKeyMiddleware)
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(retrieval.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(openai_compat.router, prefix="/v1")
    return app


app = create_app()
