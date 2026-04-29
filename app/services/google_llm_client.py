from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.services.llm_client import LLMUnavailableError


class GoogleLLMClient:
    def __init__(self, api_key: str, model: str, base_url: str, timeout: int = 120):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.1,
        top_p: float = 0.9,
        num_ctx: int = 2048,
        num_predict: int = 256,
    ) -> str | AsyncIterator[str]:
        if not self.api_key:
            raise LLMUnavailableError("GOOGLE_API_KEY is not set")
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "maxOutputTokens": num_predict,
            },
        }
        if stream:
            return self._stream(payload)
        endpoint = f"{self.base_url}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.timeout), connect=10.0)) as client:
            try:
                response = await client.post(endpoint, headers=self._headers(), json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise LLMUnavailableError(_http_error("Google generateContent", response)) from exc
            except Exception as exc:
                raise LLMUnavailableError(_describe_error(exc)) from exc
        return _extract_text(response.json())

    async def _stream(self, payload: dict) -> AsyncIterator[str]:
        endpoint = f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse"
        async with httpx.AsyncClient(timeout=httpx.Timeout(float(self.timeout), connect=10.0)) as client:
            try:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if not data or data == "[DONE]":
                            continue
                        token = _extract_text(json.loads(data))
                        if token:
                            yield token
            except httpx.HTTPStatusError as exc:
                raise LLMUnavailableError(_http_error("Google streamGenerateContent", response)) from exc
            except Exception as exc:
                raise LLMUnavailableError(_describe_error(exc)) from exc

    async def health(self) -> dict:
        if not self.api_key:
            return {"status": "error", "message": "GOOGLE_API_KEY is not set"}
        endpoint = f"{self.base_url}/models/{self.model}"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                response = await client.get(endpoint, headers=self._headers())
                response.raise_for_status()
            return {"status": "ok", "model": self.model, "provider": "google"}
        except httpx.HTTPStatusError:
            return {"status": "error", "message": _http_error("Google model health", response)}
        except Exception as exc:
            return {"status": "error", "message": _describe_error(exc)}

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        feedback = data.get("promptFeedback") or {}
        return f"Google returned no candidates. Prompt feedback: {feedback}"
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def _http_error(label: str, response: httpx.Response) -> str:
    return f"{label} returned HTTP {response.status_code}: {response.text or response.reason_phrase}"


def _describe_error(error: Exception) -> str:
    message = str(error).strip()
    return f"{type(error).__name__}: {message or repr(error)}"
