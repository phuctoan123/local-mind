from __future__ import annotations

import time

from fastapi import APIRouter

from app.database import get_connection
from app.dependencies import get_embedding_service, get_llm_client, get_vector_store
from app.models.health import ComponentHealth, HealthResponse

router = APIRouter(tags=["health"])
STARTED_AT = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health():
    components: dict[str, ComponentHealth] = {}
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        components["sqlite"] = ComponentHealth(status="ok")
    except Exception as exc:
        components["sqlite"] = ComponentHealth(status="error", message=str(exc))

    try:
        components["chroma"] = ComponentHealth(
            status="ok",
            details=get_vector_store().health(),
        )
    except Exception as exc:
        components["chroma"] = ComponentHealth(status="error", message=str(exc))

    ollama_health = await get_llm_client().health()
    embed_health = await get_embedding_service().health()
    components["llm"] = ComponentHealth(
        status="ok" if ollama_health.get("status") == "ok" and embed_health.get("status") == "ok" else "error",
        details={"chat": ollama_health, "embedding": embed_health},
    )
    system_status = "ok" if all(item.status == "ok" for item in components.values()) else "degraded"
    return HealthResponse(
        status=system_status,
        version="0.1.0",
        components=components,
        uptime_seconds=int(time.monotonic() - STARTED_AT),
    )
