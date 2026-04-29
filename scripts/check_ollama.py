from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:11434"


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(path: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    try:
        version = get_json("/api/version")
    except urllib.error.URLError as exc:
        print(f"Ollama is not reachable at {BASE_URL}: {exc}")
        print("Start Ollama with: ollama serve")
        return 1

    print(f"Ollama reachable: {version}")
    try:
        tags = get_json("/api/tags")
    except urllib.error.URLError as exc:
        print(f"Could not list models: {exc}")
        return 1

    names = [model.get("name") for model in tags.get("models", [])]
    print("Installed models:")
    for name in names:
        print(f"- {name}")

    required = {"mistral:7b", "nomic-embed-text:latest"}
    missing = required.difference(names)
    if missing:
        print(f"Missing required models: {', '.join(sorted(missing))}")
        return 1

    try:
        embedding = post_json(
            "/api/embeddings",
            {"model": "nomic-embed-text:latest", "prompt": "hello"},
        )
        vector = embedding.get("embedding")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print(f"Embedding endpoint failed: {exc.read().decode('utf-8', errors='replace')}")
            return 1
        embedding = post_json(
            "/api/embed",
            {"model": "nomic-embed-text:latest", "input": "hello"},
        )
        vectors = embedding.get("embeddings") or []
        vector = vectors[0] if vectors else None
    except urllib.error.URLError as exc:
        print(f"Embedding request failed: {exc}")
        return 1
    print(f"Embedding OK: {len(vector or [])} dimensions")

    try:
        chat = post_json(
            "/api/chat",
            {
                "model": "mistral:7b",
                "messages": [{"role": "user", "content": "Reply with OK only."}],
                "stream": False,
            },
            timeout=120,
        )
    except urllib.error.HTTPError as exc:
        print(f"Chat endpoint failed: {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Chat request failed: {exc}")
        return 1
    print(f"Chat OK: {chat.get('message', {}).get('content', '').strip()[:80]}")
    print("Required models are available.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
