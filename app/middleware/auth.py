from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.api_key and request.url.path.startswith("/api/"):
            if request.headers.get("X-API-Key") != settings.api_key:
                return JSONResponse(
                    {"error": "unauthorized", "message": "Invalid or missing API key"},
                    status_code=401,
                )
        return await call_next(request)
