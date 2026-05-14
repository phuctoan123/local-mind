from __future__ import annotations

import time

from fastapi import APIRouter

from app.database import get_connection, migration_status
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
            status = migration_status(conn)
        components["sqlite"] = ComponentHealth(
            status="ok" if not status["pending"] else "degraded",
            details={"migrations": status},
        )
    except Exception as exc:
        components["sqlite"] = ComponentHealth(status="error", message=str(exc))

    try:
        vector_health = get_vector_store().health()
        components["vector_store"] = ComponentHealth(
            status=vector_health["status"],
            message=vector_health.get("message"),
            details=vector_health,
        )
    except Exception as exc:
        components["vector_store"] = ComponentHealth(status="error", message=str(exc))

    ollama_health = await get_llm_client().health()
    embed_health = await get_embedding_service().health()
    llm_ok = ollama_health.get("status") == "ok" and embed_health.get("status") == "ok"
    components["llm"] = ComponentHealth(
        status="ok" if llm_ok else "error",
        details={"chat": ollama_health, "embedding": embed_health},
    )
    system_status = "ok" if all(item.status == "ok" for item in components.values()) else "degraded"
    return HealthResponse(
        status=system_status,
        version="0.1.0",
        components=components,
        uptime_seconds=int(time.monotonic() - STARTED_AT),
    )
