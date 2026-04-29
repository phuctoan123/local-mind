from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: str
    message: str | None = None
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict[str, ComponentHealth]
    uptime_seconds: int
