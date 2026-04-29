from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv() -> None:
    path = Path(".env")
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def post_json(url: str, api_key: str, payload: dict, timeout: int = 60) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY", "")
    base_url = os.getenv("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
    embed_model = os.getenv("GOOGLE_EMBED_MODEL", "gemini-embedding-001")

    if not api_key:
        print("GOOGLE_API_KEY is not set.")
        return 1

    try:
        response = post_json(
            f"{base_url}/models/{model}:generateContent",
            api_key,
            {
                "contents": [{"parts": [{"text": "Reply with OK only."}]}],
                "generationConfig": {"maxOutputTokens": 16},
            },
        )
        text = "".join(
            part.get("text", "")
            for part in response.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        print(f"Generate OK: {text.strip()}")
    except urllib.error.HTTPError as exc:
        print(f"Generate failed: HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Generate failed: {exc}")
        return 1

    try:
        response = post_json(
            f"{base_url}/models/{embed_model}:embedContent",
            api_key,
            {
                "model": f"models/{embed_model}",
                "content": {"parts": [{"text": "hello"}]},
                "taskType": "SEMANTIC_SIMILARITY",
            },
        )
        values = response.get("embedding", {}).get("values", [])
        print(f"Embedding OK: {len(values)} dimensions")
    except urllib.error.HTTPError as exc:
        print(f"Embedding failed: HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Embedding failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
