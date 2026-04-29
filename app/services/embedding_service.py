from __future__ import annotations

import asyncio
from typing import Any

import httpx


class EmbeddingServiceUnavailableError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self, model: str, base_url: str, timeout: int = 120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def embed_text(self, text: str) -> list[float]:
        embeddings = await self.embed_batch([text], batch_size=1)
        return embeddings[0]

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            for text in texts[start : start + batch_size]:
                vectors.append(await self._embed_with_retry(text))
        return vectors

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
                response = await client.get(f"{self.base_url}/api/version")
                response.raise_for_status()
            return {"status": "ok", "model": self.model}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def _embed_with_retry(self, text: str) -> list[float]:
        delays = [1, 2, 4]
        last_error: Exception | None = None
        for attempt, delay in enumerate([0, *delays], start=1):
            if delay:
                await asyncio.sleep(delay)
            try:
                return await self._embed_once(text)
            except Exception as exc:
                last_error = exc
                if attempt == 4:
                    break
        raise EmbeddingServiceUnavailableError(_describe_error(last_error))

    async def _embed_once(self, text: str) -> list[float]:
        payload = {"model": self.model, "prompt": text}
        timeout = httpx.Timeout(float(self.timeout), connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            endpoint = f"{self.base_url}/api/embeddings"
            response = await client.post(endpoint, json=payload)
            if response.status_code == 404:
                endpoint = f"{self.base_url}/api/embed"
                response = await client.post(
                    endpoint,
                    json={"model": self.model, "input": text},
                )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingServiceUnavailableError(
                    f"embedding endpoint {endpoint} returned HTTP {response.status_code}: "
                    f"{response.text or response.reason_phrase}"
                ) from exc
            data = response.json()
        vector = data.get("embedding")
        if vector is None and isinstance(data.get("embeddings"), list) and data["embeddings"]:
            vector = data["embeddings"][0]
        if not isinstance(vector, list):
            raise EmbeddingServiceUnavailableError("Ollama did not return an embedding")
        return [float(value) for value in vector]


def _describe_error(error: Exception | None) -> str:
    if error is None:
        return "unknown embedding error"
    message = str(error).strip()
    return f"{type(error).__name__}: {message or repr(error)}"
