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
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY", "")
    base_url = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").rstrip("/")
    model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    embed_model = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed")

    if not api_key or api_key.startswith("REPLACE_WITH"):
        print("MISTRAL_API_KEY is not set.")
        return 1

    try:
        response = post_json(
            f"{base_url}/chat/completions",
            api_key,
            {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with OK only."}],
                "max_tokens": 16,
                "temperature": 0.1,
            },
        )
        text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Chat OK: {text.strip()}")
    except urllib.error.HTTPError as exc:
        print(f"Chat failed: HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Chat failed: {exc}")
        return 1

    try:
        response = post_json(
            f"{base_url}/embeddings",
            api_key,
            {"model": embed_model, "input": ["hello"]},
        )
        values = response.get("data", [{}])[0].get("embedding", [])
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
