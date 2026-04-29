from __future__ import annotations

import asyncio

import httpx

from app.services.embedding_service import EmbeddingServiceUnavailableError


class GoogleEmbeddingService:
    def __init__(self, api_key: str, model: str, base_url: str, timeout: int = 120):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def embed_text(self, text: str) -> list[float]:
        embeddings = await self.embed_batch([text], batch_size=1)
        return embeddings[0]

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            for text in batch:
                vectors.append(await self._embed_with_retry(text))
        return vectors

    async def health(self) -> dict:
        if not self.api_key:
            return {"status": "error", "message": "GOOGLE_API_KEY is not set"}
        try:
            vector = await self.embed_text("health check")
            return {
                "status": "ok",
                "model": self.model,
                "provider": "google",
                "dimensions": len(vector),
            }
        except Exception as exc:
            return {"status": "error", "message": _describe_error(exc)}

    async def _embed_with_retry(self, text: str) -> list[float]:
        last_error: Exception | None = None
        for delay in (0, 1, 2, 4):
            if delay:
                await asyncio.sleep(delay)
            try:
                return await self._embed_once(text)
            except Exception as exc:
                last_error = exc
        raise EmbeddingServiceUnavailableError(_describe_error(last_error))

    async def _embed_once(self, text: str) -> list[float]:
        if not self.api_key:
            raise EmbeddingServiceUnavailableError("GOOGLE_API_KEY is not set")
        endpoint = f"{self.base_url}/models/{self.model}:embedContent"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "taskType": "SEMANTIC_SIMILARITY",
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.timeout), connect=10.0)) as client:
            try:
                response = await client.post(endpoint, headers=self._headers(), json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingServiceUnavailableError(
                    f"Google embedContent returned HTTP {response.status_code}: "
                    f"{response.text or response.reason_phrase}"
                ) from exc
            except Exception as exc:
                raise EmbeddingServiceUnavailableError(_describe_error(exc)) from exc
        values = response.json().get("embedding", {}).get("values")
        if not isinstance(values, list):
            raise EmbeddingServiceUnavailableError("Google did not return embedding.values")
        return [float(value) for value in values]

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}


def _describe_error(error: Exception | None) -> str:
    if error is None:
        return "unknown Google embedding error"
    message = str(error).strip()
    return f"{type(error).__name__}: {message or repr(error)}"
