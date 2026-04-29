from __future__ import annotations

import asyncio

import httpx

from app.services.embedding_service import EmbeddingServiceUnavailableError


class MistralEmbeddingService:
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
            vectors.extend(await self._embed_batch_with_retry(batch))
        return vectors

    async def health(self) -> dict:
        if not self.api_key:
            return {"status": "error", "message": "MISTRAL_API_KEY is not set"}
        try:
            vector = await self.embed_text("health check")
            return {
                "status": "ok",
                "model": self.model,
                "provider": "mistral",
                "dimensions": len(vector),
            }
        except Exception as exc:
            return {"status": "error", "message": _describe_error(exc)}

    async def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for delay in (0, 1, 2, 4):
            if delay:
                await asyncio.sleep(delay)
            try:
                return await self._embed_once(texts)
            except Exception as exc:
                last_error = exc
        raise EmbeddingServiceUnavailableError(_describe_error(last_error))

    async def _embed_once(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingServiceUnavailableError("MISTRAL_API_KEY is not set")
        endpoint = f"{self.base_url}/embeddings"
        payload = {"model": self.model, "input": texts}
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.timeout), connect=10.0)) as client:
            try:
                response = await client.post(endpoint, headers=self._headers(), json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingServiceUnavailableError(
                    f"Mistral embeddings returned HTTP {response.status_code}: "
                    f"{response.text or response.reason_phrase}"
                ) from exc
            except Exception as exc:
                raise EmbeddingServiceUnavailableError(_describe_error(exc)) from exc
        rows = sorted(response.json().get("data", []), key=lambda item: item.get("index", 0))
        vectors = [row.get("embedding") for row in rows]
        if len(vectors) != len(texts) or not all(isinstance(vector, list) for vector in vectors):
            raise EmbeddingServiceUnavailableError("Mistral did not return the expected embeddings")
        return [[float(value) for value in vector] for vector in vectors]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}


def _describe_error(error: Exception | None) -> str:
    if error is None:
        return "unknown Mistral embedding error"
    message = str(error).strip()
    return f"{type(error).__name__}: {message or repr(error)}"
