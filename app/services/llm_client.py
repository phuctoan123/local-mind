from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx


class LLMUnavailableError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.1,
        top_p: float = 0.9,
        num_ctx: int = 4096,
        num_predict: int = 256,
    ) -> str | AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
            },
        }
        if stream:
            return self._stream(payload)
        timeout = httpx.Timeout(float(self.timeout), connect=5.0)
        endpoint = f"{self.base_url}/api/chat"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = (
                    f"chat endpoint {endpoint} returned HTTP {response.status_code}: "
                    f"{response.text or response.reason_phrase}"
                )
                raise LLMUnavailableError(detail) from exc
            except Exception as exc:
                detail = _describe_error(exc)
                raise LLMUnavailableError(detail) from exc
        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    async def _stream(self, payload: dict[str, Any]) -> AsyncIterator[str]:
        timeout = httpx.Timeout(float(self.timeout), connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            import json

                            data = json.loads(line)
                            content = data.get("message", {}).get("content")
                            if content:
                                yield content
                        except ValueError:
                            continue
            except Exception as exc:
                raise LLMUnavailableError(str(exc)) from exc

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
                response = await client.get(f"{self.base_url}/api/version")
                response.raise_for_status()
            return {"status": "ok", "model": self.model}
        except Exception as exc:
            return {"status": "error", "message": _describe_error(exc)}


def _describe_error(error: Exception) -> str:
    if isinstance(error, httpx.ReadTimeout):
        return (
            "ReadTimeout: Ollama accepted the request but did not finish the response before "
            "OLLAMA_TIMEOUT. Increase OLLAMA_TIMEOUT or warm the model with `ollama run mistral:7b`."
        )
    message = str(error).strip()
    return f"{type(error).__name__}: {message or repr(error)}"
